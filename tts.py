"""Text-to-speech via Edge TTS. Isolated so the backend can be swapped. Pure logic — no Streamlit."""

import asyncio
import os
import tempfile

import edge_tts


async def _synthesize_all(turns, voice_a, voice_b, out_dir):
    paths = []
    for i, turn in enumerate(turns):
        voice = voice_a if turn["speaker"] == "A" else voice_b
        path = os.path.join(out_dir, f"turn_{i}.mp3")
        communicate = edge_tts.Communicate(turn["text"], voice)
        await communicate.save(path)
        paths.append(path)
    return paths


def synthesize_turns(turns, voice_a, voice_b):
    """Generate one MP3 per turn. Returns a list of file paths in a temp dir."""
    out_dir = tempfile.mkdtemp(prefix="duologue_")
    return asyncio.run(_synthesize_all(turns, voice_a, voice_b, out_dir))