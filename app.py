import logging
import os
import time
import uuid

import streamlit as st

from config import HOST_PRESETS, LENGTHS, MAX_SOURCE_CHARS, TONES
from ingestion import extract_pdf_text, extract_url_text
from script import (
    ScriptGenerationError,
    ScriptParseError,
    generate_script,
    research_topic,
)
from tts import AllTTSProvidersFailed, PRIMARY, synthesize_turns
from audio import stitch_audio
from db import get_client, get_audio_url, list_episodes, save_episode

RATE_LIMIT = 5              # generations allowed per session...
RATE_WINDOW = 3600          # ...within this many seconds (1 hour)

# --- Logging setup (configured once, even though Streamlit reruns this file) ---
logger = logging.getLogger("duologue")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False

st.set_page_config(page_title="Duologue AI", page_icon="🎙️")

# --- Visual polish (internal selectors; harmless if a Streamlit update ignores them) ---
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2.5rem; max-width: 900px;}

    /* Gradient title */
    h1 {
        background: linear-gradient(90deg, #A78BFA 0%, #F0A868 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* Accent bar on bordered cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-left: 3px solid #A78BFA !important;
    }

    /* Primary button: gradient fill */
    .stButton > button {
        background: linear-gradient(90deg, #7C3AED 0%, #A78BFA 100%);
        color: white;
        border: none;
        font-weight: 600;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #6D28D9 0%, #9333EA 100%);
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎙️ Duologue AI")

tab_create, tab_library = st.tabs(["Create", "My Episodes"])

with tab_create:
    st.write("Turn text, a PDF, an article URL, or just a topic into a two-host podcast conversation.")

    source_type = st.radio("Source", ["Paste text", "PDF", "URL", "Topic"], horizontal=True)

    pasted_text = ""
    uploaded_pdf = None
    url = ""
    topic = ""
    if source_type == "Paste text":
        pasted_text = st.text_area("Source text", height=250,
                                   placeholder="Paste an article or any text here...")
    elif source_type == "PDF":
        uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])
    elif source_type == "URL":
        url = st.text_input("Article URL", placeholder="https://...")
    else:  # Topic
        topic = st.text_input("Topic", max_chars=500,
                              placeholder="e.g. the history of the espresso machine")

    col1, col2, col3 = st.columns(3)
    tone_choice = col1.selectbox("Tone", list(TONES.keys()))
    length_choice = col2.selectbox("Length", list(LENGTHS.keys()))
    preset_choice = col3.selectbox("Hosts", list(HOST_PRESETS.keys()))

    if length_choice != "5 min":
        st.caption("Heads-up: on the free tier, longer scripts may truncate or hit the rate limit. 5 min is the reliable option for now.")

    if st.button("Generate podcast"):
        # --- per-session rate limit ---
        now = time.time()
        recent = [t for t in st.session_state.get("gen_times", []) if now - t < RATE_WINDOW]
        if len(recent) >= RATE_LIMIT:
            st.error(f"You've reached the limit of {RATE_LIMIT} generations per hour. Please try again later.")
            st.stop()
        st.session_state["gen_times"] = recent + [now]

        api_key = st.secrets["GROQ_API_KEY"]

        # --- Step 1: turn the chosen source into clean text ---
        with st.spinner("Preparing your source..."):
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
            elif source_type == "URL":
                if not url.strip():
                    st.warning("Please enter a URL first.")
                    st.stop()
                try:
                    source_text = extract_url_text(url.strip()).strip()
                except Exception:
                    logger.exception("URL extraction failed")
                    st.error("Couldn't fetch that URL. Please check it, or paste the text instead.")
                    st.stop()
            else:  # Topic
                if not topic.strip():
                    st.warning("Please enter a topic first.")
                    st.stop()
                try:
                    source_text = research_topic(topic.strip(), api_key).strip()
                except ScriptGenerationError:
                    logger.exception("Topic research failed")
                    st.error("Couldn't research that topic right now. Please try again.")
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

        # --- Step 2: script -> voices -> stitch -> save ---
        tone_desc = TONES[tone_choice]
        length = LENGTHS[length_choice]
        hosts = HOST_PRESETS[preset_choice]

        logger.info("Generation started | type=%s tone=%s length=%s preset=%s chars=%d",
                    source_type, tone_choice, length_choice, preset_choice, len(source_text))

        with st.spinner("Writing the script..."):
            try:
                title, turns = generate_script(source_text, tone_choice, tone_desc, length, hosts, api_key)
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
                audio_paths, tts_provider = synthesize_turns(turns, preset_choice)
            except AllTTSProvidersFailed:
                logger.exception("All TTS providers failed")
                st.error("Voice generation is unavailable right now. Please try again in a moment.")
                st.stop()

        if tts_provider != PRIMARY:
            logger.warning("TTS fell back to %s", tts_provider)
            st.info("Our main voices were unavailable, so this episode uses backup voices — they sound a bit different.")

        logger.info("Synthesis complete | provider=%s clips=%d", tts_provider, len(audio_paths))

        try:
            with st.spinner("Stitching the episode..."):
                episode_bytes, duration_seconds = stitch_audio(audio_paths)
            logger.info("Stitched episode | bytes=%d seconds=%d", len(episode_bytes), duration_seconds)
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

        # --- Save to the library (best-effort; a failure here must not block the result) ---
        episode_id = str(uuid.uuid4())
        try:
            client = get_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
            save_episode(client, episode_id, episode_bytes, {
                "title": title,
                "duration_seconds": duration_seconds,
                "source_type": source_type,
                "tone": tone_choice,
                "host_preset": preset_choice,
                "transcript": turns,
            })
            logger.info("Episode saved | id=%s", episode_id)
        except Exception:
            logger.exception("Saving episode failed")
            st.caption("(Couldn't save this to your library, but your episode is ready below.)")

        st.divider()
        st.subheader(title)
        st.audio(episode_bytes, format="audio/mp3")
        st.download_button(
            label="Download MP3",
            data=episode_bytes,
            file_name="duologue_episode.mp3",
            mime="audio/mp3",
        )

        with st.expander("Transcript"):
            for turn in turns:
                name = hosts["name_a"] if turn["speaker"] == "A" else hosts["name_b"]
                st.markdown(f"**{name}:** {turn['text']}")

with tab_library:
    st.write("Episodes created with Duologue AI.")

    # Icons are pure presentation, so they live here in the UI, not in config.py.
    PRESET_ICONS = {
        "Two Friends": "👥",
        "Expert + Novice": "🎓",
        "Skeptic + Believer": "⚖️",
    }

    try:
        lib_client = get_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        episodes = list_episodes(lib_client)
    except Exception:
        logger.exception("Loading library failed")
        st.error("Couldn't load the library right now. Please try again in a moment.")
        episodes = []

    if not episodes:
        st.caption("No episodes yet — create one in the Create tab.")
    else:
        cols = st.columns(2)
        for i, ep in enumerate(episodes):
            with cols[i % 2]:
                with st.container(border=True):
                    icon = PRESET_ICONS.get(ep.get("host_preset"), "🎙️")
                    secs_total = ep.get("duration_seconds") or 0
                    st.markdown(f"### {icon}")
                    st.markdown(f"**{ep['title']}**")
                    st.caption(
                        f"{ep.get('tone', '')} · {secs_total // 60}:{secs_total % 60:02d} · {ep['created_at'][:10]}"
                    )
                    try:
                        st.audio(get_audio_url(lib_client, ep["audio_path"]), format="audio/mp3")
                    except Exception:
                        logger.exception("Audio URL failed for %s", ep.get("id"))
                        st.caption("Audio unavailable.")