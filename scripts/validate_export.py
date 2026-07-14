#!/usr/bin/env python3
"""Validate exported CSV files for data integrity.

Checks:
  - han: only CJK characters, punctuation, or empty
  - en: only printable ASCII + common Latin extensions (diacritics in scientific names)
  - poj/tl/bp/puj/dp: valid character set + converter roundtrip
  - latn_norm: valid normalized latin form

Categories: ERRORS (true data problems) vs WARNINGS (normalization differences).
Exit code 0 unless ERRORS > 0.
"""

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

EXPORT_DIR = PROJECT_ROOT / "export"
TEOCHEW_CSV = EXPORT_DIR / "teochew.csv"
HOKKIEN_CSV = EXPORT_DIR / "hokkien.csv"
SPLIT_CSVS = [TEOCHEW_CSV, HOKKIEN_CSV]

from scripts.latn import create_converter

_CJK_RANGE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
_ANNOTATION_RE = re.compile(r"\[[^\]]*\]")
_LATN_ANN_CHAR_RE = re.compile(
    r"^[a-zA-Z\u00C0-\u024F\u0300-\u036F\u1E00-\u1EFF\u0358"
    r"\u2070-\u207Fⁿ\u00B7\u002D\u0027\d"
    r"\u00B2\u00B3\u00B9\.\?\!\,\;\:\[\]\(\)\u3001\u3002]*$"
)
_HAN_ALLOWED_EXTRA = frozenset(
    "｜·‐‑‒–—―─│﹂﹁"
    "\u200b\u3000\u3001\u3002\uff01\uff08\uff09\uff0c\uff0e\uff1a\uff1b\uff1f"
)
_HAN_ALLOWED_CATS = frozenset(
    {"Lo", "Mn", "Po", "Pd", "Ps", "Pe", "Pf", "Pi", "Sk", "So"}
)
_EN_ALLOWED = (
    "\u0000-\u007f"
    "\u00a0-\u00ff"
    "\u0100-\u017f"
    "\u0180-\u024f"
    "\u2018\u2019\u201c\u201d\u2013\u2014\u2026"
)
_EN_CHAR_RE = re.compile(f"^[{_EN_ALLOWED}]*$")

_OCR_DIGIT_MAP = {
    "0": "o", "1": "i", "2": "z", "3": "e", "4": "a",
    "5": "s", "6": "g", "7": "t", "8": "b", "9": "q",
}
_PUJ_HAS_DIGIT = re.compile(r"\d")
_PUJ_EN_LEAK = re.compile(r"^[a-z]+(?:\s+[a-z]+){2,}$", re.IGNORECASE)


_PUJ_INVALID_CLUSTER = re.compile(
    r"ss|bb|dd|gg|zz|jj|"
    r"sz|sg|sj|sd|"
    r"zs|zg|zj|zd|"
    r"gs|gz|gj|gd|"
    r"bs|bz|bj|bd|"
    r"ds|dz|dj|"
    r"tz|zt",
    re.IGNORECASE,
)

_PUJ_ILLEGIBLE_RE = re.compile(r"\[illegible[0-9]*\]", re.IGNORECASE)


def validate_puj(value: str) -> list[tuple[str, str, str]]:
    if not value:
        return []
    results = []

    for m in _PUJ_ILLEGIBLE_RE.finditer(value):
        results.append((
            "error",
            "illegible",
            f"pos {m.start()}-{m.end()}: {m.group()!r}",
        ))

    stripped = _ANNOTATION_RE.sub("", value)

    for m in _PUJ_HAS_DIGIT.finditer(stripped):
        d = m.group()
        results.append((
            "error",
            "digit",
            f"pos {m.start()}: digit {d!r}",
        ))

    for m in _PUJ_INVALID_CLUSTER.finditer(stripped):
        cluster = m.group()
        results.append((
            "warning",
            "invalid_cluster",
            f"pos {m.start()}-{m.end()}: {cluster!r}",
        ))

    if _PUJ_EN_LEAK.match(stripped):
        results.append((
            "warning",
            "en_leak",
            f"entire value looks like English: {stripped!r}",
        ))

    return results


