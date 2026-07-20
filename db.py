"""Supabase persistence: upload the episode MP3 and save/read its metadata. Pure logic — no Streamlit."""

from supabase import create_client

BUCKET = "episodes"


def get_client(url, key):
    """Create a Supabase client."""
    return create_client(url, key)


def save_episode(client, episode_id, mp3_bytes, metadata):
    """Upload the MP3 to Storage and insert a metadata row. Returns the storage path, or raises."""
    audio_path = f"{episode_id}.mp3"

    client.storage.from_(BUCKET).upload(
        audio_path,
        mp3_bytes,
        {"content-type": "audio/mpeg"},
    )

    client.table("episodes").insert({
        "id": episode_id,
        "title": metadata["title"],
        "duration_seconds": metadata["duration_seconds"],
        "source_type": metadata["source_type"],
        "tone": metadata["tone"],
        "host_preset": metadata["host_preset"],
        "transcript": metadata["transcript"],
        "audio_path": audio_path,
    }).execute()

    return audio_path


def list_episodes(client, limit=50):
    """Return recent episodes, newest first."""
    res = (
        client.table("episodes")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


def get_audio_url(client, audio_path):
    """Public URL for a stored episode MP3 (the bucket is public)."""
    return client.storage.from_(BUCKET).get_public_url(audio_path)