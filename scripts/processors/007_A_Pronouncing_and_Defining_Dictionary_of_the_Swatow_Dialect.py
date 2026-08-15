from __future__ import annotations

import re

from scripts.latn.systems.puj import FieldePUJSystem
from scripts.processors.base import (
    BookProcessor,
    Entry,
    generate_modified,
    generate_original,
)

_normalize_puj = FieldePUJSystem().normalize_book_text


def _normalize_007_puj(text: str) -> str:
    return _normalize_puj(text).replace("nn̄g", "n̄ng")

PAGE_RE = re.compile(r"<!-- page:(\d+) -->")
HEADWORD_RE = re.compile(r"^- \*\*(.+?)\*\*\s+(.+?)\s+\([^)]*\)(?:\s*—\s*(.*))?$")
EXAMPLE_RE = re.compile(r"^\s*- \*(.+?)\*(?:\s*—\s*(.*))?$")


def _normalize_headword_reading(text: str) -> str:
    return re.sub(r"\s+or\s+", "/", text.strip(), flags=re.IGNORECASE)


def _normalize_headword_puj(text: str) -> str:
    return "/".join(reading.strip() for reading in text.split("/"))


class Processor(BookProcessor):
    def extract_entries(self, text: str, source_name: str) -> list[Entry]:
        entries: list[Entry] = []
        current_page = ""
        current_han = ""
        current_puj = ""
        pending_headword_han = ""
        pending_headword_han_orig = ""
        pending_headword_puj = ""

        for line in text.split("\n"):
            stripped = line.strip()

            page_m = PAGE_RE.search(stripped)
            if page_m:
                current_page = page_m.group(1)
                continue

            head_m = HEADWORD_RE.match(stripped)
            if head_m:
                han = self.clean(generate_modified(head_m.group(1)))
                han_orig = self.clean(generate_original(head_m.group(1)))
                reading = _normalize_headword_reading(head_m.group(2))
                puj = self.clean(_normalize_headword_puj(generate_modified(reading)))
                puj_orig = self.clean(generate_original(reading))
                en_raw = (head_m.group(3) or "").strip()
                en = self.clean(generate_modified(en_raw))
                en_orig = self.clean(generate_original(en_raw))
                current_han = han
                current_puj = puj
                pending_headword_han = han if not en else ""
                pending_headword_han_orig = han_orig if not en else ""
                pending_headword_puj = puj if not en else ""
                entries.append(
                    Entry(
                        han=han,
                        han_orig=han_orig,
                        puj=puj,
                        puj_orig=puj_orig,
                        en=en,
                        en_orig=en_orig,
                        source=source_name,
                        page_num=current_page,
                    )
                )
                continue

            ex_m = EXAMPLE_RE.match(stripped)
            if ex_m:
                phrase = self.clean(generate_modified(ex_m.group(1)))
                phrase_orig = self.clean(generate_original(ex_m.group(1)))
                gloss_raw = (ex_m.group(2) or "").strip()
                gloss = self.clean(generate_modified(gloss_raw))
                gloss_orig = self.clean(generate_original(gloss_raw))
                han = pending_headword_han if gloss else ""
                han_orig = pending_headword_han_orig if gloss else ""
                entries.append(
                    Entry(
                        han=han,
                        han_orig=han_orig,
                        puj=phrase,
                        puj_orig=phrase_orig,
                        en=gloss,
                        en_orig=gloss_orig,
                        source=source_name,
                        page_num=current_page,
                    )
                )
                pending_headword_han = ""
                pending_headword_han_orig = ""
                pending_headword_puj = ""

        return entries
