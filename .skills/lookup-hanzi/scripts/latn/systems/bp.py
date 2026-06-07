from ..config import LatnSystemConfig, PhoneticMapping


def create_config() -> LatnSystemConfig:
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
        initials=[
            "bbn",
            "ggn",
            "gg",
            "bb",
            "zz",
            "ln",
            "b",
            "p",
            "m",
            "d",
            "t",
            "n",
            "l",
            "g",
            "k",
            "h",
            "z",
            "c",
            "r",
            "s",
        ],
        nasal_endings=["m", "n", "ng"],
        entering_endings=["p", "t", "k", "h"],
        tone_mark_priority=["a", "oo", "e", "o", "u", "i", "n", "m"],
    )


SYSTEM_NAME = "BP"


def create_latn_norm_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={
            "b": "p",
            "p": "ph",
            "bb": "b",
            "bbn": "m",
            "ln": "n",
            "dd": "d",
            "d": "t",
            "t": "th",
            "g": "k",
            "k": "kh",
            "ggn": "ng",
            "gg": "g",
            "z": "ch",
            "c": "chh",
            "zz": "j",
        },
        vowel_map={"oo": "ou", "ao": "au"},
    )


def create_reverse_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={
            "p": "b",
            "ph": "p",
            "b": "bb",
            "m": "bbn",
            "n": "ln",
            "d": "dd",
            "t": "d",
            "th": "t",
            "k": "g",
            "kh": "k",
            "ng": "ggn",
            "g": "gg",
            "ch": "z",
            "chh": "c",
            "j": "zz",
        },
        vowel_map={"ou": "oo", "au": "ao"},
        nasal_prefix={"nn": ("n", ""), "nnh": ("n", "h")},
    )
