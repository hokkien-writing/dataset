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

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.processors.base import generate_modified, generate_original

SOURCE_DIRS = ["books", "lyrics"]


def process_file(src: Path, out_dir: Path) -> None:
    stem = src.stem
    original_text = src.read_text(encoding="utf-8")

    out_dir.mkdir(parents=True, exist_ok=True)

    original = generate_original(original_text)
    modified = generate_modified(original_text, placeholder="〔〕")

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
