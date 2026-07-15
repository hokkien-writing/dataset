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

import re
import unicodedata

from scripts.latn.config import LatnSystemConfig, PhoneticMapping

_BREVE_TONE6 = {
    "\u0103": "a",
    "\u0115": "e",
    "\u012d": "i",
    "\u014f": "o",
    "\u016d": "u",
}

_CONSONANT_RE = re.compile(r"chh|ch|c(?![h])")
_OA_COMBINING_RE = re.compile(r"o([\u0300-\u036f]*)a")
_HYPHEN_RE = re.compile(r"(-)")

_TONE_MARK_MAP = {
    "\u0301": 2,
    "\u0300": 3,
    "\u0302": 5,
    "\u0303": 6,
    "\u0304": 7,
    "\u030d": 8,
}


_TONE_MARK_CHARS = {"\u0301", "\u0300", "\u0302", "\u0303", "\u0304", "\u030d"}


def _to_fielde_keyboard(word: str) -> str:
    if not word:
        return word
    parts = _HYPHEN_RE.split(word)
    result_parts = []
    for part in parts:
        if part == "-":
            result_parts.append("-")
        elif part:
            result_parts.append(_to_fielde_syllable(part))
    return "".join(result_parts)


def _to_fielde_syllable(syllable: str) -> str:
    if not syllable:
        return syllable

    decomposed = unicodedata.normalize("NFD", syllable)
    tone = None
    has_breve = False

    for ch in decomposed:
        if ch in _TONE_MARK_MAP:
            tone = _TONE_MARK_MAP[ch]
        elif ch == "\u0306":
            has_breve = True

    result = []
    for ch in decomposed:
        cat = unicodedata.category(ch)
        if cat.startswith("M"):
            if ch in _TONE_MARK_CHARS:
                continue
            result.append(ch)
            continue
        if has_breve and tone is None and ch == "\u0306":
            result.append("\u0303")
        else:
            result.append(ch)

    base = "".join(result)

    consonant = ""
    nucleus = base
    for ini in ["chh", "ch", "ts", "tsh", "ph", "th", "kh", "ng",
                 "p", "b", "m", "t", "n", "l", "k", "g", "h", "s", "j", "z", "c"]:
        if base.startswith(ini) and len(base) > len(ini):
            first_after = base[len(ini)]
            if first_after not in "aeiou":
                continue
            consonant = ini
            nucleus = base[len(ini):]
            break

    stripped = []
    for ch in nucleus:
        cat = unicodedata.category(ch)
        if cat.startswith("M") and ch in _TONE_MARK_CHARS:
            continue
        stripped.append(ch)
    nucleus = "".join(stripped)

    if has_breve and tone is None:
        nucleus = nucleus.replace("\u0306", "\u0303")
        tone = 6

    o_diaeresis = "o\u0324" in nucleus
    if o_diaeresis:
        nucleus = nucleus.replace("\u0324", "")
    elif nucleus.startswith("o") and not any(c in "aeiou" for c in nucleus[1:]):
        nucleus = "ou" + nucleus[1:]

    if tone == 5 and nucleus and nucleus[-1] in "ptkh":
        tone = 8

    return f"{consonant}{nucleus}{tone or 1}"


def _normalize_fielde_input(text: str) -> str:
    return text


class PUJSystem:
    name = "PUJ"

    def create_config(self) -> LatnSystemConfig:
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

    def create_latn_norm_mapping(self) -> PhoneticMapping:
        return PhoneticMapping(
            initial_map={"ts": "ch", "tsh": "chh", "z": "j"},
            vowel_map={"oo": "ou", "oa": "ua", "oe": "ue"},
        )

    def create_reverse_mapping(self) -> PhoneticMapping:
        return PhoneticMapping(
            initial_map={
                "ch": lambda init, vowel: "ch" if vowel and vowel[0] in ("i", "e") else "ts",
                "chh": lambda init, vowel: "chh" if vowel and vowel[0] in ("i", "e") else "tsh",
                "j": lambda init, vowel: "j" if vowel and vowel[0] in ("i", "e") else "z",
            },
        )

    def create_rime_algebra(self) -> list[str]:
        return [
            "derive/^ch/ts/",
            "derive/^j/z/",
            "derive/oinn$/ainn/",
            "derive/ien$/ian/",
            "derive/iet/iat/",
            "derive/([aeiu])n$/$1ng/",
            "derive/t$/k/",
            "derive/nn//",
        ]

    def create_variant_rules(self) -> dict:
        return {
            "ṳ": ["ṳ", "u", "i"],
            "oiⁿ": ["oiⁿ", "aiⁿ"],
            "t$": ["k"],
            "n$": ["ng"],
        }


