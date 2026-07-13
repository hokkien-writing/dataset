from __future__ import annotations

import re

from scripts.processors.base import (
    BookProcessor,
    Entry,
    generate_modified,
    generate_original,
)

PAGE_RE = re.compile(r"<!-- page:(\d+) -->")
HEADWORD_RE = re.compile(r"^- \*\*(.+?)\*\*(\([^)]*\))?\s+(\S+)(?:\s*—\s*(.*))?$")
EXAMPLE_RE = re.compile(r"^- \*(.+?)\*(?:\s*—\s*(.*))?$")


class Processor(BookProcessor):
    def extract_entries(self, text: str, source_name: str) -> list[Entry]:
        entries: list[Entry] = []
        current_page = ""
        current_han = ""
        current_puj = ""

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
                puj = self.clean(generate_modified(head_m.group(3)))
                puj_orig = self.clean(generate_original(head_m.group(3)))
                en_raw = (head_m.group(4) or "").strip()
                en = self.clean(generate_modified(en_raw))
                en_orig = self.clean(generate_original(en_raw))
                current_han = han
                current_puj = puj
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
                entries.append(
                    Entry(
                        han=current_han,
                        han_orig=current_han,
                        puj=phrase,
                        puj_orig=phrase_orig,
                        en=gloss,
                        en_orig=gloss_orig,
                        source=source_name,
                        page_num=current_page,
                    )
                )

        return entries
