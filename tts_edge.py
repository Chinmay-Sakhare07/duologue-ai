"""Edge TTS provider — distinct neural voices per host. Pure logic — no Streamlit.

Raises on failure so the orchestrator can fall back to the next provider.
"""

import asyncio
import os
import tempfile

import edge_tts

# preset name -> (voice for host A, voice for host B)
VOICES = {
    "Two Friends":        ("en-US-AriaNeural", "en-US-GuyNeural"),
    "Expert + Novice":    ("en-US-JennyNeural", "en-US-DavisNeural"),
    "Skeptic + Believer": ("en-US-EmmaNeural", "en-US-BrianNeural"),
}


async def _synthesize_all(turns, voice_a, voice_b, out_dir):
    paths = []
    for i, turn in enumerate(turns):
        voice = voice_a if turn["speaker"] == "A" else voice_b
        path = os.path.join(out_dir, f"turn_{i}.mp3")
        communicate = edge_tts.Communicate(turn["text"], voice)
        await communicate.save(path)
        paths.append(path)
    return paths


def synthesize(turns, preset_name):
    """Voice the whole episode with Edge TTS. Returns a list of MP3 paths, or raises."""
    voice_a, voice_b = VOICES[preset_name]
    out_dir = tempfile.mkdtemp(prefix="duologue_edge_")
    return asyncio.run(_synthesize_all(turns, voice_a, voice_b, out_dir))