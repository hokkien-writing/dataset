"""PUJ (Pe̍h-ūe-jī) system configuration."""

from scripts.latn.config import LatnSystemConfig


def create_config() -> LatnSystemConfig:
    # Concise vowel definition for tones 1-8
    vowels = {
        "a": "a á à a â ã ā a̍",
        "e": "e é è e ê ẽ ē e̍",
        "i": "i í ì i î ĩ ī i̍",
        "o": "o ó ò o ô õ ō o̍",
        "u": "u ú ù u û ũ ū u̍",
        "ur": "ṳ ṳ́ ṳ̀ ṳ ṳ̂ ṳ̃ ṳ̄ ṳ̍",
        "n": "n ń ǹ n n̂ ñ n̄ n̍",
        "m": "m ḿ m̀ m m̂ m̃ m̄ m̍",
    }

    return LatnSystemConfig.from_simple_vowels(
        name="PUJ",
        description="Pe̍h-uē-jī romanization system (han)",
        vowels=vowels,
        initials=[
            "tsh",
            "chh",
            "ts",
            "ch",
            "ph",
            "th",
            "kh",
            "ng",
            "p",
            "b",
            "m",
            "t",
            "n",
            "l",
            "k",
            "g",
            "h",
            "s",
            "j",
            "z",
        ],
        nasal_endings=["m", "n", "ng"],
        entering_endings=["p", "t", "k", "h"],
        tone_mark_priority=["a", "o", "e", "ur", "u", "i", "n", "m"],
        syllable_mappings={"ⁿ": "nn"},
    )
