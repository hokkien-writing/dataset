import re
from typing import Optional, Tuple
from .config import PhoneticMapping
from .converter import LatnConverter


class LatnTranslator:
    def __init__(
        self,
        source_converter: LatnConverter,
        target_converter: LatnConverter,
        mapping: Optional[PhoneticMapping] = None,
    ):
        self.source = source_converter
        self.target = target_converter
        self.mapping = mapping or PhoneticMapping()

        self._source_initials = sorted(
            source_converter.config.initials, key=len, reverse=True
        )
        all_endings = (
            source_converter.config.entering_endings
            + source_converter.config.nasal_endings
            + target_converter.config.entering_endings
            + target_converter.config.nasal_endings
        )
        self._source_endings = sorted(set(all_endings), key=len, reverse=True)
        self._translate_cache: dict[str, str] = {}

    def _parse_syllable(self, base: str) -> Tuple[str, str, str]:
        base = base.lower()

        for init in self._source_initials:
            if base == init:
                return init, "", ""

        ending = ""
        for e in self._source_endings:
            if base.endswith(e) and len(base) > len(e):
                ending = e
                base = base[: -len(e)]
                break

        initial = ""
        for init in self._source_initials:
            if base.startswith(init):
                initial = init
                base = base[len(init) :]
                break

        return initial, base, ending

    def _map_initial(self, initial: str, vowel: str) -> str:
        if initial not in self.mapping.initial_map:
            return initial
        val = self.mapping.initial_map[initial]
        if callable(val):
            return val(initial, vowel)
        return val

    _SYLLABLE_RE = re.compile(r"[A-Za-z\u00C0-\u1EFF\u0358ⁿ]+\d?")
    _HYPHEN_RE = re.compile(
        r"(?<=[a-zA-Z\u00C0-\u1EFF\u0358ⁿ])-(?=[a-zA-Z\u00C0-\u1EFF\u0358ⁿ])"
    )

    def translate(self, text: str) -> str:
        cached = self._translate_cache.get(text)
        if cached is not None:
            return cached

        keyboard_text = self.source.to_keyboard(text)

        def replace_syllable(match):
            syllable = match.group(0)

            tone_match = re.search(r"(\d)$", syllable)
            tone_num = tone_match.group(1) if tone_match else ""
            base = syllable[: -len(tone_num)] if tone_num else syllable

            initial, vowel, ending = self._parse_syllable(base)

            new_initial = self._map_initial(initial, vowel)
            new_vowel = self.mapping.vowel_map.get(vowel, vowel)

            tone_int = int(tone_num) if tone_num else 0

            if self.mapping.nasal_prefix and ending in self.mapping.nasal_prefix:
                prefix, remaining = self.mapping.nasal_prefix[ending]
                new_vowel = prefix + new_vowel
                raw = self.mapping.ending_map.get(remaining, remaining)
                new_ending = raw(remaining, tone_int) if callable(raw) else raw
            else:
                raw = self.mapping.ending_map.get(ending, ending)
                new_ending = raw(ending, tone_int) if callable(raw) else raw

            return new_initial + new_vowel + new_ending + tone_num

        translated_keyboard = self._SYLLABLE_RE.sub(replace_syllable, keyboard_text)

        result = self.target.to_handwriting(translated_keyboard)

        if self.mapping.remove_hyphens:
            result = self._HYPHEN_RE.sub("", result)

        self._translate_cache[text] = result
        return result
