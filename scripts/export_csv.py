#!/usr/bin/env python3
"""
Export structured CSV from content directories.

For each .md file, auto-discovers a matching processor in
scripts/processors/{stem}.py. If found, extracts structured
entries and writes them to CSV.
"""

import csv
import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SOURCE_DIRS = ["books", "lyrics"]
PROCESSORS_DIR = PROJECT_ROOT / "scripts" / "processors"
CSV_FIELDS = [
    "puj",
    "puj_orig",
    "teochew",
    "teochew_orig",
    "english",
    "english_orig",
    "source",
]


def find_processor(stem: str):
    proc_file = PROCESSORS_DIR / f"{stem}.py"
    if not proc_file.exists():
        return None

    from scripts.processors.base import BookProcessor

    module = importlib.import_module(f"scripts.processors.{stem}")
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, BookProcessor)
            and attr is not BookProcessor
        ):
            return attr()
    return None


def main():
    export_root = PROJECT_ROOT / "export"
    export_root.mkdir(parents=True, exist_ok=True)

    any_processed = False

    for dir_name in SOURCE_DIRS:
        src_dir = PROJECT_ROOT / dir_name
        if not src_dir.exists():
            continue

        md_files = sorted(
            f for f in src_dir.glob("*.md") if f.name.lower() != "readme.md"
        )
        if not md_files:
            continue

        out_dir = export_root / dir_name
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"[{dir_name}] Processing {len(md_files)} file(s) for CSV export...")

        for md_file in md_files:
            processor = find_processor(md_file.stem)
            if processor is None:
                print(f"  ⚠ No processor for {md_file.stem}, skipping")
                continue

            text = md_file.read_text(encoding="utf-8")
            entries = processor.extract_entries(text, md_file.stem)
            entries.sort(key=lambda e: e.puj.lower())

            csv_path = out_dir / f"{md_file.stem}.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_FIELDS)
                for entry in entries:
                    writer.writerow(
                        [
                            entry.puj,
                            entry.puj_orig if entry.puj_orig != entry.puj else "",
                            entry.teochew,
                            entry.teochew_orig
                            if entry.teochew_orig != entry.teochew
                            else "",
                            entry.english,
                            entry.english_orig
                            if entry.english_orig != entry.english
                            else "",
                            entry.source,
                        ]
                    )

            print(f"  ✓ {md_file.stem} → {md_file.stem}.csv ({len(entries)} entries)")
            any_processed = True

    if not any_processed:
        print("No CSV files were exported.", file=sys.stderr)
        sys.exit(1)

    print(f"\nDone. CSV exported to {export_root}/")


if __name__ == "__main__":
    main()