def validate_han(value: str) -> list[tuple[str, str]]:
    if not value:
        return []
    errors = []
    for i, ch in enumerate(value):
        if _CJK_RANGE.match(ch):
            continue
        if ch in _HAN_ALLOWED_EXTRA:
            continue
        cat = unicodedata.category(ch)
        if cat in _HAN_ALLOWED_CATS:
            continue
        errors.append(
            (
                "error",
                f"pos {i}: unexpected char {ch!r} (U+{ord(ch):04X}, cat={cat})",
            )
        )
    return errors


def validate_en(value: str) -> list[tuple[str, str]]:
    if not value:
        return []
    errors = []
    for i, ch in enumerate(value):
        if ch.isascii():
            continue
        if _EN_CHAR_RE.match(ch):
            continue
        errors.append(("error", f"pos {i}: unexpected char {ch!r} (U+{ord(ch):04X})"))
    return errors


def _roundtrip_syllables(converter, value: str) -> list[tuple[str, str]]:
    if not value:
        return []
    results = []
    syllables = re.split(r"[-\s]+", value)
    for syllable in syllables:
        if not syllable:
            continue
        try:
            keyboard = converter.to_keyboard(syllable)
            restored = converter.to_handwriting(keyboard)
            norm_orig = unicodedata.normalize("NFC", syllable)
            norm_rest = unicodedata.normalize("NFC", restored)
            if norm_orig != norm_rest:
                results.append(
                    (
                        "warning",
                        f"roundtrip: {syllable!r} -> {keyboard!r} -> {restored!r}",
                    )
                )
        except Exception as e:
            results.append(("error", f"converter error: {e}"))
    return results


def validate_latn(converter, field: str, value: str) -> list[tuple[str, str]]:
    if not value:
        return []
    results = []
    stripped = _ANNOTATION_RE.sub("", value)
    for syl in re.split(r"[-\s]+", stripped):
        if not syl:
            continue
        if not _LATN_ANN_CHAR_RE.match(syl):
            bad = [ch for ch in syl if not _LATN_ANN_CHAR_RE.match(ch)]
            results.append(
                (
                    "warning",
                    f"non-latn char(s) in annotation context: {syl!r} ({bad})",
                )
            )
    results.extend(_roundtrip_syllables(converter, stripped))
    return results


FIELD_SYSTEM = {
    "poj": "POJ",
    "tl": "TL",
    "bp": "BP",
    "puj": "PUJ",
    "dp": "DP",
    "latn_norm": "LATN_NORM",
}


def main():
    parser = argparse.ArgumentParser(description="Validate exported CSV files")
    parser.add_argument(
        "--errors-only", action="store_true", help="Suppress warnings, only show errors"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write output to file (default: stdout)",
    )
    parser.add_argument(
        "--puj",
        type=Path,
        default=None,
        metavar="CSV",
        help="Check PUJ for errors (digits, English leaks) and write to CSV",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Specific file or directory to validate (relative to project root). "
        "Defaults to all export CSVs.",
    )
    args = parser.parse_args()

    out = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    errors_only = args.errors_only
    targets = [Path(p) for p in args.paths]

    try:
        return _run(out, errors_only, targets, puj_output=args.puj)
    finally:
        if out is not sys.stdout:
            out.close()


def _resolve_csv_files(targets: list[Path]) -> list[Path]:
    if not targets:
        csv_files = sorted(EXPORT_DIR.glob("external/*.csv"))
        csv_files += sorted(EXPORT_DIR.glob("clippings/*.csv"))
        csv_files += sorted(EXPORT_DIR.glob("books/*.csv"))
        for split_csv in SPLIT_CSVS:
            if split_csv.exists():
                csv_files.append(split_csv)
        return csv_files

    resolved = []
    for t in targets:
        if not t.is_absolute():
            t = PROJECT_ROOT / t
        if t.is_file():
            resolved.append(t)
        elif t.is_dir():
            resolved.extend(sorted(t.glob("*.csv")))
        else:
            print(f"WARNING: path not found: {t}", file=sys.stderr)
    return resolved


