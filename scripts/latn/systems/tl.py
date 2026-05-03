"""TL (Tâi-lô) system configuration."""

from scripts.latn.config import LatnSystemConfig, PhoneticMapping


def create_config() -> LatnSystemConfig:
    # Concise vowel definition for tones 1-8
    vowels = {
        "a": "a á à a â ǎ ā a̍",
        "e": "e é è e ê ě ē e̍",
        "i": "i í ì i î ǐ ī i̍",
        "o": "o ó ò o ô ǒ ō o̍",
        "oo": "oo óo òo oo ôo ǒo ōo o̍o",
        "u": "u ú ù u û ǔ ū u̍",
        "n": "n ń ǹ n n̂ ň n̄ n̍",
        "m": "m ḿ m̀ m m̂ m̌ m̄ m̍",
    }

    return LatnSystemConfig.from_simple_vowels(
        name="TL",
        description="Taiwanese Romanization System (Tâi-lô)",
        vowels=vowels,
        initials=[
            "tsh",
            "ts",
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
        ],
        nasal_endings=["m", "n", "ng"],
        entering_endings=["p", "t", "k", "h"],
        tone_mark_priority=["a", "oo", "e", "o", "u", "i", "n", "m"],
        syllable_mappings={"ⁿ": "nn"},
    )


SYSTEM_NAME = "TL"

def create_latn_norm_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={"ts": "ch", "tsh": "chh"},
    )


def create_reverse_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={"ch": "ts", "chh": "tsh"},
    )


def create_rime_algebra() -> list[str]:
    return [
        "derive/nn//"
    ]
