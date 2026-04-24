from __future__ import annotations

import csv
import re
from pathlib import Path

from scripts.importers.base import ExternalEntry, ExternalImporter

DP_INITIALS = sorted(
    [
        "bh",
        "gh",
        "ng",
        "b",
        "p",
        "m",
        "d",
        "t",
        "n",
        "l",
        "g",
        "k",
        "h",
        "z",
        "c",
        "r",
        "s",
    ],
    key=len,
    reverse=True,
)


def _parse_initial_from_code(code: str) -> str:
    base = code.rstrip("0123456789")
    for ini in DP_INITIALS:
        if base.startswith(ini):
            return ini
    return "null"


def _parse_tone_from_code(code: str) -> int | None:
    m = re.search(r"(\d+)$", code)
    return int(m.group(1)) if m else None


def _convert_dp_code(code: str) -> str:
    tone_m = re.search(r"(\d+)$", code)
    tone = tone_m.group(1) if tone_m else ""
    base = code[: -len(tone)] if tone else code

    base = re.sub(r"e", "ê", base)
    base = re.sub(r"n$", "ⁿ", base)
    base = re.sub(r"v", "e", base)
    base = re.sub(r"p$", "b", base)
    base = re.sub(r"t$", "d", base)
    base = re.sub(r"k$", "g", base)

    superscript = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    tone = tone.translate(superscript)
    return base + tone


def _load_dieziu_dict(dict_yaml_path: Path) -> dict[str, list[tuple[str, str, int]]]:
    lookup: dict[str, list[tuple[str, str, int]]] = {}
    past_header = False
    with open(dict_yaml_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not past_header:
                if line.strip() == "...":
                    past_header = True
                continue
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            char, code = parts[0].strip(), parts[1].strip()
            if len(char) != 1:
                continue
            initial = _parse_initial_from_code(code)
            tone = _parse_tone_from_code(code)
            if tone is None:
                continue
            if char not in lookup:
                lookup[char] = []
            lookup[char].append((code, initial, tone))
    return lookup


def _is_dieziu(dialect_flag: str) -> bool:
    if not dialect_flag:
        return True
    return len(dialect_flag) >= 5 and dialect_flag[4] == "1"


class DieghvImporter(ExternalImporter):
    def get_source_name(self) -> str:
        return "dieghv"

    def import_file(self, csv_path: Path, source_id: str) -> list[ExternalEntry]:
        dict_yaml_path = csv_path.parent / "dieziu.dict.yaml"
        if not dict_yaml_path.exists():
            print(f"  ⚠ {dict_yaml_path.name} not found, skipping.")
            return []

        lookup = _load_dieziu_dict(dict_yaml_path)
        entries: list[ExternalEntry] = []

        current_initial = "null"
        current_tone = ""

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            header = next(reader, None)
            if header is None:
                return []

            for row in reader:
                if len(row) < 4:
                    continue
                rhyme = row[0].strip()
                initial = row[1].strip()
                tone = row[2].strip()
                char = row[3].strip()
                variant = row[4].strip() if len(row) > 4 else ""
                dialect = row[5].strip() if len(row) > 5 else ""

                if not char:
                    continue

                if rhyme and initial and rhyme == header[0] and initial == header[1]:
                    continue

                if initial:
                    current_initial = initial
                if tone:
                    current_tone = tone

                if not _is_dieziu(dialect):
                    continue

                matched_code = self._match_code(
                    lookup, char, current_initial, int(current_tone)
                )
                if matched_code is None:
                    continue

                entries.append(
                    ExternalEntry(
                        dp=_convert_dp_code(matched_code),
                        han=char,
                        han_variants=variant,
                        source=f"{self.get_source_name()} > {source_id}",
                    )
                )

        return entries

    def _match_code(
        self,
        lookup: dict[str, list[tuple[str, str, int]]],
        char: str,
        initial: str,
        tone: int,
    ) -> str | None:
        codes = lookup.get(char)
        if not codes:
            return None
        for code, code_initial, code_tone in codes:
            if code_initial == initial and code_tone == tone:
                return code
        for code, code_initial, code_tone in codes:
            if code_tone == tone:
                return code
        return None
