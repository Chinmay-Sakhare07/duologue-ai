import logging
import os

import streamlit as st

from config import HOST_PRESETS, LENGTHS, MAX_SOURCE_CHARS, TONES
from ingestion import extract_pdf_text, extract_url_text
from script import ScriptGenerationError, ScriptParseError, generate_script
from tts import synthesize_turns
from audio import stitch_audio

# --- Logging setup (configured once, even though Streamlit reruns this file) ---
logger = logging.getLogger("duologue")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False

st.set_page_config(page_title="Duologue AI")

st.title("Duologue AI")
st.write("Turn text, a PDF, or an article URL into a two-host podcast conversation.")

# --- Source selection ---
source_type = st.radio("Source", ["Paste text", "PDF", "URL"], horizontal=True)

pasted_text = ""
uploaded_pdf = None
url = ""
if source_type == "Paste text":
    pasted_text = st.text_area("Source text", height=250,
                               placeholder="Paste an article or any text here...")
elif source_type == "PDF":
    uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])
else:  # URL
    url = st.text_input("Article URL", placeholder="https://...")

col1, col2, col3 = st.columns(3)
tone_choice = col1.selectbox("Tone", list(TONES.keys()))
length_choice = col2.selectbox("Length", list(LENGTHS.keys()))
preset_choice = col3.selectbox("Hosts", list(HOST_PRESETS.keys()))

if length_choice != "5 min":
    st.caption("Heads-up: on the free tier, longer scripts may truncate or hit the rate limit. 5 min is the reliable option for now.")

if st.button("Generate podcast"):
    # --- Step 1: turn the chosen source into clean text ---
    with st.spinner("Reading your source..."):
        if source_type == "Paste text":
            source_text = pasted_text.strip()
        elif source_type == "PDF":
            if uploaded_pdf is None:
                st.warning("Please upload a PDF first.")
                st.stop()
            try:
                source_text = extract_pdf_text(uploaded_pdf).strip()
            except Exception:
                logger.exception("PDF extraction failed")
                st.error("Couldn't read that PDF. Please try a different file.")
                st.stop()
        else:  # URL
            if not url.strip():
                st.warning("Please enter a URL first.")
                st.stop()
            try:
                source_text = extract_url_text(url.strip()).strip()
            except Exception:
                logger.exception("URL extraction failed")
                st.error("Couldn't fetch that URL. Please check it, or paste the text instead.")
                st.stop()

    if not source_text:
        st.error(
            "No usable text found. A scanned PDF has no text layer — try an OCR'd version. "
            "Some sites block scraping — paste the article text instead."
        )
        st.stop()

    if len(source_text) > MAX_SOURCE_CHARS:
        source_text = source_text[:MAX_SOURCE_CHARS]
        logger.info("Source truncated to %d chars", MAX_SOURCE_CHARS)
        st.caption("Your source was long, so only the beginning was used to stay within free-tier limits.")

    # --- Step 2: script -> voices -> stitch ---
    tone_desc = TONES[tone_choice]
    length = LENGTHS[length_choice]
    hosts = HOST_PRESETS[preset_choice]

    logger.info("Generation started | type=%s tone=%s length=%s preset=%s chars=%d",
                source_type, tone_choice, length_choice, preset_choice, len(source_text))

    with st.spinner("Writing the script..."):
        try:
            turns = generate_script(source_text, tone_choice, tone_desc, length, hosts,
                                    st.secrets["GROQ_API_KEY"])
        except ScriptGenerationError:
            logger.exception("Groq request failed")
            st.error("The script generator is unavailable right now. Please try again in a moment.")
            st.stop()
        except ScriptParseError:
            logger.exception("Could not parse Groq output")
            st.error("Couldn't parse the model's output. Try again, or pick a shorter length.")
            st.stop()

    logger.info("Parsed script | turns=%d", len(turns))

    with st.spinner("Recording the voices..."):
        try:
            audio_paths = synthesize_turns(turns, hosts["voice_a"], hosts["voice_b"])
        except Exception:
            logger.exception("Voice generation failed")
            st.error("Voice generation failed — this may be a temporary issue with the TTS service.")
            st.stop()

    logger.info("Synthesis complete | clips=%d", len(audio_paths))

    try:
        with st.spinner("Stitching the episode..."):
            episode_bytes = stitch_audio(audio_paths)
        logger.info("Stitched episode | bytes=%d", len(episode_bytes))
    except Exception:
        logger.exception("Stitching failed")
        st.error("Couldn't assemble the final audio. Please try again.")
        st.stop()
    finally:
        for path in audio_paths:
            try:
                os.remove(path)
            except OSError:
                pass

    st.divider()
    st.subheader("Your episode")
    st.audio(episode_bytes, format="audio/mp3")
    st.download_button(
        label="Download MP3",
        data=episode_bytes,
        file_name="duologue_episode.mp3",
        mime="audio/mp3",
    )

    with st.expander("Transcript"):
        for turn in turns:
            speaker = "Host A" if turn["speaker"] == "A" else "Host B"
            st.markdown(f"**{speaker}:** {turn['text']}")