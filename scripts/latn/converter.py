"""Core latn converter implementation."""

import re
import unicodedata
from abc import ABC
from scripts.latn.config import LatnSystemConfig

_SUPERSCRIPT_DIGITS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
_NORMAL_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


class LatnConverter(ABC):
    """Base class for latn converters."""

    def __init__(self, config: LatnSystemConfig):
        """Initialize the converter with system configuration."""
        self.config = config
        self.vowel_dict = config.vowel_dict
        self.nasal_endings = config.nasal_endings
        self.entering_endings = config.entering_endings
        self.reverse_vowel_map = config.reverse_vowel_map or {}
        self.reverse_complex_map = config.reverse_complex_map or {}

        # Priority for tone marking on vowels
        self.tone_mark_priority = config.tone_mark_priority

    def to_keyboard(self, text: str) -> str:
        """Convert romanized text to keyboard input format."""
        # Keep syllables together with their tone digits
        tokens = re.findall(
            r"[a-zA-Z\u00B2\u00B3\u00B9\u00C0-\u024F\u0300-\u036F\u1E00-\u1EFF\u2070-\u207F'-]+\d*|\s+|[^\s]",
            text,
        )
        converted_tokens = []
        for token in tokens:
            if token.isspace():
                converted_tokens.append(token)
                continue
            # Match tokens with optional trailing digits
            if re.match(
                r"[a-zA-Z\u00B2\u00B3\u00B9\u00C0-\u024F\u0300-\u036F\u1E00-\u1EFF\u2070-\u207F'-]+\d*",
                token,
            ):
                # Handle proper nouns/capitalization where needed
                converted_tokens.append(self._to_keyboard_word(token))
            else:
                converted_tokens.append(token)

        return "".join(converted_tokens)

    def _to_keyboard_word(self, word: str) -> str:
        """Convert a romanized word to keyboard input format."""
        parts = re.split(r"(-)", word)
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

    def _to_keyboard_syllable(self, syllable: str) -> str:
        """Convert a single syllable from marked latn to keyboard format."""
        if not syllable:
            return ""

        if any(c.isdigit() for c in syllable):
            for marked, keyboard in self.config.syllable_mappings.items():
                if marked in syllable:
                    syllable = syllable.replace(marked, keyboard)
            syllable = syllable.translate(_NORMAL_DIGITS)
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
                # Try longest match from reverse_vowel_map
                for marked_vowel, options in self.reverse_vowel_map.items():
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
                        base_vowel, t = options[0]  # Default to first
                        all_tone_options.extend(options)

                        # Disambiguation logic for multiple tones mapping to same diacritic
                        if len(options) > 1:
                            # If it's a checked syllable, prefer tones 4 or 8
                            is_checked = any(
                                syllable.endswith(e) for e in self.entering_endings
                            )
                            for opt_base, opt_t in options:
                                if is_checked and opt_t in [4, 8]:
                                    base_vowel, t = opt_base, opt_t
                                    break
                                if not is_checked and opt_t not in [4, 8] and opt_t > 1:
                                    base_vowel, t = opt_base, opt_t
                                    # Don't break, keep looking for better non-checked tone if any

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

        # Remove tone digits first
        syllable = re.sub(r"\d", "", syllable)

        # Apply system-specific syllable mappings FIRST (marked -> keyboard)
        # This handles things like ur -> e in PUJ before vowel_map processes e
        for marked, keyboard in self.config.syllable_mappings.items():
            if marked in syllable:
                syllable = syllable.replace(marked, keyboard)
                break

        # Note: the numbers are used to mark tone.
        return f"{syllable}{tone_num}"

    def to_handwriting(self, text: str) -> str:
        """Convert keyboard input format (e.g., 'li3') to marked latn (e.g., 'lí')."""
        # Keep syllables together with their tone digits
        tokens = re.findall(
            r"[a-zA-Z0-9\u00C0-\u024F\u0300-\u036F\u1E00-\u1EFF\u207F'-]+|\s+|[^\s]",
            text,
        )
        converted_tokens = []

        for token in tokens:
            if token.isspace():
                converted_tokens.append(token)
                continue

            if re.match(
                r"[a-zA-Z0-9\u00C0-\u024F\u0300-\u036F\u1E00-\u1EFF'-]+", token
            ):
                converted_tokens.append(self._word_to_handwriting(token))
            else:
                converted_tokens.append(token)

        return "".join(converted_tokens)

    def _word_to_handwriting(self, word: str) -> str:
        parts = re.split(r"(-)", word)
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

    def _syllable_to_handwriting(self, syllable: str) -> str:
        """Convert keyboard format syllable (e.g., 'li3') to marked (e.g., 'lí')."""
        if not syllable:
            return ""

        match = re.match(r"^(.*?)(\d)$", syllable)
        if not match:
            # Handle default tone if not provided (assume tone 1)
            # Or preserve it if it contains no tone digit.
            # Usually users might pass un-toned words.
            return syllable

        base_part = match.group(1)
        tone_num = int(match.group(2))

        if not base_part:
            return syllable

        # Apply system-specific syllable mappings (keyboard -> marked)
        # Must happen BEFORE tone marking so that e.g. 'uann' -> 'uaⁿ'
        # prevents 'uan' from matching as a composite vowel.
        for marked_sym, keyboard in self.config.syllable_mappings.items():
            base_part = re.sub(keyboard + "$", marked_sym, base_part)

        # Prioritize predefined dictionary (e.g. for complex syllables in POJ/PUJ)
        # Check if the combined form matches our complex map
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
