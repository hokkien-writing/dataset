"""POJ (Pe̍h-ōe-jī) system configuration based on core.py."""

from scripts.latn.config import LatnSystemConfig, PhoneticMapping


def create_config() -> LatnSystemConfig:
    # Concise vowel definition for tones 1-8
    vowels = {
        "a": "a á à a â ǎ ā a̍",
        "e": "e é è e ê ě ē e̍",
        "i": "i í ì i î ǐ ī i̍",
        "o": "o ó ò o ô ǒ ō o̍",
        "oo": "o͘ ó͘ ò͘ o͘ ô͘ ǒ͘ ō͘ o̍͘",
        "or": "o̤ ó̤ ò̤ o̤ ô̤ ǒ̤ ō̤ o̤̍",
        "u": "u ú ù u û ǔ ū u̍",
        "ur": "ṳ ṳ́ ṳ̀ ṳ ṳ̂ ṳ̌ ṳ̄ ṳ̍",
        "oa": "oa óa òa oa ôa ǒa ōa oa̍",
        "oe": "oe óe òe oe ôe ǒe ōe oe̍",
        "oai": "oai oái oài oai oâi oǎi oāi oa̍i",
        "oan": "oan oán oàn oat oân oǎn oān oa̍t",
        "oang": "oang oáng oàng oak oâng oǎng oāng oa̍k",
        "ui": "ui úi ùi ui ûi ǔi ūi ui̍",
        "iu": "iu iú iù iu iû iǔ iū iu̍",
        "n": "n ń ǹ n n̂ ň n̄ n̍",
        "m": "m ḿ m̀ m m̂ m̌ m̄ m̍",
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
            "or",
            "e",
            "o",
            "ui",
            "iu",
            "ur",
            "u",
            "i",
            "n",
            "m",
        ],
        syllable_mappings={"ⁿ": "nn", "̤": "r", "ṳ": "ur"},
    )


SYSTEM_NAME = "POJ"


def create_latn_norm_mapping() -> PhoneticMapping:
    return PhoneticMapping()


def create_reverse_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        vowel_map={"oo": "ou", "oa": "ua", "oe": "ue"},
    )


def create_rime_algebra() -> list[str]:
    return [
        "xform/ou/oo/",
        "xform/ua/oa/",
        "xform/ue/oe/",
        "derive/nn//",
    ]
