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

SOURCE_DIRS = ["books", "clippings", "lyrics"]
PROCESSORS_DIR = PROJECT_ROOT / "scripts" / "processors"
CSV_FIELDS = [
    "puj",
    "puj_orig",
    "poj",
    "poj_orig",
    "han",
    "han_orig",
    "fanqie",
    "en",
    "en_orig",
    "zh_TW",
    "zh_CN",
    "source",
    "page_num",
]

def _get_field(field: str, entry) -> str:
    val = getattr(entry, field, "")
    if field.endswith("_orig"):
        base = field.replace("_orig", "")
        orig = val
        main = getattr(entry, base, "")
        return orig if orig != main else ""
    return val


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

        ext = "*.csv" if dir_name == "clippings" else "*.md"
        md_files = sorted(f for f in src_dir.glob(ext) if f.name.lower() != "readme.md")
        if not md_files:
            continue

        out_dir = export_root / dir_name
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"[{dir_name}] Processing {len(md_files)} file(s) for CSV export...")

        for md_file in md_files:
            if dir_name == "clippings":
                processor = find_processor(dir_name)
                if processor is None:
                    print(f"  ⚠ No processor for clippings, skipping")
                    continue
                source_name = md_file.stem
            else:
                processor = find_processor(md_file.stem)
                if processor is None:
                    print(f"  ⚠ No processor for {md_file.stem}, skipping")
                    continue
                source_name = md_file.stem

            text = md_file.read_text(encoding="utf-8")
            entries = processor.extract_entries(text, source_name)
            entries.sort(key=lambda e: (e.puj or e.poj or "").lower())

            active = [f for f in CSV_FIELDS if any(getattr(e, f, "") for e in entries)]

            csv_path = out_dir / f"{md_file.stem}.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(active)
                for entry in entries:
                    row = []
                    for field in active:
                        val = getattr(entry, field, "")
                        if field.endswith("_orig"):
                            base = field.replace("_orig", "")
                            if val == getattr(entry, base, ""):
                                val = ""
                        row.append(val)
                    writer.writerow(row)

            print(f"  ✓ {md_file.stem} → {md_file.stem}.csv ({len(entries)} entries, {len(active)} cols)")
            any_processed = True

    if not any_processed:
        print("No CSV files were exported.", file=sys.stderr)
        sys.exit(1)

    print(f"\nDone. CSV exported to {export_root}/")


if __name__ == "__main__":
    main()
