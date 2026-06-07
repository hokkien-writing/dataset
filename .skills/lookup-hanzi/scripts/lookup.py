#!/usr/bin/env python3
import csv
import sys
from collections import Counter
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from latn import create_translator

TEOCHEW_CSV = SKILL_DIR / "data" / "teochew.csv"
HOKKIEN_CSV = SKILL_DIR / "data" / "hokkien.csv"

TEOCHEW_SYSTEMS = {"PUJ", "DP"}
HOKKIEN_SYSTEMS = {"POJ", "TL", "BP"}


def load_csv(path):
    rows = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8") as f:
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


def _get_romanization(row, system):
    return (row.get(system.lower()) or "").strip()


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
                if han:
                    results.append({"han": han, "en": en, "zh_TW": zh})
                for v in han_var.split("|"):
                    v = v.strip()
                    if v:
                        results.append(
                            {"han": v, "en": en, "zh_TW": zh, "variant": True}
                        )
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
    return [
        (han, cnt, examples.get(han, "")) for han, cnt in candidates.most_common(12)
    ]


def format_results(words_input, system, primary_rows, secondary_rows):
    lines = []
    is_teochew = system in TEOCHEW_SYSTEMS
    lang_label = "潮州" if is_teochew else "福建"
    sec_label = "福建" if is_teochew else "潮州"

    for word_input in words_input:
        word_input = word_input.strip()
        if not word_input:
            continue

        latn_word = translate_word(word_input, system)
        syllables = [s.strip() for s in latn_word.split("-") if s.strip()]
        syllable_count = len(syllables)

        lines.append(f"=== {word_input} ({system} → {latn_word}) ===")

        primary_word = lookup_word_level(latn_word, primary_rows)
        if primary_word:
            lines.append(f"  {lang_label}詞級匹配 ({len(primary_word)} 筆):")
            seen = set()
            for r in primary_word:
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
                lines.append(" | ".join(parts))

        secondary_word = lookup_word_level(latn_word, secondary_rows)
        if secondary_word:
            lines.append(f"  {sec_label}參考匹配 ({len(secondary_word)} 筆):")
            seen = set()
            for r in secondary_word:
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
                lines.append(" | ".join(parts))

        primary_syl = {
            syl: lookup_syllable_level(syl, primary_rows) for syl in syllables
        }
        secondary_syl = {
            syl: lookup_syllable_level(syl, secondary_rows) for syl in syllables
        }

        for i, syl in enumerate(syllables):
            p_results = primary_syl.get(syl, [])
            s_results = secondary_syl.get(syl, [])

            pos = f"[{i + 1}/{syllable_count}]" if syllable_count > 1 else ""
            if p_results:
                cands = " ".join(f"{h}(x{c})" for h, c, _ in p_results)
                lines.append(f"  {lang_label}音節 {syl} {pos}: {cands}")
                ens = " | ".join(f"{h}={e}" for h, c, e in p_results if e)
                if ens:
                    lines.append(f"    en: {ens}")
            if s_results:
                cands = " ".join(f"{h}(x{c})" for h, c, _ in s_results)
                lines.append(f"  {sec_label}音節 {syl} {pos}: {cands}")

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

    is_teochew = system in TEOCHEW_SYSTEMS
    if is_teochew:
        primary_rows = load_csv(TEOCHEW_CSV)
        secondary_rows = load_csv(HOKKIEN_CSV)
    else:
        primary_rows = load_csv(HOKKIEN_CSV)
        secondary_rows = load_csv(TEOCHEW_CSV)

    output = format_results(words, system, primary_rows, secondary_rows)
    print(output)


if __name__ == "__main__":
    main()
