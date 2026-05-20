from __future__ import annotations

import re

from scripts.processors.base import BookProcessor, Entry

LINE_RE = re.compile(r"^\*\*(.+?)\*\*,\s*(.*)")
HAN_ANN_RE = re.compile(r"\+\+\(([^)]*)\)\+\+")
PLAIN_HAN_RE = re.compile(r"\(([\u4E00-\u9FFF\u3400-\u4DBF\U00020000-\U0002EBEF]+)\)")
COMMA_ANN_SPLIT_RE = re.compile(r"(?<=\)\+\+),\s+(?=\S.*\+\+(?:\(|\+\+))")
COLON_SPLIT_RE = re.compile(r":\s+")
_VARIANT_FIX_RE = re.compile(r"~~([^~(]+?)~~\(([^()]+)\)")
_VARIANT_NOTE_RE = re.compile(r"\s*~~\([^~]+?\)~~\(.+?\)\)\s*")


class Processor(BookProcessor):
    def extract_entries(self, text: str, source_name: str) -> list[Entry]:
        entries: list[Entry] = []
        current_section = ""

        for line in text.split("\n"):
            stripped = line.strip().rstrip("&c.")

            if stripped.startswith("#"):
                current_section = stripped.lstrip("#").strip()
                continue

            m = LINE_RE.match(stripped)
            if not m:
                continue

            en_base = m.group(1).strip()
            rest = m.group(2).strip()
            if not rest:
                continue

            rest = rest.replace("...", "…")
            rest = rest.rstrip(".")
            groups = re.split(r"\.\s+(?=\*)", rest)
            if not groups[0]:
                groups = groups[1:]

            source_label = (
                f"{source_name} > {current_section}" if current_section else source_name
            )

            for group in groups:
                group = group.strip()
                if not group:
                    continue

                sub_groups = re.split(r";\s+(?=\*)", group)

                for sub in sub_groups:
                    sub = sub.strip()
                    if not sub:
                        continue

                    en = en_base
                    puj_text = ""

                    qual = re.match(
                        r"^([a-zA-Z][a-zA-Z ]*?),\s*\*(.+?)\*\s*,\s*(.*)", sub
                    )
                    if qual and qual.group(1).strip().isascii():
                        qualifier = qual.group(1).strip()
                        italic = qual.group(2).strip()
                        puj_text = qual.group(3).strip()
                        if italic.isascii():
                            en = f"{en_base}, {qualifier}, {italic}"
                        else:
                            en = f"{en_base}, {qualifier}"
                            puj_text = f"{italic}; {puj_text}"

                    if not puj_text:
                        ctx = re.match(r"\*(.+?)\*\s*,\s*(.*)", sub)
                        if not ctx:
                            ctx = re.match(r"\*(.+?)\*\s+(.*)", sub)
                        if ctx:
                            en = f"{en_base}, {ctx.group(1).strip()}"
                            puj_text = ctx.group(2).strip()
                        else:
                            puj_text = sub

                    if not puj_text or puj_text.startswith("see "):
                        continue

                    while True:
                        extra_ctx = re.match(r"\*(.+?)\*\s*,\s*(.*)", puj_text)
                        if not extra_ctx:
                            break
                        en = f"{en}, {extra_ctx.group(1).strip()}"
                        puj_text = extra_ctx.group(2).strip()

                    puj_text = puj_text.replace("*", "")

                    for puj in puj_text.split(";"):
                        puj = puj.strip()
                        if not puj:
                            continue
                        puj = re.sub(
                            r"\.\s+(?:and\s+)?see\s+\w[\w\s]*", "", puj, flags=re.IGNORECASE
                        ).strip()
                        if not puj:
                            continue

                        puj = _VARIANT_FIX_RE.sub(r"\2", puj)
                        puj = _VARIANT_NOTE_RE.sub("", puj).strip()
                        if not puj:
                            continue

                        for item in self._split_annotated_items(puj):
                            self._emit_entry(item, en, source_label, entries)

        return entries

    @staticmethod
    def _split_annotated_items(puj: str) -> list[str]:
        if COLON_SPLIT_RE.search(puj) and COMMA_ANN_SPLIT_RE.search(puj):
            parts = COLON_SPLIT_RE.split(puj, maxsplit=1)
            items = [parts[0].rstrip(": ")]
            if len(parts) > 1:
                items.extend(
                    s.strip() for s in COMMA_ANN_SPLIT_RE.split(parts[1]) if s.strip()
                )
            return items

        if COMMA_ANN_SPLIT_RE.search(puj):
            return [
                s.strip() for s in COMMA_ANN_SPLIT_RE.split(puj) if s.strip()
            ]

        return [puj]

    @staticmethod
    def _emit_entry(puj: str, en: str, source_label: str, entries: list[Entry]) -> None:
        han_match = HAN_ANN_RE.search(puj)
        han = han_match.group(1) if han_match else ""

        if not han:
            plain = PLAIN_HAN_RE.search(puj)
            if plain:
                han = plain.group(1)

        puj = HAN_ANN_RE.sub("", puj).strip()
        puj = PLAIN_HAN_RE.sub("", puj).strip()
        puj = re.sub(r"\+\+\+\+", "", puj).strip()
        puj = puj.rstrip(": ")
        if not puj:
            return

        entries.append(
            Entry(
                han=han,
                han_orig=han,
                puj=BookProcessor.clean(puj),
                puj_orig="",
                en=BookProcessor.clean(en),
                en_orig="",
                source=source_label,
            )
        )
