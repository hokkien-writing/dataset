"""BP (Bînpîn / Southern Min Pinyin) system configuration."""

from scripts.latn.config import LatnSystemConfig


def create_config() -> LatnSystemConfig:
    # Concise vowel definition for tones 1-8
    # BP uses Mandarin-style diacritics
    vowels = {
        "a": "ā ǎ à ā á a â á",
        "e": "ē ě è ē é e ê é",
        "i": "ī ǐ ì ī í i î í",
        "o": "ō ǒ ò ō ó o ô ó",
        "oo": "ōo ǒo òo ōo óo oo ôo óo",
        "u": "ū ǔ ù ū ú u û ú",
        "n": "n ň ǹ n ń n n̂ ń",
        "m": "m m̌ m̀ m ḿ m m̂ ḿ",
    }

    return LatnSystemConfig.from_simple_vowels(
        name="BP",
        description="Southern Min Pinyin (Bînpîn)",
        vowels=vowels,
        nasal_endings=["m", "n", "ng"],
        entering_endings=["p", "t", "k", "h"],
        tone_mark_priority=["a", "oo", "e", "o", "u", "i", "n", "m"],
    )
