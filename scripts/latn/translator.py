"""Translator for converting between different latn systems."""

import re
from typing import Optional
from scripts.latn.config import PhoneticMapping
from scripts.latn.converter import LatnConverter


class LatnTranslator:
    """Handles translation between two latn systems."""

    def __init__(
        self,
        source_converter: LatnConverter,
        target_converter: LatnConverter,
        mapping: Optional[PhoneticMapping] = None,
    ):
        self.source = source_converter
        self.target = target_converter
        self.mapping = mapping or PhoneticMapping()

        # Prepare regex for vowel replacement (descending length)
        vowel_keys = sorted(self.mapping.vowel_map.keys(), key=len, reverse=True)
        self.vowel_pattern = None
        if vowel_keys:
            pattern_str = "|".join(re.escape(k) for k in vowel_keys)
            self.vowel_pattern = re.compile(f"({pattern_str})")

        # Prepare sorted consonant mapping
        self.sorted_consonants = sorted(
            self.mapping.consonant_map.items(), key=lambda x: len(x[0]), reverse=True
        )

        self.compiled_rules = [
            (re.compile(pattern), repl)
            for pattern, repl in self.mapping.conversion_rules
        ]

    def translate(self, text: str) -> str:
        """
        Translates text from source system to target system.

        Process: Source (Handwriting) -> Source (Keyboard) -> Target (Keyboard) -> Target (Handwriting)
        """
        # Step 1: Source Handwriting -> Source Keyboard
        keyboard_text = self.source.to_keyboard(text)

        # Step 2: Source Keyboard -> Target Keyboard
        # We need to split keyboard text into tokens to avoid mapping inside tone numbers or other symbols
        # But since to_keyboard returns tokens like 'oo1', 'ua2', we can just process those.

        # A simple approach: token-based replacement in the keyboard representation
        # Each syllable in keyboard form is usually [consonant][vowel][entering][tone]
        # or [vowel][entering][tone]

        def replace_syllable(match):
            syllable = match.group(0)

            # Extract tone number if present
            tone_match = re.search(r"(\d)$", syllable)
            tone_num = tone_match.group(1) if tone_match else ""
            new_base = syllable[: -len(tone_num)] if tone_num else syllable

            # Apply vowel mappings
            if self.vowel_pattern:
                new_base = self.vowel_pattern.sub(
                    lambda m: self.mapping.vowel_map.get(m.group(0), m.group(0)),
                    new_base,
                )

            # Apply consonant mappings if any (sorted by length descending)
            for src, tgt in self.sorted_consonants:
                if new_base.startswith(src):
                    new_base = tgt + new_base[len(src) :]
                    break  # Only one consonant replacement per syllable

            # Apply custom regex rules (e.g., for context-sensitive changes)
            for pattern, repl in self.compiled_rules:
                new_base = pattern.sub(repl, new_base)

            return new_base + tone_num

        # Apply to all keyboard tokens (alphanumeric clusters with optional trailing digit)
        translated_keyboard = re.sub(
            r"[A-Za-z\u00C0-\u1EFF\u0358ⁿ]+\d?", replace_syllable, keyboard_text
        )

        # Convert back from keyboard format
        result = self.target.to_handwriting(translated_keyboard)

        if self.mapping.remove_hyphens:
            # Remove hyphens that are between alphanumeric/marked characters
            result = re.sub(
                r"(?<=[a-zA-Z\u00C0-\u1EFF\u0358ⁿ])-(?=[a-zA-Z\u00C0-\u1EFF\u0358ⁿ])",
                "",
                result,
            )

        return result
