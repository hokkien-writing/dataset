#!/usr/bin/env python3
"""
Merge CSV files from export/books/ into a single wide table.

Columns: latn_norm, puj, dp, poj, tl, bp, han, han_variants, en, zh_CN, zh_TW, source

- latn_norm: normalized latin form (auto-generated from puj via translator)
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
import sys
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
EXPORT_DIR = PROJECT_ROOT / "export"
BOOKS_DIR = EXPORT_DIR / "books"
CLIPPINGS_DIR = EXPORT_DIR / "clippings"
EXTERNAL_DIR = EXPORT_DIR / "external"
VARIANTS_CSV = EXPORT_DIR / "variants.csv"
CAPITALIZED_CSV = EXPORT_DIR / "capitalized_en.csv"
OUTPUT_CSV = EXPORT_DIR / "merged.csv"

WIDE_FIELDS = [
    "latn_norm",
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

from scripts.latn import create_translator

_puj_to_latn_norm = create_translator("PUJ", "LATN_NORM")
_poj_to_latn_norm = create_translator("POJ", "LATN_NORM")
_tl_to_latn_norm = create_translator("TL", "LATN_NORM")
_dp_to_latn_norm = create_translator("DP", "LATN_NORM")

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

    for csv_file in csv_files:
        print(f"Reading {csv_file.name}...")
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                puj_val = row.get("puj", "").lower()
                poj_val = (row.get("poj") or "").lower()
                han = row.get("han", "")
                latn_norm = ""
                if puj_val:
                    try:
                        latn_norm = _puj_to_latn_norm.translate(puj_val).lower()
                    except Exception:
                        pass
                if not latn_norm and poj_val:
                    try:
                        latn_norm = _poj_to_latn_norm.translate(poj_val).lower()
                    except Exception:
                        pass
                rec = {
                    "latn_norm": latn_norm,
                    "puj": puj_val,
                    "dp": "",
                    "poj": poj_val,
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

    clip_files = sorted(CLIPPINGS_DIR.glob("*.csv")) if CLIPPINGS_DIR.exists() else []
    if clip_files:
        for csv_file in clip_files:
            print(f"Reading clippings/{csv_file.name}...")
            with open(csv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    puj_val = (row.get("puj") or "").strip().lower()
                    poj_val = (row.get("poj") or "").strip().lower()
                    han = (row.get("han") or "").strip()
                    latn_norm = ""
                    if puj_val:
                        try:
                            latn_norm = _puj_to_latn_norm.translate(puj_val).lower()
                        except Exception:
                            pass
                    if not latn_norm and poj_val:
                        try:
                            latn_norm = _poj_to_latn_norm.translate(poj_val).lower()
                        except Exception:
                            pass
                    rows.append(
                        {
                            "latn_norm": latn_norm,
                            "puj": puj_val,
                            "dp": "",
                            "poj": poj_val,
                            "tl": "",
                            "bp": "",
                            "han": han,
                            "han_variants": "",
                            "en": (row.get("en") or "").strip(),
                            "zh_CN": (row.get("zh_CN") or "").strip(),
                            "zh_TW": (row.get("zh_TW") or "").strip(),
                            "source": (row.get("source") or csv_file.stem)
                            .strip()
                            .split(" > ")[0],
                        }
                    )
        print(f"Loaded {sum(1 for r in rows)} total entries (incl. clippings)")

    ext_files = sorted(EXTERNAL_DIR.glob("*.csv")) if EXTERNAL_DIR.exists() else []
    if ext_files:
        # 如果中括號中沒有漢字，則連同中括號一起移除
        pattern = r"\[[^\[\]\u4e00-\u9fff]*\]"

        # Fix: ⁿ̌ → nň (nasalization + tone 6 should be n + caron, not superscript n + caron)
        _NNAI_G = re.compile(r"ⁿ̌([gm])")

        def _fix_nasal_tone6(val: str) -> str:
            if not val:
                return val
            # ⁿ̌g → nňg, ⁿ̌m → nňm
            val = _NNAI_G.sub(r"nň\1", val)
            return val

        for csv_file in ext_files:
            print(f"Reading external/{csv_file.name}...")
            with open(csv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    latn_norm = (row.get("latn_norm") or "").strip().lower()
                    puj_val = (row.get("puj") or "").strip(":#-.")
                    poj_val = (row.get("poj") or "").strip(":#-.")
                    tl_val = (row.get("tl") or "").strip(":#-.")
                    poj_val = _fix_nasal_tone6(poj_val)
                    tl_val = _fix_nasal_tone6(tl_val)
                    dp_val = (row.get("dp") or "").strip(":#-.")
                    bp_val = (row.get("bp") or "").strip(":#-.")
                    han = (row.get("han") or "").strip(":#-")
                    poj_val = re.sub(pattern, "", poj_val).strip()
                    tl_val = re.sub(pattern, "", tl_val).strip()
                    # 如果 poj_val 沒有英文字母，則跳過
                    if poj_val and re.search(r"[a-z]", poj_val) is None:
                        continue
                    # 如果 poj_val 不是英文字母開頭，則跳過
                    if poj_val and not (
                        poj_val and poj_val[0].isascii() and poj_val[0].isalpha()
                    ):
                        continue

                    if poj_val == "牛角oâiⁿ":
                        print(poj_val)

                    if not latn_norm and puj_val:
                        try:
                            latn_norm = _puj_to_latn_norm.translate(puj_val).lower()
                        except Exception:
                            pass
                    if not latn_norm and poj_val:
                        try:
                            latn_norm = _poj_to_latn_norm.translate(poj_val).lower()
                        except Exception:
                            pass
                    if not latn_norm and tl_val:
                        try:
                            latn_norm = _tl_to_latn_norm.translate(tl_val).lower()
                        except Exception:
                            pass
                    if not latn_norm and dp_val:
                        try:
                            latn_norm = _dp_to_latn_norm.translate(dp_val).lower()
                        except Exception:
                            pass
                    rows.append(
                        {
                            "latn_norm": latn_norm,
                            "puj": puj_val,
                            "dp": dp_val,
                            "poj": poj_val,
                            "tl": tl_val,
                            "bp": bp_val,
                            "han": han,
                            "han_variants": "",
                            "en": lower_first_en((row.get("en") or "").strip()),
                            "zh_CN": (row.get("zh_CN") or "").strip(),
                            "zh_TW": (row.get("zh_TW") or "").strip(),
                            "source": (row.get("source") or "").strip().split(" > ")[0],
                        }
                    )
        print(f"Loaded {sum(1 for r in rows)} total entries (incl. external)")

    rows.sort(key=lambda r: r["latn_norm"])

    latn_fields = {"latn_norm", "puj", "dp", "poj", "tl", "bp"}
    for row in rows:
        for k in latn_fields:
            v = row.get(k, "")
            if v:
                row[k] = unicodedata.normalize("NFC", v)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=WIDE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} entries to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
