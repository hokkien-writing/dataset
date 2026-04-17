#!/usr/bin/env python3
"""
Merge CSV files from export/books/ into a single wide table.

Columns: puj, dp, poj, tl, bp, han, han_variants, en, zh_CN, zh_TW, source

- puj: Peng'im romanization (from existing CSV)
- dp, poj, tl, bp: other romanization systems (reserved, empty for now)
- han: Chinese characters (from han column)
- han_variants: variant forms from han_orig + variants.csv lookup
- en: en definition (from en column)
- zh_CN, zh_TW: Chinese translations (reserved, empty for now)
- source: provenance
"""

import csv
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = PROJECT_ROOT / "export"
BOOKS_DIR = EXPORT_DIR / "books"
VARIANTS_CSV = EXPORT_DIR / "variants.csv"
CAPITALIZED_CSV = EXPORT_DIR / "capitalized_en.csv"
OUTPUT_CSV = EXPORT_DIR / "merged.csv"

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

_WORD_RE = re.compile(r"[a-zA-Z]+")


def _load_capitalized_en(path: Path) -> frozenset[str]:
    if not path.exists():
        return frozenset()
    words = set()
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            w = row.get("word", "").strip()
            if w:
                words.add(w)
    return frozenset(words)


CAPITALIZED_EN = _load_capitalized_en(CAPITALIZED_CSV)


def lower_first_en(text: str) -> str:
    if not text or not text[0].isupper():
        return text
    m = _WORD_RE.match(text)
    if m and m.group(0) in CAPITALIZED_EN:
        return text
    return text[0].lower() + text[1:]


def load_char_variants(path: Path) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    if not path.exists():
        return mapping
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rec = row["recommend"]
            variants: list[str] = []
            for k in ("variant_1", "variant_2", "variant_3"):
                v = (row.get(k) or "").strip()
                if v:
                    variants.append(v)
            if variants:
                mapping[rec] = variants
    return mapping


def _product(choices: list[list[str]]) -> list[tuple[str, ...]]:
    if not choices:
        return [()]
    rest = _product(choices[1:])
    return [(v, *r) for v in choices[0] for r in rest]


def _find_matches(
    han: str, variants: dict[str, list[str]]
) -> list[tuple[int, int, list[str]]]:
    keys_by_len = sorted(variants.keys(), key=len, reverse=True)
    matches: list[tuple[int, int, list[str]]] = []
    used: list[tuple[int, int]] = []
    pos = 0
    while pos < len(han):
        found = False
        for key in keys_by_len:
            klen = len(key)
            if han[pos : pos + klen] == key:
                overlap = any(s < pos + klen and e > pos for s, e in used)
                if not overlap:
                    matches.append((pos, pos + klen, [key, *variants[key]]))
                    used.append((pos, pos + klen))
                    pos += klen
                    found = True
                    break
        if not found:
            pos += 1
    return matches


def build_han_variants(han: str, variants: dict[str, list[str]]) -> str:
    if not han:
        return ""
    matches = _find_matches(han, variants)
    if not matches:
        return ""
    groups: dict[str, tuple[list[tuple[int, int]], list[str]]] = {}
    for start, end, opts in matches:
        key = han[start:end]
        if key not in groups:
            groups[key] = ([], opts)
        groups[key][0].append((start, end))
    unique_keys = list(dict.fromkeys(han[s:e] for s, e, _ in matches))
    choices: list[list[str]] = [groups[k][1] for k in unique_keys]
    parts: list[str] = []
    for combo in _product(choices):
        result = list(han)
        for key, rep in zip(unique_keys, combo):
            if key != rep:
                for start, end in groups[key][0]:
                    for i in range(start, end):
                        result[i] = ""
                    result[start] = rep
        parts.append("".join(result))
    return "|".join(p for p in parts if p != han)


def main():
    char_variants = load_char_variants(VARIANTS_CSV)
    rows: list[dict[str, str]] = []

    csv_files = sorted(BOOKS_DIR.glob("*.csv"))
    if not csv_files:
        print("No CSV files found", BOOKS_DIR)
        return

    for csv_file in csv_files:
        print(f"Reading {csv_file.name}...")
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                han = row.get("han", "")
                rec = {
                    "puj": row.get("puj", "").lower(),
                    "dp": "",
                    "poj": "",
                    "tl": "",
                    "bp": "",
                    "han": han,
                    "han_variants": build_han_variants(han, char_variants),
                    "en": lower_first_en(row.get("en", "")),
                    "zh_CN": "",
                    "zh_TW": "",
                    "source": row.get("source", "").split(" > ")[0],
                }
                rows.append(rec)

    rows.sort(key=lambda r: r["puj"].lower())

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=WIDE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} entries to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
