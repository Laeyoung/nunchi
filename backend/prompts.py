LANG_NAMES = {"ja": "Japanese", "en": "English", "zh": "Simplified Chinese", "ko": "Korean"}

BRIDGE_RULES = {
    "ja": "For Japanese users: if the Korean word is Sino-Korean, show the hanja (e.g. 일방통행 = 一方通行) and say whether Japanese uses the same word, a slightly different one (e.g. 출입금지 出入禁止 vs Japanese 立入禁止), or none. Mention that the sound is similar when it genuinely is.",
    "en": "For English users: point out Konglish or English loanwords (e.g. 핸드폰 'hand phone', 서비스 'service' = free extra) or a simple tip for reading the Hangul letters in it.",
    "zh": "For Chinese users: show the hanja form and note any difference in meaning or usage from modern Chinese.",
    "ko": "For Korean users: give an interesting origin or trivia.",
}

SYSTEM = """You are a friendly local guide in Korea who explains Korean signs, menus and notices to foreign travellers.
Rules:
- Read only what is actually visible. Never invent text that is not in the image.
- The tapped region may cut words off at its edges. Use the full photo to read the complete word or phrase, and report korean_text as complete words, never fragments.
- If the text is unreadable or you are unsure of the cultural reason, set confidence to "low" and say so plainly in the narration instead of guessing.
- Be concrete and practical: the traveller is standing in front of this right now.
- Keep facts about Korean law and customs conservative and widely known.
- Write every explanation field in the user's language. korean_text stays in Korean."""


def user_prompt(lang: str, has_full: bool = True, has_crop: bool = True) -> str:
    name = LANG_NAMES.get(lang, "English")
    if has_full and has_crop:
        images = ("The first image is the full photo for context; the second image is the region they tapped. "
                  "Explain the Korean text in the tapped region.")
    elif has_crop:
        images = "The image is the region of the photo they tapped. Explain the Korean text in it."
    else:
        images = "The image is the full photo. Explain the most prominent Korean text in it."
    return f"The traveller speaks {name}. {images}\n{BRIDGE_RULES.get(lang, BRIDGE_RULES['en'])}"
