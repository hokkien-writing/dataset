#!/usr/bin/env python3
"""
Export structured CSV from content directories.

For each .md file, auto-discovers a matching processor in
scripts/processors/{stem}.py. If found, extracts structured
entries and writes them to CSV.
"""

import csv
import argparse
import importlib
import re
import sys
from pathlib import Path

from scripts.punctuation import normalize_english_gloss, normalize_roman_reading

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_ILLEGIBLE_RE = re.compile(r"\[illegible[0-9]*\]", re.IGNORECASE)

SOURCE_DIRS = ["books", "clippings", "lyrics"]
PROCESSORS_DIR = PROJECT_ROOT / "scripts" / "processors"
CSV_FIELDS = [
    "puj",
    "puj_proofread",
    "puj_orig",
    "poj",
    "poj_orig",
    "han",
    "han_orig",
    "en",
    "en_orig",
    "zh_TW",
    "zh_CN",
    "source",
    "page_num",
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export structured CSV from content sources")
    parser.add_argument(
        "--book",
        dest="books",
        action="append",
        default=[],
        metavar="STEM",
        help="export only books/STEM.md; may be repeated",
    )
    parser.add_argument(
        "--preserve-order",
        action="store_true",
        help="write entries in processor order instead of sorting by reading",
    )
    return parser.parse_args(argv)


def resolve_books(stems: list[str], books_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for stem in stems:
        path = books_dir / f"{stem}.md"
        if not path.is_file():
            raise ValueError(f"book not found: {stem}")
        paths.append(path)
    return paths


def order_entries(entries: list, preserve_order: bool) -> list:
    if not preserve_order:
        entries.sort(key=lambda entry: (entry.puj or entry.poj or "").lower())
    return entries


def normalize_entry_punctuation(entry) -> None:
    entry.en = normalize_english_gloss(entry.en) if entry.en else ""
    for field in ("puj", "poj", "dp", "bp", "tl"):
        value = getattr(entry, field)
        if value:
            setattr(entry, field, normalize_roman_reading(value, entry.en))


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    export_root = PROJECT_ROOT / "export"
    export_root.mkdir(parents=True, exist_ok=True)

    any_processed = False

    if args.books:
        try:
            selected_books = resolve_books(args.books, PROJECT_ROOT / "books")
        except ValueError as error:
            raise SystemExit(str(error)) from error
        source_files = [("books", selected_books)]
    else:
        source_files = []
        for dir_name in SOURCE_DIRS:
            src_dir = PROJECT_ROOT / dir_name
            if not src_dir.exists():
                continue
            ext = "*.csv" if dir_name == "clippings" else "*.md"
            files = sorted(
                file for file in src_dir.glob(ext) if file.name.lower() != "readme.md"
            )
            if files:
                source_files.append((dir_name, files))

    for dir_name, md_files in source_files:
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
                    if args.books:
                        raise SystemExit(f"no processor for requested book: {md_file.stem}")
                    print(f"  ⚠ No processor for {md_file.stem}, skipping")
                    continue
                source_name = md_file.stem

            text = md_file.read_text(encoding="utf-8")
            entries = processor.extract_entries(text, source_name)
            entries = [
                e for e in entries
                if not _ILLEGIBLE_RE.search(e.puj) and not _ILLEGIBLE_RE.search(e.poj)
            ]
            for entry in entries:
                normalize_entry_punctuation(entry)
            order_entries(entries, args.preserve_order)

            csv_path = out_dir / f"{md_file.stem}.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_FIELDS)
                for entry in entries:
                    writer.writerow(
                        [
                            entry.puj,
                            entry.puj_proofread,
                            entry.puj_orig,
                            entry.poj,
                            entry.poj_orig if entry.poj_orig != entry.poj else "",
                            entry.han,
                            entry.han_orig if entry.han_orig != entry.han else "",
                            entry.en,
                            entry.en_orig if entry.en_orig != entry.en else "",
                            entry.zh_TW,
                            entry.zh_CN,
                            entry.source,
                            entry.page_num,
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
