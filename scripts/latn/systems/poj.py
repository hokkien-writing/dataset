"""POJ (Pe̍h-ōe-jī) system configuration based on core.py."""

from scripts.latn.config import LatnSystemConfig


def create_config() -> LatnSystemConfig:
    # Concise vowel definition for tones 1-8
    vowels = {
        "a": "a á à a â ã ā a̍",
        "e": "e é è e ê ẽ ē e̍",
        "i": "i í ì i î ĩ ī i̍",
        "o": "o ó ò o ô õ ō o̍",
        "oo": "o͘ ó͘ ò͘ o͘ ô͘ õ͘ ō͘ o̍͘",
        "u": "u ú ù u û ũ ū u̍",
        "oa": "oa óa òa oa ôa õa ōa oa̍",
        "oe": "oe óe òe oe ôe õe ōe oe̍",
        "oai": "oai oái oài oai oâi oãi oāi oa̍i",
        "oan": "oan oán oàn oat oân oãn oān oa̍t",
        "oang": "oang oáng oàng oak oâng oãng oāng oa̍k",
        "ui": "ui úi ùi ui ûi ũi ūi ui̍",
        "iu": "iu iú iù iu iû iũ iū iu̍",
        "n": "n ń ǹ n n̂ ñ n̄ n̍",
        "m": "m ḿ m̀ m m̂ m̃ m̄ m̍",
    }

    return LatnSystemConfig.from_simple_vowels(
        name="POJ",
        description="Pe̍h-ōe-jī system",
        vowels=vowels,
        initials=[
            "chh",
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
        ],
        nasal_endings=["m", "n", "ng"],
        entering_endings=["p", "t", "k", "h"],
        tone_mark_priority=[
            "oai",
            "oan",
            "oang",
            "oa",
            "oe",
            "a",
            "oo",
            "e",
            "o",
            "ui",
            "iu",
            "u",
            "i",
            "n",
            "m",
        ],
        syllable_mappings={"ⁿ": "nn"},
    )