class FieldePUJSystem(PUJSystem):
    variant = "fielde"

    def __init__(self):
        from scripts.latn import create_converter
        self._converter = create_converter("PUJ", system_class=self)

    def create_config(self) -> LatnSystemConfig:
        config = super().create_config()
        config.variant = self.variant
        config.initials.insert(config.initials.index("ch") + 1, "c")
        config.normalize_input = _normalize_fielde_input

        for k in list(config.vowel_dict):
            config.vowel_dict[k] = unicodedata.normalize("NFC", config.vowel_dict[k])

        config.reverse_vowel_map = {}
        for key, marked_vowel in config.vowel_dict.items():
            if len(key) >= 2 and key[-1].isdigit():
                tone_num = int(key[-1])
                base_vowel = key[:-1]
                if marked_vowel not in config.reverse_vowel_map:
                    config.reverse_vowel_map[marked_vowel] = []
                config.reverse_vowel_map[marked_vowel].append((base_vowel, tone_num))

        for breve_char, base in _BREVE_TONE6.items():
            config.reverse_vowel_map[breve_char] = [(base, 6)]

        config.reverse_vowel_map = dict(
            sorted(
                config.reverse_vowel_map.items(),
                key=lambda x: len(x[0]),
                reverse=True,
            )
        )

        return config

    def create_latn_norm_mapping(self) -> PhoneticMapping:
        mapping = super().create_latn_norm_mapping()
        mapping.initial_map["c"] = "ch"
        return mapping

    def create_reverse_mapping(self) -> PhoneticMapping:
        mapping = super().create_reverse_mapping()
        mapping.vowel_map["ou"] = "o"
        return mapping

    def normalize_book_text(self, text: str) -> str:
        text = unicodedata.normalize("NFD", text).replace("w", "u")
        text = text.replace("\u0306", "\u0303")

        text = _normalize_fielde_input(text)

        def _fix_consonant(m: re.Match) -> str:
            c = m.group()
            nxt = text[m.end():m.end() + 1]
            if c in ("ch", "chh"):
                return "chh" if nxt in "ie" else "tsh"
            if c == "c":
                return "ch" if nxt in "ie" else "ts"
            return c

        text = _CONSONANT_RE.sub(_fix_consonant, text)
        text = _OA_COMBINING_RE.sub(lambda m: "u" + (m.group(1) or "") + "a", text)
        text = unicodedata.normalize("NFC", text)

        words = text.split(" ")
        result = []
        for word in words:
            kb = _to_fielde_keyboard(word)
            hw = self._converter.to_handwriting(kb)
            result.append(hw)
        return " ".join(result)


# ── Goddard (1883 A Chinese and English Vocabulary in the Tie-chiu Dialect) ──

GODDARD_TONE_MAP: dict[str, int] = {
    "1": 1,
    "-1": 5,
    "2": 2,
    "3": 7,
    "3-": 3,
    "-3": 6,
    "4": 4,
    "-4": 8,
}

_GODDARD_VOWEL_MAP: dict[str, str] = {
    "\u00e1": "a",   # á
    "\u00c1": "a",   # Á
    "\u00e0": "a",   # à
    "\u00c0": "a",   # À
    "\u00f3": "o",   # ó
    "\u00d3": "o",   # Ó
    "\u00f9": "ur",  # ù
    "\u00d9": "ur",  # Ù
    "\u00fa": "u",   # ú
    "\u00da": "u",   # Ú
    "\u00e9": "e",   # é
    "\u00c9": "e",   # É
    "\u00ed": "i",   # í
    "\u00cd": "i",   # Í
}

