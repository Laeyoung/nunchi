"""Muse Spark structured-output schema (strict subset: every object has additionalProperties=false and lists all keys in required)."""

EXPLAIN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "korean_text": {"type": "string", "description": "The Korean text exactly as written in the selected region. Empty if none."},
        "romanization": {"type": "string", "description": "Revised Romanization, syllables separated by hyphens, e.g. il-bang-tong-haeng"},
        "pronunciation_hint": {"type": "string", "description": "How it sounds, written in the user's own script (katakana for Japanese, English spelling for English)."},
        "category": {"type": "string", "enum": ["road", "safety", "transit", "food", "shop", "daily_life", "other"]},
        "meaning": {"type": "string", "description": "What it says, in the user's language. One sentence."},
        "why_here": {"type": "string", "description": "Why this sign/text exists here: Korean law, custom or culture. Max 2 sentences, user's language."},
        "what_to_do": {"type": "string", "description": "Concrete action for a tourist right now. Max 2 sentences, user's language."},
        "native_bridge": {"type": "string", "description": "A delightful link to the user's native language (shared hanja for Japanese/Chinese, Konglish or loanwords for English). Empty string if nothing genuine."},
        "narration": {"type": "string", "description": "A warm 20-30 second spoken script in the user's language combining the above, like a friendly local guide. No markdown, no emojis."},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [
        "korean_text", "romanization", "pronunciation_hint", "category", "meaning",
        "why_here", "what_to_do", "native_bridge", "narration", "confidence",
    ],
}
