#!/usr/bin/env python3
"""
Export markdown files from content directories.

Supported directories are configured in SOURCE_DIRS. Each directory is
exported into a matching subdirectory under export/.

Produces two versions per file:
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

SOURCE_DIRS = ["books", "lyrics"]


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
    export_root = PROJECT_ROOT / "export"
    export_root.mkdir(parents=True, exist_ok=True)

    any_processed = False

    for dir_name in SOURCE_DIRS:
        src_dir = PROJECT_ROOT / dir_name
        if not src_dir.exists():
            print(f"Skipping {dir_name}/ (not found)")
            continue

        md_files = sorted(
            f for f in src_dir.glob("*.md") if f.name.lower() != "readme.md"
        )
        if not md_files:
            print(f"No .md files found in {dir_name}/")
            continue

        out_dir = export_root / dir_name
        print(f"[{dir_name}] Processing {len(md_files)} file(s)...")
        for f in md_files:
            process_file(f, out_dir)
            any_processed = True

    if not any_processed:
        print("No files were exported.", file=sys.stderr)
        sys.exit(1)

    print(f"\nDone. Exported to {export_root}/")


if __name__ == "__main__":
    main()
