"""PUJ (Pe̍h-ūe-jī) system configuration.

Tone Mark Placement Rules (歸納自 Handbook of the Swatow Vernacular 8000+ 條資料)
================================================================================

舒聲（非入聲）：

  含 a 的複合韻 → 標於 a
    ai, au, ia, iam, iang, oi, ou, iou, etc.
    例: ái, áu, iá, iám, iâng, ói, óu, ióu

  ua（裸，無韻尾）→ 標於 u
    例: úa, úe, úi

  ua + 韻尾 (i/n/ng) → 標於 a
    uai, uan, uang
    例: uái, uân, uáng

  ie 系列 → 標於 e
    例: ié, ién, iéⁿ

  ie 以外的無 a 雙元音 → 標於前一個元音
    iu → u (iú), ui → u (úi), ue → u (úe), ou → o (óu), oi → o (ói)

  m（自成音節）→ 標於 m
    例: ḿ

  ng → 標於 n（雙字母標於前一個字母）
    例: n̂g, ńg

入聲（韻尾 p/t/k/h）：

  標於韻尾前一個元音
    uah → a (ua̍h), ueh → e (ue̍h), aih → i (ai̍h), oih → i (oi̍h)
    iah → a (ia̍h), ieh → e (ie̍h), auh → u (au̍h), eh → e (e̍h)

鼻化 ⁿ 視同韻尾，uaⁿ 與 uan 同規則標於 a
    uaⁿ → a (kuáⁿ), aiⁿ → a (áiⁿ), oiⁿ → o (óiⁿ)
"""

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
        "ua": "ua úa ùa ua ûa ũa ūa u̍a",
        "uai": "uai uái uài uai uâi uãi uāi ua̍i",
        "uan": "uan uán uàn uan uân uãn uān ua̍n",
        "uang": "uang uáng uàng uang uâng uãng uāng ua̍ng",
    }

    return LatnSystemConfig.from_simple_vowels(
        name="PUJ",
        description="Tiê-chiu Pe̍h-ūe-jī romanization system",
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
        tone_mark_priority=[
            "uai",
            "uan",
            "uang",
            "ua",
            "a",
            "o",
            "ur",
            "u",
            "e",
            "i",
            "n",
            "m",
        ],
        entering_tone_mark_before_ending=True,
        vowel_initial_overrides={
            "au1": "au",
            "au2": "aú",
            "au3": "aù",
            "au4": "au",
            "au5": "aû",
            "au6": "aũ",
            "au7": "aū",
            "au8": "au̍",
            "ua1": "ua",
            "ua2": "uá",
            "ua3": "uà",
            "ua4": "ua",
            "ua5": "uâ",
            "ua6": "uã",
            "ua7": "uā",
            "ua8": "ua̍",
            "ue1": "ue",
            "ue2": "ué",
            "ue3": "uè",
            "ue4": "ue",
            "ue5": "uê",
            "ue6": "uẽ",
            "ue7": "uē",
            "ue8": "ue̍",
            "uaⁿ1": "uaⁿ",
            "uaⁿ2": "uáⁿ",
            "uaⁿ3": "uàⁿ",
            "uaⁿ4": "uaⁿ",
            "uaⁿ5": "uâⁿ",
            "uaⁿ6": "uãⁿ",
            "uaⁿ7": "uāⁿ",
            "uaⁿ8": "ua̍ⁿ",
        },
        syllable_mappings={"ⁿ": "nn"},
    )


def create_variant_rules():
    return {
        "ṳ": ["ṳ", "u", "i"],
        "oiⁿ": ["oiⁿ", "aiⁿ"],
        "t$": ["k"],
        "n$": ["ng"],
    }
