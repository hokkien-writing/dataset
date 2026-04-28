"""PUJ (Pe̍h-ūe-jī) system configuration.

Tone Mark Rules (from Handbook of the Swatow Vernacular 語料庫分析)
====================================================================

輔音聲母 舒聲：
  含 a → a:  ái, áu, iá, iám, iâng, ói, óu, ióu
  ua+尾 → a: uái, uân, uáng
  ua裸 → u:  úa, Búa, Hûa
  uaⁿ → u:  Húaⁿ, Kùaⁿ (語料84%)
  ue+尾 → e: uéng
  ie → e:   ié, ién, iéⁿ
  無a雙元音 → 前元音: iú, úi, úe, óu, ói
  ng → n,  m → m

零聲母 舒聲 (vowel_initial_overrides)：
  ua → a:  uá, uâ, uà
  au → u:  aú, aû, aù
  ue → e:  ué, uê, uē
  uaⁿ → a: uáⁿ, uâⁿ, uàⁿ

入聲（韻尾 p/t/k/h）：
  標於韻尾前元音（從右往左掃描）
  ua̍h, ue̍h, ia̍h, ie̍h, aih→i, oih→i, auh→u
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
        "uaⁿ": "uaⁿ úaⁿ ùaⁿ uaⁿ ûaⁿ ũaⁿ ūaⁿ u̍aⁿ",
        "uai": "uai uái uài uai uâi uãi uāi ua̍i",
        "uan": "uan uán uàn uan uân uãn uān ua̍n",
        "uang": "uang uáng uàng uang uâng uãng uāng ua̍ng",
        "ueng": "ueng uéng uèng ueng uêng uẽng uēng ue̍ng",
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
            "uaⁿ",
            "ua",
            "ueng",
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