_GODDARD_INITIALS: list[tuple[str, str | None, str]] = [
    ("ch\u02bd", "chh", "tsh"),
    ("ch\u02bc", "chh", "tsh"),
    ("ch\u2019", "chh", "tsh"),
    ("ch'", "chh", "tsh"),
    ("ch", "ch", "ts"),
    ("k\u02bd", None, "kh"),
    ("k\u02bc", None, "kh"),
    ("k\u2019", None, "kh"),
    ("k'", None, "kh"),
    ("k", None, "k"),
    ("p\u02bd", None, "ph"),
    ("p\u02bc", None, "ph"),
    ("p\u2019", None, "ph"),
    ("p'", None, "ph"),
    ("p", None, "p"),
    ("t\u02bd", None, "th"),
    ("t\u02bc", None, "th"),
    ("t\u2019", None, "th"),
    ("t'", None, "th"),
    ("t", None, "t"),
    ("\u02bd", None, "h"),   # ʻ → h (standalone aspiration)
    ("\u02bc", None, "h"),  # ʼ → h
    ("\u2019", None, "h"),  # ' → h
    ("'", None, "h"),       # ' → h
    ("ng", None, "ng"),
    ("b", None, "b"),
    ("g", None, "g"),
    ("h", None, "h"),
    ("j", None, "j"),
    ("l", None, "l"),
    ("m", None, "m"),
    ("n", None, "n"),
    ("s", None, "s"),
    ("z", None, "z"),
]


def goddard_to_keyboard(goddard_word: str, tone_str: str) -> str:
    word = unicodedata.normalize("NFC", goddard_word).lower()
    initial_puj = ""
    rhyme = word
    for g_init, i_e_map, other_map in _GODDARD_INITIALS:
        if word.startswith(g_init):
            after = word[len(g_init):]
            first_vowel = _first_vowel_char(after)
            if i_e_map is not None:
                initial_puj = i_e_map if first_vowel in ("i", "e") else other_map
            else:
                initial_puj = other_map
            rhyme = after
            break
    rhyme = rhyme.replace("w", "u")
    # Goddard Y at start of rhyme = vowel i. Yiak → iak, Yok → iok.
    if rhyme.startswith("y"):
        if len(rhyme) > 1 and rhyme[1] == "i":
            rhyme = rhyme[1:]  # yiak → iak (y=i, i already present)
        else:
            rhyme = "i" + rhyme[1:]  # yok → iok
    rhyme = rhyme.replace("\u1d58", "")  # ᵘ marks syllabic ng, not vowel quality
    nasal = "\u207f" in rhyme
    if nasal:
        rhyme = rhyme.replace("\u207f", "")
    # map Goddard vowel quality chars → PUJ base vowels
    # Track whether the final o was accented (ó→o) or bare (o→ou).
    had_marked_o = False
    rhyme_chars = []
    for ch in rhyme:
        mapped = _GODDARD_VOWEL_MAP.get(ch, ch)
        if mapped == "o" and ch != "o":
            had_marked_o = True
        rhyme_chars.append(mapped)
    rhyme = "".join(rhyme_chars)
    # Goddard's io → iou, ao → aou, etc. (o preceded by another vowel).
    # Bare o → ou; accented ó → o (diacritic resolves the ambiguity).
    if rhyme and rhyme[-1] == "o":
        if len(rhyme) >= 2 and rhyme[-2] in "aeiou":
            rhyme = rhyme[:-1] + "ou"
        elif len(rhyme) == 1 and not had_marked_o:
            rhyme = "ou"
    if nasal:
        rhyme += "nn"
    # Strip trailing h: in Goddard's orthography h can mark vowel quality,
    # but entering tone words without p/t/k end in glottal stop (h in PUJ).
    had_h = rhyme.endswith("h")
    rhyme = rhyme.rstrip("h")
    tone_num = GODDARD_TONE_MAP.get(tone_str, 1)
    # For entering tone words without p/t/k, restore h (glottal stop)
    if tone_num in (4, 8) and not rhyme[-1:] in ("p", "t", "k"):
        rhyme += "h"
    return f"{initial_puj}{rhyme}{tone_num}"


def _first_vowel_char(s: str) -> str:
    for ch in s:
        base = _GODDARD_VOWEL_MAP.get(ch, ch)
        if base in "aeiou\u1e73":
            return base
    return ""


# ── Module-level exports ──

SYSTEM_NAME = "PUJ"

_system = PUJSystem()


def create_config() -> LatnSystemConfig:
    return _system.create_config()


def create_latn_norm_mapping() -> PhoneticMapping:
    return _system.create_latn_norm_mapping()


def create_reverse_mapping() -> PhoneticMapping:
    return _system.create_reverse_mapping()


def create_rime_algebra() -> list[str]:
    return _system.create_rime_algebra()


def create_variant_rules() -> dict:
    return _system.create_variant_rules()
