"""One-time exporter of the 007 correction constants into the authoritative CSV.

Run:
    PYTHONPATH=. .venv/bin/python scripts/migrations/export_007_corrections.py
"""

from __future__ import annotations

import csv
import importlib
from pathlib import Path

from scripts.wikisource.corrections import CSV_HEADER, rule_id_for

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MOD = importlib.import_module(
    "scripts.wikisource.007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect"
)
OUTPUT = (
    PROJECT_ROOT
    / "books/corrections/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv"
)


def _rules() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    tables = (
        ("reading", MOD._BOOK_READING_CORRECTIONS),
        ("gloss", MOD._BOOK_GLOSS_CORRECTIONS),
        ("example_split", MOD._BOOK_EXAMPLE_SPLITS),
        ("review", MOD._BOOK_REVIEW_CORRECTIONS),
        ("headword_review", MOD._BOOK_HEADWORD_REVIEW_CORRECTIONS),
    )
    for rule_type, table in tables:
        for key, value in table.items():
            if rule_type == "headword_review":
                headword, reading, gloss, page = key
            else:
                headword, reading, gloss, page = "", *key
            if rule_type == "example_split":
                items: list[tuple[str, str]] = list(value)
            elif rule_type in {"review", "headword_review"}:
                reading_replacement, gloss_replacement = value
                items = [(reading_replacement or "", gloss_replacement or "")]
            elif rule_type == "gloss":
                items = [("", value)]
            else:
                items = [(value, "")]
            rule_id = rule_id_for(rule_type, headword, (reading, gloss, page))
            for index, (replacement_reading, replacement_gloss) in enumerate(items, start=1):
                rows.append(
                    {
                        "rule_id": rule_id,
                        "rule_type": rule_type,
                        "headword": headword,
                        "key_reading": reading,
                        "key_gloss": gloss,
                        "page": str(int(page)),
                        "output_index": str(index),
                        "replacement_reading": replacement_reading,
                        "replacement_gloss": replacement_gloss,
                        "enabled": "true",
                        "review_status": "pending",
                        "note": "",
                    }
                )
    rows.sort(
        key=lambda row: (
            int(row["page"]),
            row["rule_type"],
            row["headword"],
            row["key_reading"],
            row["key_gloss"],
            row["output_index"],
        )
    )
    return rows


def main() -> None:
    rows = _rules()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADER.split(","), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[str, int] = {}
    seen_ids: set[str] = set()
    for row in rows:
        if row["rule_id"] not in seen_ids:
            seen_ids.add(row["rule_id"])
            counts[row["rule_type"]] = counts.get(row["rule_type"], 0) + 1
    print(
        f"reading={counts.get('reading', 0)} gloss={counts.get('gloss', 0)} "
        f"example_split={counts.get('example_split', 0)} review={counts.get('review', 0)} "
        f"headword_review={counts.get('headword_review', 0)} total={len(seen_ids)}"
    )


if __name__ == "__main__":
    main()
