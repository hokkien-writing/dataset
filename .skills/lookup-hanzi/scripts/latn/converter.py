import re
import unicodedata
from abc import ABC
from .config import LatnSystemConfig

_SUPERSCRIPT_DIGITS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
_NORMAL_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


class LatnConverter(ABC):
    def __init__(self, config: LatnSystemConfig):
        self.config = config
        self.vowel_dict = config.vowel_dict
        self.nasal_endings = config.nasal_endings
        self.entering_endings = config.entering_endings
        self.reverse_vowel_map = config.reverse_vowel_map or {}
        self.reverse_complex_map = config.reverse_complex_map or {}

        self.tone_mark_priority = config.tone_mark_priority

        self._reverse_vowel_index: dict[str, list[tuple[str, list]]] = {}
        for k, v in self.reverse_vowel_map.items():
            first = k[0] if k else ""
            if first not in self._reverse_vowel_index:
                self._reverse_vowel_index[first] = []
            self._reverse_vowel_index[first].append((k, v))
        for first in self._reverse_vowel_index:
            self._reverse_vowel_index[first].sort(key=lambda x: len(x[0]), reverse=True)

        self._keyboard_cache: dict[str, str] = {}
        self._handwriting_cache: dict[str, str] = {}
        self._keyboard_syllable_cache: dict[str, str] = {}
        self._handwriting_syllable_cache: dict[str, str] = {}

    _KEYBOARD_TOKEN_RE = re.compile(
        r"[a-zA-Z\u00B2\u00B3\u00B9\u00C0-\u024F\u0300-\u036F\u1E00-\u1EFF\u2070-\u207F'-]+\d*|\s+|[^\s]"
    )
    _KEYBOARD_WORD_RE = re.compile(
        r"[a-zA-Z\u00B2\u00B3\u00B9\u00C0-\u024F\u0300-\u036F\u1E00-\u1EFF\u2070-\u207F'-]+\d*"
    )

    def to_keyboard(self, text: str) -> str:
        cached = self._keyboard_cache.get(text)
        if cached is not None:
            return cached
        tokens = self._KEYBOARD_TOKEN_RE.findall(text)
        converted_tokens = []
        for token in tokens:
            if token.isspace():
                converted_tokens.append(token)
                continue
            if self._KEYBOARD_WORD_RE.match(token):
                converted_tokens.append(self._to_keyboard_word(token))
            else:
                converted_tokens.append(token)

        result = "".join(converted_tokens)
        self._keyboard_cache[text] = result
        return result

    def _to_keyboard_word(self, word: str) -> str:
        parts = self._HYPHEN_SPLIT_RE.split(word)
        converted_parts = []

        for part in parts:
            if part == "-":
                converted_parts.append("-")
            elif part:
                is_upper = part.isupper()
                is_title = part[0].isupper() if part else False

                converted = self._to_keyboard_syllable(part.lower())

                if is_upper and len(converted) > 0:
                    converted = converted.upper()
                elif is_title and len(converted) > 0:
                    converted = converted.capitalize()

                converted_parts.append(converted)

        return "".join(converted_parts)

    _DIGIT_RE = re.compile(r"\d")
    _HYPHEN_SPLIT_RE = re.compile(r"(-)")

    def _to_keyboard_syllable(self, syllable: str) -> str:
        cached = self._keyboard_syllable_cache.get(syllable)
        if cached is not None:
            return cached
        result = self._to_keyboard_syllable_inner(syllable)
        self._keyboard_syllable_cache[syllable] = result
        return result

    def _to_keyboard_syllable_inner(self, syllable: str) -> str:
        if not syllable:
            return ""

        syllable = unicodedata.normalize("NFC", syllable)

        if self.config.superscript_tones:
            syllable = syllable.translate(_NORMAL_DIGITS)

        if any(c.isdigit() for c in syllable):
            tone_match = re.search(r"(\d)$", syllable)
            tone_num = tone_match.group(1) if tone_match else None
            if tone_num:
                syllable = syllable[:-1]

            for marked, keyboard in self.config.syllable_mappings.items():
                if marked in syllable:
                    syllable = syllable.replace(marked, keyboard)

            if tone_num:
                syllable = syllable + tone_num

            if tone_num:
                syllable = syllable.translate(_NORMAL_DIGITS)

            has_diacritics = any(
                unicodedata.category(c).startswith("M") for c in syllable
            )
            if not has_diacritics:
                return syllable

        original_syllable = syllable
        tone_num = None

        found_complex = False
        for length in range(len(syllable), 0, -1):
            suffix = syllable[-length:]
            if suffix in self.reverse_complex_map:
                base_suffix, t = self.reverse_complex_map[suffix]
                tone_num = t
                syllable = syllable[:-length] + base_suffix
                found_complex = True
                break

        all_tone_options = []
        if not found_complex:
            new_syllable_chars = []
            i = 0
            all_tone_options = []
            while i < len(syllable):
                found_vowel = False
                first_char = syllable[i]
                candidates = self._reverse_vowel_index.get(first_char, ())
                for marked_vowel, options in candidates:
                    if syllable.startswith(marked_vowel, i):
                        end_pos = i + len(marked_vowel)
                        if end_pos < len(syllable) and unicodedata.category(
                            syllable[end_pos]
                        ).startswith("M"):
                            continue
                        has_diacritics = unicodedata.normalize(
                            "NFD", marked_vowel
                        ) != marked_vowel or any(
                            unicodedata.category(c).startswith("M")
                            for c in marked_vowel
                        )
                        if not has_diacritics:
                            if (
                                marked_vowel in ("n", "m")
                                and i + 1 < len(syllable)
                                and syllable[i + 1] == "g"
                            ):
                                continue
                        base_vowel, t = options[0]
                        all_tone_options.extend(options)

                        if len(options) > 1:
                            is_checked = any(
                                syllable.endswith(e) for e in self.entering_endings
                            )
                            for opt_base, opt_t in options:
                                if is_checked and opt_t in [4, 8]:
                                    base_vowel, t = opt_base, opt_t
                                    break
                                if not is_checked and opt_t not in [4, 8] and opt_t > 1:
                                    base_vowel, t = opt_base, opt_t

                        if tone_num is None or (has_diacritics and t > 1):
                            tone_num = t
                        new_syllable_chars.append(base_vowel)
                        i += len(marked_vowel)
                        found_vowel = True
                        break

                if not found_vowel:
                    new_syllable_chars.append(syllable[i])
                    i += 1
            syllable = "".join(new_syllable_chars)

        if tone_num is None:
            tone_num = 1

        if (
            tone_num not in [4, 8]
            and syllable
            and syllable[-1] in self.entering_endings
        ):
            tone_num = 8 if tone_num > 1 else 4

        syllable = self._DIGIT_RE.sub("", syllable)

        for marked, keyboard in self.config.syllable_mappings.items():
            if marked in syllable:
                syllable = syllable.replace(marked, keyboard)
                break

        return f"{syllable}{tone_num}"

    _HANDWRITING_TOKEN_RE = re.compile(
        r"[a-zA-Z0-9\u00C0-\u024F\u0300-\u036F\u1E00-\u1EFF\u207F'-]+|\s+|[^\s]"
    )
    _HANDWRITING_WORD_RE = re.compile(
        r"[a-zA-Z0-9\u00C0-\u024F\u0300-\u036F\u1E00-\u1EFF'-]+"
    )

    def to_handwriting(self, text: str) -> str:
        cached = self._handwriting_cache.get(text)
        if cached is not None:
            return cached
        tokens = self._HANDWRITING_TOKEN_RE.findall(text)
        converted_tokens = []

        for token in tokens:
            if token.isspace():
                converted_tokens.append(token)
                continue

            if self._HANDWRITING_WORD_RE.match(token):
                converted_tokens.append(self._word_to_handwriting(token))
            else:
                converted_tokens.append(token)

        result = unicodedata.normalize("NFC", "".join(converted_tokens))
        self._handwriting_cache[text] = result
        return result

    def _word_to_handwriting(self, word: str) -> str:
        parts = self._HYPHEN_SPLIT_RE.split(word)
        converted_parts = []
        for part in parts:
            if part == "-":
                converted_parts.append("-")
            elif part:
                is_upper = part.isupper() and not any(c.isdigit() for c in part)
                is_title = part[0].isupper() if part else False

                converted = self._syllable_to_handwriting(part.lower())

                if is_upper:
                    converted = converted.upper()
                elif is_title:
                    converted = converted.capitalize()

                converted_parts.append(converted)
        return "".join(converted_parts)

    _TONE_DIGIT_RE = re.compile(r"^(.*?)(\d)$")

    def _syllable_to_handwriting(self, syllable: str) -> str:
        cached = self._handwriting_syllable_cache.get(syllable)
        if cached is not None:
            return cached
        result = self._syllable_to_handwriting_inner(syllable)
        self._handwriting_syllable_cache[syllable] = result
        return result

    def _syllable_to_handwriting_inner(self, syllable: str) -> str:
        if not syllable:
            return ""

        match = self._TONE_DIGIT_RE.match(syllable)
        if not match:
            return syllable

        base_part = match.group(1)
        tone_num = int(match.group(2))

        if not base_part:
            return syllable

        for marked_sym, keyboard in self.config.syllable_mappings.items():
            base_part = re.sub(keyboard + "$", marked_sym, base_part)

        key = f"{base_part}{tone_num}"
        if self.config.complex_syllable_map and key in self.config.complex_syllable_map:
            return self.config.complex_syllable_map[key]

        marked = False

        is_entering = (
            self.config.entering_tone_mark_before_ending
            and tone_num in [4, 8]
            and base_part
            and base_part[-1] in self.entering_endings
        )

        if is_entering:
            ending = base_part[-1]
            stem = base_part[:-1]
            for i in range(len(stem) - 1, -1, -1):
                for vowel in self.tone_mark_priority:
                    if stem[i : i + len(vowel)] == vowel:
                        k = f"{vowel}{tone_num}"
                        if k in self.vowel_dict:
                            stem = (
                                stem[:i] + self.vowel_dict[k] + stem[i + len(vowel) :]
                            )
                            marked = True
                            break
                if marked:
                    break
            if marked:
                base_part = stem + ending

        if not marked:
            has_consonant_initial = any(
                base_part[: len(ini)] == ini
                for ini in self.config.initials
                if ini and ini[0] not in "aeiou"
            )
            if not has_consonant_initial and self.config.vowel_initial_overrides:
                k = f"{base_part}{tone_num}"
                if k in self.config.vowel_initial_overrides:
                    base_part = self.config.vowel_initial_overrides[k]
                    marked = True
            if not marked:
                for vowel in self.tone_mark_priority:
                    if vowel in base_part:
                        k = f"{vowel}{tone_num}"
                        if k in self.vowel_dict:
                            idx = base_part.rfind(vowel)
                            if idx != -1:
                                marked_char = self.vowel_dict[k]
                                base_part = (
                                    base_part[:idx]
                                    + marked_char
                                    + base_part[idx + len(vowel) :]
                                )
                                marked = True
                                break

        if not marked:
            tone_str = str(tone_num)
            if self.config.superscript_tones:
                tone_str = tone_str.translate(_SUPERSCRIPT_DIGITS)
            return f"{base_part}{tone_str}"

        return base_part
