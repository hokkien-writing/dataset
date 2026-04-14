"""Core latn converter implementation."""

import re
from abc import ABC
from scripts.latn.config import LatnSystemConfig


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
        tokens = re.findall(r"[a-zA-Z\u00C0-\u024F'-]+|[^\s]", text)
        converted_tokens = []
        for token in tokens:
            if re.match(r"[a-zA-Z\u00C0-\u024F'-]+", token):
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
                is_title = part.istitle()

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

        if not found_complex:
            new_syllable_chars = []
            i = 0
            while i < len(syllable):
                char = syllable[i]
                if char in self.reverse_vowel_map:
                    base_vowel, t = self.reverse_vowel_map[char]
                    if tone_num is None:
                        tone_num = t
                    new_syllable_chars.append(base_vowel)
                else:
                    new_syllable_chars.append(char)
                i += 1
            syllable = "".join(new_syllable_chars)

        if tone_num is None or tone_num == 1:
            if syllable and syllable[-1] in self.entering_endings:
                tone_num = 4
            elif tone_num is None:
                tone_num = 1

        syllable = re.sub(r"\d", "", syllable)

        # specific normalization for nn->ⁿ logic mapped to POJ/PUJ keyboard representation
        syllable = syllable.replace("ⁿ", "nn")

        # Note: the numbers are used to mark tone.
        return f"{syllable}{tone_num}"

    def to_handwriting(self, text: str) -> str:
        """Convert keyboard input format (e.g., 'li3') to marked latn (e.g., 'lí')."""
        tokens = re.findall(r"[a-zA-Z0-9'-]+|[^\s]", text)
        converted_tokens = []

        for token in tokens:
            if re.match(r"[a-zA-Z0-9'-]+", token):
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

        # Prioritize predefined dictionary (e.g. for complex syllables in POJ/PUJ)
        # Check if the combined form matches our complex map
        key = f"{base_part}{tone_num}"
        if self.config.complex_syllable_map and key in self.config.complex_syllable_map:
            return self.config.complex_syllable_map[key]

        marked = False
        for vowel in self.tone_mark_priority:
            if vowel == "ur":
                if "ur" in base_part:
                    k = f"ur{tone_num}"
                    if k in self.vowel_dict:
                        base_part = base_part.replace("ur", self.vowel_dict[k], 1)
                        marked = True
                        break
            else:
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

        # Final replacement rules (e.g. nn -> ⁿ)
        base_part = re.sub(r"nn$", "ⁿ", base_part)

        return base_part
