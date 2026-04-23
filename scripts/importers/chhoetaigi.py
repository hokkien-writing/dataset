from __future__ import annotations

import csv
import re
from pathlib import Path

from scripts.importers.base import ExternalEntry, ExternalImporter

_HAN_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf000-\uf8ff]+")


_HAN_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf000-\uf8ff]+")
_BRACKET_WRAP_RE = re.compile(r"^\[([^\]]+)\]$")
_ANNOTATION_RE = re.compile(r"\(([^)]+)\)")


def _normalize_annotations(text: str) -> str:
    text = _BRACKET_WRAP_RE.sub(r"\1", text)
    return _ANNOTATION_RE.sub(r"[\1]", text)


def extract_han_chars(text: str) -> str:
    return "".join(m.group() for m in _HAN_RE.finditer(text))


class ChhoeTaigiImporter(ExternalImporter):
    def get_source_name(self) -> str:
        return "ChhoeTaigi"

    def import_file(self, csv_path: Path, source_id: str) -> list[ExternalEntry]:
        entries: list[ExternalEntry] = []
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                poj_raw = _normalize_annotations((row.get("PojUnicode") or "").strip())
                kip_raw = _normalize_annotations((row.get("KipUnicode") or "").strip())
                hanlo_poj = (row.get("HanLoTaibunPoj") or "").strip()
                hanlo_kip = (row.get("HanLoTaibunKip") or "").strip()
                hoa = (row.get("HoaBun") or "").strip()
                eng = (row.get("EngBun") or "").strip()

                hanlo = hanlo_poj or hanlo_kip
                han = extract_han_chars(hanlo) if hanlo else ""
                if han != (hanlo or "").replace(" ", ""):
                    han = ""
                if not poj_raw and not kip_raw:
                    continue

                poj_variants = [v.strip() for v in poj_raw.split("/") if v.strip()] or [
                    ""
                ]
                kip_variants = [v.strip() for v in kip_raw.split("/") if v.strip()] or [
                    ""
                ]
                n = max(len(poj_variants), len(kip_variants))
                poj_variants = (poj_variants * ((n // len(poj_variants)) + 1))[:n]
                kip_variants = (kip_variants * ((n // len(kip_variants)) + 1))[:n]

                for poj_val, kip_val in zip(poj_variants, kip_variants):
                    entries.append(
                        ExternalEntry(
                            poj=poj_val,
                            tl=kip_val,
                            han=han,
                            en=eng,
                            zh_TW=hoa,
                            source=f"{self.get_source_name()} > {source_id}",
                        )
                    )
        return entries
