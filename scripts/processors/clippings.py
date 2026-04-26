from __future__ import annotations

import csv
import io

from scripts.latn import create_translator
from scripts.processors.base import BookProcessor, Entry

_LATN_NORM_TO_PUJ = create_translator("LATN_NORM", "PUJ")
_LATN_NORM_TO_POJ = create_translator("LATN_NORM", "POJ")


class Processor(BookProcessor):
    def extract_entries(self, text: str, source_name: str) -> list[Entry]:
        prefix = source_name.split(".")[0]
        if prefix == "teochew":
            translator = _LATN_NORM_TO_PUJ
        elif prefix == "hokkien":
            translator = _LATN_NORM_TO_POJ
        else:
            return []

        entries: list[Entry] = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            latn_norm = (row.get("latn_norm") or "").strip()
            han = (row.get("han") or "").strip()
            zh_TW = (row.get("zh_TW") or "").strip()
            zh_CN = (row.get("zh_CN") or "").strip()
            en = (row.get("en") or "").strip()

            latn_variants = [v.strip() for v in latn_norm.split("|") if v.strip()]
            han_variants = [h.strip() for h in han.split("|") if h.strip()]
            zh_tw_variants = [z.strip() for z in zh_TW.split("|") if z.strip()]
            if not latn_variants:
                latn_variants = [latn_norm]
            if not han_variants:
                han_variants = [han]
            if not zh_tw_variants:
                zh_tw_variants = [zh_TW]

            for latn in latn_variants:
                puj = ""
                poj = ""
                if latn:
                    try:
                        romanized = translator.translate(latn).lower()
                    except Exception:
                        romanized = ""
                    if prefix == "teochew":
                        puj = romanized
                    else:
                        poj = romanized

                for h in han_variants:
                    for z in zh_tw_variants:
                        entries.append(
                            Entry(
                                han=h,
                                han_orig="",
                                puj=puj,
                                puj_orig="",
                                poj=poj,
                                poj_orig="",
                                en=en,
                                zh_TW=z,
                                zh_CN=zh_CN,
                                source=source_name,
                            )
                        )

        return entries
