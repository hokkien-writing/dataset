#!/usr/bin/env python3
"""Convert external dataset CSVs to merged.csv format."""

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

IMPORTERS = {
    "ChhoeTaigiDatabase": ChhoeTaigiImporter(),
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    any_processed = False

    for dir_name, importer in sorted(IMPORTERS.items()):
        src_dir = EXTERNAL_DIR / dir_name
        if not src_dir.exists():
            print(f"[{dir_name}] Not found, skipping.")
            continue

        csv_files = sorted(src_dir.rglob("*.csv"))
        if not csv_files:
            print(f"[{dir_name}] No CSV files found.")
            continue

        print(f"[{dir_name}] Processing {len(csv_files)} file(s)...")

        for csv_file in csv_files:
            entries = importer.import_file(csv_file, csv_file.stem)
            if not entries:
                print(f"  ⚠ {csv_file.name}: no entries")
                continue

            out_path = OUTPUT_DIR / csv_file.name
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

            print(f"  ✓ {csv_file.name} ({len(entries)} entries)")
            any_processed = True

    if not any_processed:
        print("No external CSV files were exported.")
        return

    print(f"\nDone. External CSV exported to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
