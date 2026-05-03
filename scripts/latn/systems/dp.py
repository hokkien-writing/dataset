"""DP (Tiô-phêng / Teochew Pinyin) system configuration."""

from scripts.latn.config import LatnSystemConfig, PhoneticMapping


def create_config() -> LatnSystemConfig:
    # Concise vowel definition for tones 1-8
    # DP usually uses numerical tones (1-8)
    vowels = {
        "a": "a1 a2 a3 a4 a5 a6 a7 a8",
        "e": "e1 e2 e3 e4 e5 e6 e7 e8",
        "ê": "ê1 ê2 ê3 ê4 ê5 ê6 ê7 ê8",
        "i": "i1 i2 i3 i4 i5 i6 i7 i8",
        "o": "o1 o2 o3 o4 o5 o6 o7 o8",
        "u": "u1 u2 u3 u4 u5 u6 u7 u8",
        "n": "n1 n2 n3 n4 n5 n6 n7 n8",
        "m": "m1 m2 m3 m4 m5 m6 m7 m8",
    }

    return LatnSystemConfig.from_simple_vowels(
        name="DP",
        description="Teochew Pinyin (Diê⁵-pêng¹)",
        vowels=vowels,
        initials=[
            "gh",
            "bh",
            "ng",
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
        entering_endings=["b", "d", "g", "h"],
        tone_mark_priority=[],
        syllable_mappings={"ⁿ": "nn"},
        superscript_tones=True,
    )


SYSTEM_NAME = "DP"

def create_latn_norm_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={
            "b": "p", "p": "ph", "bh": "b",
            "d": "t", "t": "th",
            "g": "k", "k": "kh", "gh": "g",
            "z": "ch", "c": "chh", "r": "j",
        },
        vowel_map={"e": "ur", "ê": "e", "uê": "ue", "iê": "ie", "ao": "au"},
        ending_map={"b": "p", "d": "t", "g": "k"},
    )


def create_reverse_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={
            "p": "b", "ph": "p", "b": "bh",
            "t": "d", "th": "t",
            "k": "g", "kh": "k", "g": "gh",
            "ch": "z", "chh": "c", "j": "r",
        },
        vowel_map={"ur": "e", "e": "ê", "ue": "uê", "ie": "iê", "au": "ao"},
        ending_map={"p": "b", "t": "d", "k": "g"},
    )


def create_rime_algebra() -> list[str]:
    return [
        "xform/ur/v/",
        "xform/au/ao/",
        "derive/oinn/ainn/",
        "derive/ien/ian/",
        "derive/ied/iad/",
        "derive/([aeiu])n$/$1ng/",
        "derive/d$/g/",
        "derive/nn//",
    ]
