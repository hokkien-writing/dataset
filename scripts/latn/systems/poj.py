"""POJ (Pe̍h-ōe-jī) system configuration based on core.py."""

from scripts.latn.config import LatnSystemConfig


def create_config() -> LatnSystemConfig:
    # Concise vowel definition for tones 1-8
    vowels = {
        "a": "a á à a â ã ā a̍",
        "e": "e é è e ê ẽ ē e̍",
        "i": "i í ì i î ĩ ī i̍",
        "o": "o ó ò o ô õ ō o̍",
        "oo": "o\u0358 ó\u0358 ò\u0358 o\u0358 ô\u0358 õ\u0358 ō\u0358 o̍\u0358",
        "u": "u ú ù u û ũ ū u̍",
        "ui": "ui uí uì ui uî uĩ uī ui̍",
        "iu": "iu iú iù iu iû iũ iū iu̍",
        "n": "n ń ǹ n n̂ ñ n̄ n̍",
        "m": "m ḿ m̀ m m̂ m̃ m̄ m̍",
    }

    return LatnSystemConfig.from_simple_vowels(
        name="POJ",
        description="Pe̍h-ōe-jī system (Taiwanese/Amoy)",
        vowels=vowels,
        nasal_endings=["m", "n", "ng"],
        entering_endings=["p", "t", "k", "h"],
        tone_mark_priority=["a", "oo", "e", "o", "ui", "iu", "u", "i", "n", "m"],
        syllable_mappings={"ⁿ": "nn"},
    )
