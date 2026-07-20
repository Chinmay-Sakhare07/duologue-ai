"""Stitch per-turn MP3s into one episode using pydub. Pure logic — no Streamlit."""

import os
import tempfile

from pydub import AudioSegment


def stitch_audio(audio_paths, gap_ms=300):
    """Combine per-turn MP3s into one MP3 with silence gaps. Returns (bytes, duration_seconds)."""
    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=gap_ms)
    for path in audio_paths:
        turn_audio = AudioSegment.from_mp3(path)
        combined += turn_audio + silence

    out_path = os.path.join(tempfile.gettempdir(), "duologue_episode.mp3")
    combined.export(out_path, format="mp3", bitrate="128k")
    with open(out_path, "rb") as f:
        data = f.read()

    duration_seconds = round(len(combined) / 1000)
    return data, duration_seconds