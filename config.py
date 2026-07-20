"""Static configuration: tones, lengths, host presets, and limits."""

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
        "a": "warm and curious, asks good follow-up questions",
        "b": "knowledgeable, explains clearly, cracks the occasional joke",
        "voice_a": "en-US-AriaNeural",
        "voice_b": "en-US-GuyNeural",
    },
    "Expert + Novice": {
        "a": "an expert who explains ideas clearly and patiently",
        "b": "an enthusiastic novice who asks the questions a beginner would ask",
        "voice_a": "en-US-JennyNeural",
        "voice_b": "en-US-DavisNeural",
    },
    "Skeptic + Believer": {
        "a": "a skeptic who questions claims and asks for evidence",
        "b": "a believer who is enthusiastic and optimistic about the topic",
        "voice_a": "en-US-EmmaNeural",
        "voice_b": "en-US-BrianNeural",
    },
}