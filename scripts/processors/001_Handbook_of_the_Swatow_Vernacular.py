from __future__ import annotations

import re

from scripts.processors.base import (
    BookProcessor,
    Entry,
    generate_modified,
    generate_original,
)

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf000-\uf8ff]")
LINE_RE = re.compile(r"^\s*- \*\*(.+?)\*\*\s*(.*)")
SEP_RE = re.compile(r"\s*\.\.\.\s*\.\.\.\s*\.\.\.\s*")
ANNOTATION_RE = re.compile(r"~~[^~]*~~\([^)]*\)")


def _split_outside_annotations(text: str, sep: str) -> list[str]:
    masked = ANNOTATION_RE.sub(lambda m: "\x00" * len(m.group()), text)
    parts = []
    start = 0
    for m in re.finditer(re.escape(sep), masked):
        parts.append(text[start : m.start()])
        start = m.end()
    parts.append(text[start:])
    return parts


class Processor(BookProcessor):
    def extract_entries(self, text: str, source_name: str) -> list[Entry]:
        entries: list[Entry] = []
        current_section = ""
        last_en_base = ""
        last_en_orig_base = ""

        for line in text.split("\n"):
            stripped = line.strip()

            if stripped.startswith("#"):
                current_section = stripped.lstrip("#").strip()
                continue

            m = LINE_RE.match(line)
            if not m:
                continue

            bold_raw = m.group(1)
            rest = m.group(2)

            parts = SEP_RE.split(rest, maxsplit=1)
            if len(parts) != 2:
                continue

            puj_raw = parts[0].strip()
            trailing_raw = parts[1].strip()

            bold_mod = generate_modified(bold_raw)
            is_lesson = bool(CJK_RE.search(bold_mod))

            if is_lesson:
                raw_chunks = re.split(r"  +", bold_raw)
                puj_mod = self.clean(generate_modified(puj_raw))
                puj_orig = self.clean(generate_original(puj_raw))
                eng_mod = self.clean(generate_modified(trailing_raw))
                eng_orig = self.clean(generate_original(trailing_raw))
            else:
                if bold_raw.startswith("„"):
                    qualifier = bold_raw[1:].strip()
                    qualifier_orig = generate_original(bold_raw)[1:].strip()
                    eng_mod = (
                        f"{last_en_base}, {generate_modified(qualifier)}"
                        if qualifier
                        else last_en_base
                    )
                    eng_orig = (
                        f"{last_en_orig_base}, {qualifier_orig}"
                        if qualifier_orig
                        else last_en_orig_base
                    )
                else:
                    eng_mod = self.clean(generate_modified(bold_raw))
                    eng_orig = self.clean(generate_original(bold_raw))
                    base_mod = re.split(r"[,(]", eng_mod)[0].strip()
                    base_orig = re.split(r"[,(]", eng_orig)[0].strip()
                    if base_mod:
                        last_en_base = base_mod
                    if base_orig:
                        last_en_orig_base = base_orig

                raw_chunks = re.split(r"  +", trailing_raw)
                puj_mod = self.clean(generate_modified(puj_raw))
                puj_orig = self.clean(generate_original(puj_raw))

            stripped_for_check = ANNOTATION_RE.sub("", puj_raw)
            if ";" in stripped_for_check:
                puj_parts_raw = [
                    p.strip()
                    for p in _split_outside_annotations(puj_raw, ";")
                    if p.strip()
                ]
            else:
                puj_parts_raw = [
                    p.strip()
                    for p in _split_outside_annotations(puj_raw, ",")
                    if p.strip()
                ]
                if any(" " in p for p in puj_parts_raw):
                    puj_parts_raw = [puj_raw.strip()]

            chunks = []
            for chunk in raw_chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                mod = generate_modified(chunk)
                orig = generate_original(chunk)
                chunks.append((mod, orig))

            if not chunks:
                continue

            source_label = (
                f"{source_name} > {current_section}" if current_section else source_name
            )

            if len(puj_parts_raw) == len(chunks) and len(chunks) > 1:
                for i, (mod, orig) in enumerate(chunks):
                    p_part = puj_parts_raw[i]
                    entries.append(
                        Entry(
                            han=self.clean(mod),
                            han_orig=self.clean(orig),
                            puj=self.clean(generate_modified(p_part)),
                            puj_orig=self.clean(generate_original(p_part)),
                            en=eng_mod,
                            en_orig=eng_orig,
                            source=source_label,
                        )
                    )
            elif len(puj_parts_raw) > 1 and len(chunks) == 1:
                mod, orig = chunks[0]
                for p_part in puj_parts_raw:
                    entries.append(
                        Entry(
                            han=self.clean(mod),
                            han_orig=self.clean(orig),
                            puj=self.clean(generate_modified(p_part)),
                            puj_orig=self.clean(generate_original(p_part)),
                            en=eng_mod,
                            en_orig=eng_orig,
                            source=source_label,
                        )
                    )
            else:
                for mod, orig in chunks:
                    entries.append(
                        Entry(
                            han=self.clean(mod),
                            han_orig=self.clean(orig),
                            puj=puj_mod,
                            puj_orig=puj_orig,
                            en=eng_mod,
                            en_orig=eng_orig,
                            source=source_label,
                        )
                    )

        return entries
