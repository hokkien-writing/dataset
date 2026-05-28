#!/usr/bin/env python3
"""Convert external dataset CSVs to unified format for merge_csv.py."""

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

EXTERNAL_DIR = PROJECT_ROOT / "external"
OUTPUT_DIR = PROJECT_ROOT / "export" / "external"

WIDE_FIELDS = [
    "puj",
    "dp",
    "poj",
    "tl",
    "bp",
    "han",
    "han_variants",
    "en",
    "zh_CN",
    "zh_TW",
    "source",
]

from scripts.importers.chhoetaigi import ChhoeTaigiImporter
from scripts.importers.dieghv import DieghvImporter

IMPORTERS = {
    "ChhoeTaigiDatabase": ChhoeTaigiImporter(),
    "dieghv": DieghvImporter(),
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    any_processed = False

    for dir_name, importer in sorted(IMPORTERS.items()):
        src_dir = EXTERNAL_DIR / dir_name
        if not src_dir.exists():
            print(f"[{dir_name}] Not found, skipping.")
            continue

        if dir_name == "dieghv":
            data_files = sorted(
                p
                for p in src_dir.rglob("*.dict.yaml")
                if "schema" not in p.name
                and "_60" not in p.name
                and "mtr" not in p.name
            )
        else:
            data_files = sorted(
                p for ext in ("*.csv", "*.tsv") for p in src_dir.rglob(ext)
            )
        if not data_files:
            print(f"[{dir_name}] No data files found.")
            continue

        print(f"[{dir_name}] Processing {len(data_files)} file(s)...")

        for data_file in data_files:
            entries = importer.import_file(data_file, data_file.stem)
            if not entries:
                print(f"  ⚠ {data_file.name}: no entries")
                continue

            out_path = OUTPUT_DIR / data_file.name
            if data_file.suffix == ".tsv":
                out_path = OUTPUT_DIR / (
                    importer.get_source_name() + "_" + data_file.stem + ".csv"
                )
            if data_file.suffix in (".yaml", ".dict.yaml"):
                out_path = OUTPUT_DIR / (
                    importer.get_source_name() + "_" + data_file.stem + ".csv"
                )
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=WIDE_FIELDS)
                writer.writeheader()
                for entry in entries:
                    writer.writerow(
                        {
                            "puj": entry.puj,
                            "dp": entry.dp,
                            "poj": entry.poj,
                            "tl": entry.tl,
                            "bp": entry.bp,
                            "han": entry.han,
                            "han_variants": entry.han_variants,
                            "en": entry.en,
                            "zh_CN": entry.zh_CN,
                            "zh_TW": entry.zh_TW,
                            "source": entry.source,
                        }
                    )

            print(f"  ✓ {data_file.name} ({len(entries)} entries)")
            any_processed = True

    if not any_processed:
        print("No external CSV files were exported.")
        return

    print(f"\nDone. External CSV exported to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
