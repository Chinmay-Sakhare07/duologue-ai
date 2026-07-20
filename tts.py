"""TTS orchestration: try providers in order, first success wins (graceful degradation).

Pure logic — no Streamlit. Returns which provider succeeded so the UI can note a fallback.
Adding a third provider is a one-line change to PROVIDERS.
"""

import tts_edge
import tts_gtts

# Ordered fallback chain: best quality first, sturdier fallback second.
PROVIDERS = [
    ("Edge TTS", tts_edge.synthesize),
    ("gTTS", tts_gtts.synthesize),
]

PRIMARY = PROVIDERS[0][0]


class AllTTSProvidersFailed(Exception):
    """Raised when every provider in the chain failed."""


def synthesize_turns(turns, preset_name):
    """Voice the whole episode. Returns (mp3_paths, provider_name). Raises AllTTSProvidersFailed."""
    errors = []
    for name, provider in PROVIDERS:
        try:
            paths = provider(turns, preset_name)
            return paths, name
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise AllTTSProvidersFailed(" | ".join(errors))