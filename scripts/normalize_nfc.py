#!/usr/bin/env python3
"""Normalize text files to Unicode NFC.

Combining marks such as U+0324 (diaeresis below) and U+0301 (acute) must appear
in canonical order (ccc 220 before ccc 230). Files written by OCR or manual
editing often store them in the wrong order, which renders incorrectly and
breaks grep/dedup/CSV comparison even though the sequences are canonically
equivalent.

NFC normalization is lossless: the result is canonically equivalent to the
input, so no romanization information is lost.

Usage:
    python3 scripts/normalize_nfc.py books/*.csv
    python3 scripts/normalize_nfc.py --check books/
    python3 scripts/normalize_nfc.py --dry-run books/ --ext .csv --ext .md
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

DEFAULT_EXTS = (".csv", ".md", ".txt", ".tsv", ".yaml", ".yml")
SKIP_DIRS = frozenset({".git", ".venv", "__pycache__", "node_modules"})


def collect_files(paths: list[Path], exts: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if SKIP_DIRS & set(child.parts):
                    continue
                if child.is_file() and child.suffix.lower() in exts:
                    files.append(child)
        else:
            print(f"WARNING: path not found: {path}", file=sys.stderr)
    return files


def count_changed_lines(original: str, normalized: str) -> int:
    return sum(
        1
        for a, b in zip(original.splitlines(), normalized.splitlines())
        if a != b
    )


def normalize_file(path: Path, write: bool) -> int:
    original = path.read_text(encoding="utf-8")
    normalized = unicodedata.normalize("NFC", original)
    if normalized == original:
        return 0
    changed = count_changed_lines(original, normalized)
    if write:
        path.write_text(normalized, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize text files to Unicode NFC")
    parser.add_argument("paths", nargs="+", type=Path, help="Files or directories")
    parser.add_argument(
        "--ext",
        action="append",
        dest="exts",
        default=None,
        help=f"Extension filter for directories (default: {' '.join(DEFAULT_EXTS)})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report files needing normalization only"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Like --dry-run but exit 1 if any file is not NFC",
    )
    args = parser.parse_args()

    exts = tuple(e.lower() if e.startswith(".") else f".{e.lower()}" for e in args.exts) if args.exts else DEFAULT_EXTS
    write = not (args.dry_run or args.check)

    files = collect_files(args.paths, exts)
    total_lines = 0
    changed_files = 0

    for path in files:
        try:
            changed = normalize_file(path, write)
        except UnicodeDecodeError:
            print(f"SKIP (not utf-8): {path}", file=sys.stderr)
            continue
        if changed:
            changed_files += 1
            total_lines += changed
            action = "would normalize" if not write else "normalized"
            print(f"{action}: {path} ({changed} lines)")

    print(
        f"\n{changed_files}/{len(files)} files, {total_lines} lines "
        f"{'to change' if not write else 'changed'}"
    )

    return 1 if args.check and changed_files else 0


if __name__ == "__main__":
    sys.exit(main())
