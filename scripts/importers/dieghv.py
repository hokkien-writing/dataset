from __future__ import annotations

import re
from pathlib import Path

from scripts.importers.base import ExternalEntry, ExternalImporter


def _to_dp(code: str) -> str:
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


class DieghvImporter(ExternalImporter):
    def get_source_name(self) -> str:
        return "dieghv"

    def import_file(self, dict_yaml_path: Path, source_id: str) -> list[ExternalEntry]:
        if dict_yaml_path.suffix not in (".yaml", ".dict.yaml"):
            dict_yaml_path = dict_yaml_path.parent / f"{dict_yaml_path.stem}.dict.yaml"
        if not dict_yaml_path.exists():
            print(f"  ⚠ {dict_yaml_path.name} not found, skipping.")
            return []

        entries: list[ExternalEntry] = []
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
                han = parts[0].strip()
                code = parts[1].strip()
                if not han:
                    continue

                entries.append(
                    ExternalEntry(
                        dp=_to_dp(code),
                        han=han,
                        source=f"{self.get_source_name()} > {source_id}",
                    )
                )

        return entries
