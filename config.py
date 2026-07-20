"""Static configuration: tones, lengths, host presets, and limits.

Host presets hold personas + names only. Voice details live in the TTS
providers (tts_edge.py, tts_gtts.py), keyed by preset name — so each
provider decides how to voice the same set of hosts.
"""

MAX_SOURCE_CHARS = 12000  # keep the prompt within the free-tier token budget

TONES = {
    "Casual": "relaxed and friendly, like two friends talking over coffee",
    "Academic": "thoughtful and precise, like two experts discussing a paper, but still accessible",
    "Comedic": "playful and funny, quick with jokes and banter, while still covering the material",
    "Debate": "two hosts who respectfully disagree, each pushing back on the other's points",
}

LENGTHS = {
    "5 min":  {"minutes": 5,  "words": 700,  "max_tokens": 2500},
    "15 min": {"minutes": 15, "words": 2100, "max_tokens": 5000},
    "30 min": {"minutes": 30, "words": 4200, "max_tokens": 8000},
}

HOST_PRESETS = {
    "Two Friends": {
        "name_a": "Maya",
        "name_b": "Theo",
        "persona_a": "warm and curious, asks the questions listeners are thinking, and reacts openly ('wait, really?')",
        "persona_b": "easygoing and knowledgeable, explains things clearly with the occasional dry joke, and loves a good tangent",
    },
    "Expert + Novice": {
        "name_a": "Elena",
        "name_b": "Jai",
        "persona_a": "a patient expert who explains ideas clearly with vivid analogies and never talks down to anyone",
        "persona_b": "an enthusiastic newcomer who asks the beginner questions and lights up when something clicks",
    },
    "Skeptic + Believer": {
        "name_a": "Nora",
        "name_b": "Sam",
        "persona_a": "a fair-minded skeptic who probes claims and asks for evidence before accepting anything",
        "persona_b": "an optimist who's genuinely excited about the ideas and sees their potential",
    },
}