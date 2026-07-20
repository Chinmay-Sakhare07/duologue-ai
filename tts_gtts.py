"""gTTS fallback provider — one voice, accent-differentiated per host. Pure logic — no Streamlit.

Lower quality than Edge and cannot do distinct male/female voices — only accents.
Raises on failure (including Google's 429 rate limit) so the orchestrator can react.
"""

import os
import tempfile

from gtts import gTTS

# preset name -> (accent domain for host A, accent domain for host B)
# gTTS has no voice/gender selection; different tlds give different accents.
ACCENTS = {
    "Two Friends":        ("com", "co.uk"),
    "Expert + Novice":    ("co.uk", "com"),
    "Skeptic + Believer": ("com", "com.au"),
}


def synthesize(turns, preset_name):
    """Voice the whole episode with gTTS. Returns a list of MP3 paths, or raises."""
    tld_a, tld_b = ACCENTS[preset_name]
    out_dir = tempfile.mkdtemp(prefix="duologue_gtts_")
    paths = []
    for i, turn in enumerate(turns):
        tld = tld_a if turn["speaker"] == "A" else tld_b
        path = os.path.join(out_dir, f"turn_{i}.mp3")
        gTTS(text=turn["text"], lang="en", tld=tld).save(path)
        paths.append(path)
    return paths