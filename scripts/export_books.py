#!/usr/bin/env python3
"""
Export books from the books/ directory.

Produces two versions per book:
  - original: removes all edit markers, restores the pre-edit text
  - modified: applies all edit markers

Edit marker syntax:
  1. ~~餮~~          → delete (no correction)
  2. ~~餮~~(餐)      → delete and correct
  3. ~~小暑~~()      → delete but unknown correction, leave blank
  4. ++等++          → addition
  5. ++++            → addition placeholder (blank)
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def generate_original(text: str) -> str:
    text = re.sub(r"\+\+\+\+", "", text)
    text = re.sub(r"\+\+([^\n+]+)\+\+", "", text)
    text = re.sub(r"~~([^\n~]+)~~\([^\n)]*\)", r"\1", text)
    text = re.sub(r"~~([^\n~]+)~~", r"\1", text)
    return text


def _replace_correction(m: re.Match) -> str:
    correction = m.group(2)
    return correction if correction else "〔〕"


def generate_modified(text: str) -> str:
    text = re.sub(r"\+\+\+\+", "〔〕", text)
    text = re.sub(r"\+\+([^\n+]+)\+\+", r"\1", text)
    text = re.sub(r"~~([^\n~]+)~~\(([^\n)]*)\)", _replace_correction, text)
    text = re.sub(r"~~([^\n~]+)~~", "", text)
    return text


def process_file(src: Path, out_dir: Path) -> None:
    stem = src.stem
    original_text = src.read_text(encoding="utf-8")

    out_dir.mkdir(parents=True, exist_ok=True)

    original = generate_original(original_text)
    modified = generate_modified(original_text)

    (out_dir / f"{stem}_original.md").write_text(original, encoding="utf-8")
    (out_dir / f"{stem}_modified.md").write_text(modified, encoding="utf-8")

    print(f"  ✓ {stem} → {stem}_original.md, {stem}_modified.md")


def main():
    books_dir = PROJECT_ROOT / "books"
    output_dir = PROJECT_ROOT / "export"

    if not books_dir.exists():
        print(f"Error: {books_dir} not found", file=sys.stderr)
        sys.exit(1)

    md_files = sorted(books_dir.glob("*.md"))
    if not md_files:
        print("No .md files found in books/", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(md_files)} book(s)...")
    for f in md_files:
        process_file(f, output_dir)

    print(f"\nDone. Exported to {output_dir}/")


if __name__ == "__main__":
    main()
