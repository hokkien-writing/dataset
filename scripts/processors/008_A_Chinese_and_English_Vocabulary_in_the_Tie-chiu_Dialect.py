from __future__ import annotations

import re

from scripts.latn.converter import LatnConverter
from scripts.latn.systems.puj import (
    create_config as create_puj_config,
    goddard_to_keyboard,
)
from scripts.processors.base import (
    BookProcessor,
    Entry,
    generate_modified,
    generate_original,
)

_PAGE_RE = re.compile(r"<!-- page:(\d+) -->")
_SECTION_RE = re.compile(r"^### (.+)\.\s*$")
_ENTRY_LINE_RE = re.compile(r"^\s*-\s*\*\*(.+?)\*\*\s*(.*?)\s*—\s*(.*)")
_HAN_TONE_PAIR_RE = re.compile(r"\*\*(.+?)\*\*\s*(?:<sup>([^<]*)</sup>)?")
_VOCAB_START_RE = re.compile(r"^## VOCABULARY\.?\s*$")
_VOCAB_END_RE = re.compile(r"^## (Table of radicals|List of words)")
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df]")

_puj_converter = LatnConverter(create_puj_config())


def _goddard_to_puj(goddard_word: str, tone_str: str) -> str:
    kb = goddard_to_keyboard(goddard_word, tone_str)
    return _puj_converter.to_handwriting(kb)


class Processor(BookProcessor):
    def extract_entries(self, text: str, source_name: str) -> list[Entry]:
        entries: list[Entry] = []
        current_roms: list[str] = []
        current_page = ""
        in_vocab = False

        for line in text.split("\n"):
            stripped = line.strip()

            page_m = _PAGE_RE.search(stripped)
            if page_m:
                current_page = page_m.group(1)
                continue

            if _VOCAB_START_RE.match(stripped):
                in_vocab = True
                continue

            if in_vocab and _VOCAB_END_RE.match(stripped):
                in_vocab = False
                continue

            if not in_vocab:
                continue

            section_m = _SECTION_RE.match(stripped)
            if section_m:
                raw_rom = section_m.group(1).strip()
                rom = generate_modified(raw_rom)
                current_roms = [r.strip() for r in re.split(r"\s+or\s+", rom)]
                continue

            entry_m = _ENTRY_LINE_RE.match(line)
            if not entry_m:
                continue

            bold_text = entry_m.group(1)
            middle = entry_m.group(2)
            definition = entry_m.group(3)

            combined = f"**{bold_text}** {middle}"
            pairs = _HAN_TONE_PAIR_RE.findall(combined)

            for hanzi, tone in pairs:
                hanzi = hanzi.strip()
                if not _CJK_RE.search(hanzi):
                    continue

                han_mod = generate_modified(hanzi)
                han_orig = generate_original(hanzi)
                en_mod = generate_modified(definition)
                en_orig = generate_original(definition)

                for rom in current_roms:
                    puj = _goddard_to_puj(rom, tone)
                    entries.append(Entry(
                        han=han_mod,
                        han_orig=han_orig,
                        puj=puj,
                        puj_orig=f"{rom} {tone}".strip(),
                        en=en_mod,
                        en_orig=en_orig,
                        source=source_name,
                        page_num=current_page,
                    ))

        return entries
