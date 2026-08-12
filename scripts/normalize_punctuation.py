from __future__ import annotations

import argparse
import csv
import json
import os
import re
import tempfile
from pathlib import Path

from scripts.punctuation import to_chinese_punctuation, to_roman_punctuation

PROOFREAD_CHINESE_FIELDS = ("字目", "词条")
PROOFREAD_ROMAN_FIELDS = ("读音", "释义")
PROOFREAD_ROMAN_READING_FIELDS = ("读音",)
_TRAILING_READING_SEMICOLON_RE = re.compile(r"(?:;\s*)+$")


def _temporary_path(target: Path) -> Path:
    handle = tempfile.NamedTemporaryFile(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    )
    handle.close()
    return Path(handle.name)


def _replace_file(temporary: Path, target: Path) -> None:
    if target.exists():
        os.chmod(temporary, target.stat().st_mode)
    temporary.replace(target)


def normalize_csv(
    path: Path,
    chinese_fields: tuple[str, ...],
    roman_fields: tuple[str, ...],
    roman_reading_fields: tuple[str, ...] = (),
) -> dict[str, object]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if fieldnames is None:
        raise ValueError("CSV is missing a header")
    missing = [
        field
        for field in (*chinese_fields, *roman_fields, *roman_reading_fields)
        if field not in fieldnames
    ]
    if missing:
        raise ValueError(f"CSV is missing required fields: {', '.join(missing)}")
    invalid_reading_fields = set(roman_reading_fields) - set(roman_fields)
    if invalid_reading_fields:
        raise ValueError("Roman reading fields must also be Roman fields")

    field_changes = {field: 0 for field in (*chinese_fields, *roman_fields)}
    changed_rows = 0
    for row in rows:
        row_changed = False
        for field in chinese_fields:
            value = to_chinese_punctuation(row[field])
            if value != row[field]:
                row[field] = value
                field_changes[field] += 1
                row_changed = True
        for field in roman_fields:
            value = to_roman_punctuation(row[field])
            if field in roman_reading_fields:
                value = _TRAILING_READING_SEMICOLON_RE.sub("", value)
            if value != row[field]:
                row[field] = value
                field_changes[field] += 1
                row_changed = True
        changed_rows += row_changed

    temporary = _temporary_path(path)
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        with temporary.open(encoding="utf-8", newline="") as handle:
            check = csv.DictReader(handle)
            check_rows = list(check)
        if check.fieldnames != fieldnames or len(check_rows) != len(rows):
            raise ValueError("CSV verification failed")
        _replace_file(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()

    return {
        "rows": len(rows),
        "changed_rows": changed_rows,
        "fields": field_changes,
    }


def normalize_text(path: Path, output: Path, mode: str) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    converter = to_roman_punctuation if mode == "roman" else to_chinese_punctuation
    normalized = converter(source)
    temporary = _temporary_path(output)
    try:
        temporary.write_text(normalized, encoding="utf-8")
        _replace_file(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"characters": len(source), "changed": source != normalized}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize Chinese and Roman punctuation")
    parser.add_argument("input", type=Path)
    parser.add_argument("--mode", choices=("roman", "chinese", "proofread-csv"), required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not args.input.is_file():
        raise SystemExit(f"Input file does not exist: {args.input}")
    if args.mode == "proofread-csv":
        if args.output is not None and args.output != args.input:
            raise SystemExit("proofread-csv mode updates the input file in place")
        summary = normalize_csv(
            args.input,
            chinese_fields=PROOFREAD_CHINESE_FIELDS,
            roman_fields=PROOFREAD_ROMAN_FIELDS,
            roman_reading_fields=PROOFREAD_ROMAN_READING_FIELDS,
        )
    else:
        output = args.output or args.input
        output.parent.mkdir(parents=True, exist_ok=True)
        summary = normalize_text(args.input, output, args.mode)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
