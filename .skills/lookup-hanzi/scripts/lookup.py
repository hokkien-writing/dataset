#!/usr/bin/env python3
import csv
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.latn import create_translator

MERGED_CSV = PROJECT_ROOT / "export" / "merged.csv"


def load_merged():
    rows = []
    with open(MERGED_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def translate_word(word, system):
    translator = create_translator(system, "LATN_NORM")
    parts = word.split("-")
    norm_parts = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        try:
            n = translator.translate(p).lower()
        except Exception:
            n = p.lower()
        norm_parts.append(n)
    return "-".join(norm_parts)


def lookup_word_level(latn_norm_word, rows):
    results = []
    for row in rows:
        row_latn = (row.get("latn_norm") or "").strip()
        if not row_latn:
            continue
        row_latn_parts = [p.strip() for p in row_latn.split(",") if p.strip()]
        for rlp in row_latn_parts:
            if rlp == latn_norm_word:
                han = (row.get("han") or "").strip()
                han_var = (row.get("han_variants") or "").strip()
                en = (row.get("en") or "").strip()
                zh = (row.get("zh_TW") or "").strip()
                puj = (row.get("puj") or "").strip()
                if han:
                    results.append({"han": han, "en": en, "zh_TW": zh, "puj": puj})
                for v in han_var.split("|"):
                    v = v.strip()
                    if v:
                        results.append({"han": v, "en": en, "zh_TW": zh, "puj": puj, "variant": True})
                break
    return results


def lookup_syllable_level(syllable, rows):
    candidates = Counter()
    examples = {}
    for row in rows:
        row_latn = (row.get("latn_norm") or "").strip()
        if not row_latn:
            continue
        for rlp in row_latn.split(","):
            rlp = rlp.strip()
            if rlp == syllable:
                han = (row.get("han") or "").strip()
                if han and len(han) == 1:
                    candidates[han] += 1
                    if han not in examples:
                        en = (row.get("en") or "").strip()
                        examples[han] = en
    return [(han, cnt, examples.get(han, "")) for han, cnt in candidates.most_common(12)]


def format_results(words_input, system, rows):
    lines = []
    for word_input in words_input:
        word_input = word_input.strip()
        if not word_input:
            continue

        latn_word = translate_word(word_input, system)
        syllables = [s.strip() for s in latn_word.split("-") if s.strip()]
        syllable_count = len(syllables)

        lines.append(f"=== {word_input} ({system} → {latn_word}) ===")

        word_results = lookup_word_level(latn_word, rows)
        if word_results:
            lines.append(f"  詞級匹配 ({len(word_results)} 筆):")
            seen = set()
            for r in word_results:
                han = r["han"]
                if han in seen:
                    continue
                seen.add(han)
                tag = " [異]" if r.get("variant") else ""
                parts = [f"    {han}{tag}"]
                if r["en"]:
                    parts.append(f"en={r['en']}")
                if r["zh_TW"]:
                    parts.append(f"zh={r['zh_TW']}")
                if r["puj"]:
                    parts.append(f"puj={r['puj']}")
                lines.append(" | ".join(parts))

        for i, syl in enumerate(syllables):
            syl_results = lookup_syllable_level(syl, rows)
            if syl_results:
                cands = " ".join(f"{h}(x{c})" for h, c, _ in syl_results)
                ens = " | ".join(f"{h}={e}" for h, c, e in syl_results if e)
                pos = f"[{i+1}/{syllable_count}]" if syllable_count > 1 else ""
                lines.append(f"  音節 {syl} {pos}: {cands}")
                if ens:
                    lines.append(f"    en: {ens}")

        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: lookup.py <SYSTEM> <text> [<text> ...]")
        print("  SYSTEM: PUJ DP POJ TL BP")
        print("  text: romanized word(s), space-separated")
        sys.exit(1)

    system = sys.argv[1].upper()
    words = sys.argv[2:]

    rows = load_merged()
    output = format_results(words, system, rows)
    print(output)


if __name__ == "__main__":
    main()
