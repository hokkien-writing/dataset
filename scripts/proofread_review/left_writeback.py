from __future__ import annotations

import argparse
import csv
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path

from scripts.proofread_review.models import ReviewDataset, ReviewRecord, validate_decision_export


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SOURCE = PROJECT_ROOT / "books/部分校对/合併_斐姑娘詞典_proofread.csv"
DEFAULT_TARGET = PROJECT_ROOT / "books/（合併校對&修正讀音）斐姑娘詞典.csv"
DEFAULT_DATA = Path(__file__).resolve().parent / "review_data.json"
DEFAULT_DECISIONS = PROJECT_ROOT / "tmp/007-proofread-decisions.json"
DEFAULT_PLAN = PROJECT_ROOT / "tmp/007-left-writeback-plan.json"
KEY_FIELDS = ("字目", "词条", "读音", "释义", "字段1", "字段2", "页码")
PROOFREAD_FIELDS = {
    "字目": ("Proofread_字目",),
    "词条": ("Proofread_词条",),
    "读音": ("Proofread_读音",),
    "释义": ("Proofread_释义", "Proofread_释义_2"),
    "页码": ("Proofread_页码",),
}
LEFT_REVIEW_OVERRIDES = {
    "review-a3bff6d5f117f5131c98": {"词条": "邋杂"},
}


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(_normalize(row.get(field, "")) for field in KEY_FIELDS)


def _first_value(row: dict[str, str], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = row.get(field, "")
        if value:
            return value
    return ""


def _left_reading(final: str, proofread: str) -> str:
    if proofread.rstrip().endswith(";") and not final.rstrip().endswith(";"):
        return f"{final.rstrip()} ;"
    return final


def compile_left_plan(
    source_rows: list[dict[str, str]],
    target_rows: list[dict[str, str]],
    review_data: dict[str, object],
    decision_payload: dict[str, object],
) -> dict[str, object]:
    dataset = ReviewDataset.from_records(
        [ReviewRecord.from_dict(row) for row in review_data["records"]]
    )
    decisions = validate_decision_export(dataset, decision_payload)
    records = {record["id"]: record for record in review_data["records"]}
    decisions_by_row = {records[item["id"]]["row"]: item for item in decisions}
    target_by_key: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for index, row in enumerate(target_rows):
        target_by_key[_key(row)].append(index)

    changes: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    matched_targets: set[int] = set()
    for source_index, source in enumerate(source_rows):
        values = {
            field: _first_value(source, proofread_fields)
            for field, proofread_fields in PROOFREAD_FIELDS.items()
        }
        if not any(values.values()):
            continue
        hits = target_by_key.get(_key(source), [])
        if len(hits) != 1:
            raise ValueError(f"source row {source_index} matched {len(hits)} target rows")
        target_index = hits[0]
        if target_index in matched_targets:
            raise ValueError(f"target row {target_index} matched more than once")
        matched_targets.add(target_index)
        decision = decisions_by_row.get(source_index)
        if decision is not None and decision["disposition"] != "normal_match":
            skipped.append(
                {
                    "source_row": source_index,
                    "target_row": target_index,
                    "decision_id": decision["id"],
                    "disposition": decision["disposition"],
                    "note": decision.get("note", ""),
                }
            )
            continue
        if decision is not None:
            final = decision["final"]
            if values["读音"]:
                values["读音"] = _left_reading(final.get("reading", ""), values["读音"])
            if values["释义"]:
                values["释义"] = final.get("gloss", "")
            override = LEFT_REVIEW_OVERRIDES.get(decision["id"], {})
            for field, value in override.items():
                if field == "页码_delta":
                    values["页码"] = str(int(source["页码"]) + int(value))
                else:
                    values[field] = str(value)
        row_changes = {
            field: {"old": target_rows[target_index].get(field, ""), "new": value}
            for field, value in values.items()
            if value and value != target_rows[target_index].get(field, "")
        }
        if row_changes:
            changes.append(
                {
                    "source_row": source_index,
                    "target_row": target_index,
                    "decision_id": decision["id"] if decision else "",
                    "fields": row_changes,
                }
            )
    return {
        "schema": "007-left-writeback-plan/v1",
        "proofread_rows": len(matched_targets),
        "change_rows": len(changes),
        "skipped": skipped,
        "changes": changes,
    }


def apply_left_plan(rows: list[dict[str, str]], plan: dict[str, object]) -> None:
    for change in plan["changes"]:
        row = rows[change["target_row"]]
        for field, values in change["fields"].items():
            if row.get(field, "") != values["old"]:
                raise ValueError(f"target row {change['target_row']} field {field} changed after planning")
            row[field] = values["new"]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def _atomic_write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    _, source_rows = _read_csv(args.source)
    fieldnames, target_rows = _read_csv(args.target)
    if tuple(fieldnames) != KEY_FIELDS:
        raise ValueError(f"unexpected target columns: {fieldnames}")
    plan = compile_left_plan(
        source_rows,
        target_rows,
        json.loads(args.data.read_text(encoding="utf-8")),
        json.loads(args.decisions.read_text(encoding="utf-8")),
    )
    args.plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.apply:
        apply_left_plan(target_rows, plan)
        _atomic_write_csv(args.target, fieldnames, target_rows)
    print(
        f"proofread_rows={plan['proofread_rows']} change_rows={plan['change_rows']} "
        f"skipped={len(plan['skipped'])}"
    )


if __name__ == "__main__":
    main()