def _run(out, errors_only: bool, targets: list[Path], puj_output: Path | None = None) -> int:
    def log(msg: str):
        print(msg, file=out)

    converters = {}
    for name in FIELD_SYSTEM.values():
        try:
            converters[name] = create_converter(name)
        except Exception as e:
            log(f"WARNING: cannot create converter for {name}: {e}")

    csv_files = _resolve_csv_files(targets)

    total_errors = 0
    total_warnings = 0
    total_rows = 0
    error_kinds = Counter()

    puj_writer = None
    puj_file = None
    puj_count = 0
    puj_rows = []
    if puj_output:
        puj_output.parent.mkdir(parents=True, exist_ok=True)

    try:
        for csv_file in csv_files:
            file_errors = 0
            file_warnings = 0
            file_rows = 0
            rel = csv_file.relative_to(PROJECT_ROOT)
            log(f"\nValidating {rel} ...")

            with open(csv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    log("  SKIP: no header")
                    continue
                for row_num, row in enumerate(reader, 2):
                    file_rows += 1

                    row_had_error = False
                    row_errors = []
                    row_warnings = []

                    for check_fn, fld in [(validate_han, "han"), (validate_en, "en")]:
                        val = row.get(fld, "")
                        if not val:
                            continue
                        for level, msg in check_fn(val):
                            if level == "error" and fld == "en":
                                level = "warning"
                            if level == "error":
                                file_errors += 1
                                row_errors.append(f"{fld}: [{level}] {msg}")
                            else:
                                file_warnings += 1
                                row_warnings.append(f"{fld}: [{level}] {msg}")

                    for fld, sys_name in FIELD_SYSTEM.items():
                        val = row.get(fld, "")
                        if not val or sys_name not in converters:
                            continue
                        for level, msg in validate_latn(converters[sys_name], fld, val):
                            error_kinds[f"{fld}:{msg.split(':')[0]}"] += 1
                            if level == "error":
                                file_errors += 1
                                row_errors.append(f"{fld}: [{level}] {msg}")
                            else:
                                file_warnings += 1
                                row_warnings.append(f"{fld}: [{level}] {msg}")

                    if puj_output:
                        puj_val = row.get("puj", "")
                        if puj_val:
                            han_val = row.get("han", "")
                            en_val = row.get("en", "")
                            page_val = row.get("page_num", "")
                            for level, etype, detail in validate_puj(puj_val):
                                if level == "error":
                                    puj_rows.append((
                                        page_val, row_num, puj_val, han_val, en_val, etype, detail,
                                    ))
                                puj_count += 1

                    if row_errors:
                        row_dump = "  |  ".join(f"{k}={v}" for k, v in row.items() if v)
                        log(f"  row {row_num}: {row_dump}")
                        for e in row_errors:
                            log(f"    {e}")

                    if not errors_only:
                        for w in row_warnings:
                            log(f"  row {row_num} {w}")

            log(f"  {file_rows} rows, {file_errors} errors, {file_warnings} warnings")
            total_errors += file_errors
            total_warnings += file_warnings
            total_rows += file_rows

        log(f"\n{'=' * 60}")
        if error_kinds and not errors_only:
            log("Top warning/error kinds:")
            for kind, count in error_kinds.most_common(20):
                log(f"  {count:6d}  {kind}")
        log(
            f"Total: {total_rows} rows, {total_errors} errors, "
            f"{total_warnings} warnings across {len(csv_files)} files"
        )
    finally:
        if puj_output:
            puj_rows.sort(key=lambda r: (
                int(r[0]) if r[0] and r[0].isdigit() else 0,
                r[1],
            ))
            with open(puj_output, "w", newline="", encoding="utf-8") as puj_file:
                puj_writer = csv.writer(puj_file)
                puj_writer.writerow(["page_num", "row", "puj", "han", "en", "error_type", "error_detail"])
                puj_writer.writerows(puj_rows)
            log(f"PUJ errors written to {puj_output} ({len(puj_rows)} rows)")

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
