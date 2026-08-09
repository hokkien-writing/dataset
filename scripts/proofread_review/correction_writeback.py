from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from scripts.proofread_review.models import ReviewDataset, ReviewRecord, validate_decision_export
from scripts.wikisource.corrections import CSV_HEADER, catalog_digest, load_correction_catalog

PLAN_SCHEMA = "007-correction-csv-writeback-plan/v1"


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if list(reader.fieldnames or []) != CSV_HEADER.split(","):
            raise ValueError(f"unexpected CSV header: {reader.fieldnames}")
        return list(reader)


def _ordinary_accepted_row(
    old_row: dict[str, str],
    current: dict[str, str],
    final: dict[str, str],
) -> dict[str, str]:
    row = dict(old_row)
    for field, csv_field in (
        ("reading", "replacement_reading"),
        ("gloss", "replacement_gloss"),
    ):
        final_value = final.get(field, "")
        if final_value != current.get(field, "") or row[csv_field] != "":
            row[csv_field] = final_value
    return row


def _split_accepted_rows(
    old_rows: list[dict[str, str]], final: dict[str, str]
) -> list[dict[str, str]]:
    readings = [line for line in final.get("reading", "").split("\n") if line]
    glosses = [line for line in final.get("gloss", "").split("\n") if line]
    if len(readings) != len(glosses):
        raise ValueError("split final reading and gloss line counts differ")
    if len(readings) < 2:
        raise ValueError("example_split requires at least two rows")
    new_rows: list[dict[str, str]] = []
    for index, (reading, gloss) in enumerate(zip(readings, glosses), start=1):
        template = old_rows[index - 1] if index - 1 < len(old_rows) else old_rows[0]
        row = dict(template)
        row["output_index"] = str(index)
        row["replacement_reading"] = reading
        row["replacement_gloss"] = gloss
        new_rows.append(row)
    return new_rows


def compile_correction_plan(
    catalog_path: Path,
    data_path: Path,
    decisions_path: Path,
) -> dict[str, object]:
    rows = _read_rows(catalog_path)
    catalog = load_correction_catalog(catalog_path)
    digest = catalog_digest(catalog)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    dataset = ReviewDataset.from_records(
        [ReviewRecord.from_dict(row) for row in data["records"]]
    )
    payload = json.loads(decisions_path.read_text(encoding="utf-8"))
    decisions = validate_decision_export(dataset, payload)
    records = {record.id: record for record in dataset.records}
    rows_by_rule: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        rows_by_rule.setdefault(row["rule_id"], []).append(row)
    changes: list[dict[str, object]] = []
    unchanged: list[str] = []
    deferred: list[str] = []
    for decision in decisions:
        record = records[decision["id"]]
        rule_id = record.context.get("rule_id", "")
        if not rule_id:
            raise ValueError(f"record {record.id} has no rule_id")
        if record.context.get("catalog_digest") != digest:
            raise ValueError(f"stale catalog digest for rule {rule_id}")
        old_rows = rows_by_rule.get(rule_id)
        if old_rows is None:
            raise ValueError(f"rule {rule_id} not found in catalog")
        status = decision["status"]
        if status == "deferred":
            deferred.append(rule_id)
            continue
        final = decision["final"]
        if status == "accepted" and final == record.current:
            keep_current = True
        elif status == "accepted":
            keep_current = False
        else:
            keep_current = True
        if keep_current:
            new_rows = [dict(row) for row in old_rows]
        elif old_rows[0]["rule_type"] == "example_split":
            new_rows = _split_accepted_rows(old_rows, final)
        else:
            new_rows = [_ordinary_accepted_row(old_rows[0], record.current, final)]
        enabled = "false" if keep_current else "true"
        review_status = "rejected" if keep_current else "accepted"
        note = decision.get("note", "")
        for row in new_rows:
            row["enabled"] = enabled
            row["review_status"] = review_status
            row["note"] = note
        if new_rows == old_rows:
            unchanged.append(rule_id)
            continue
        changes.append(
            {
                "rule_id": rule_id,
                "old_rows": old_rows,
                "new_rows": new_rows,
                "decision_id": decision["id"],
            }
        )
    return {
        "schema": PLAN_SCHEMA,
        "catalog_digest": digest,
        "changes": changes,
        "unchanged": unchanged,
        "deferred": deferred,
    }


def apply_correction_plan(catalog_path: Path, plan: dict[str, object]) -> None:
    if plan.get("schema") != PLAN_SCHEMA:
        raise ValueError("unsupported write-back plan schema")
    rows = _read_rows(catalog_path)
    catalog = load_correction_catalog(catalog_path)
    if catalog_digest(catalog) != plan.get("catalog_digest"):
        raise ValueError("stale catalog digest")
    changes = plan.get("changes")
    if not isinstance(changes, list):
        raise ValueError("changes must be a list")
    replacement: dict[str, list[dict[str, str]]] = {}
    rows_by_rule: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        rows_by_rule.setdefault(row["rule_id"], []).append(row)
    for change in changes:
        if not isinstance(change, dict):
            raise ValueError("change must be an object")
        rule_id = change.get("rule_id")
        old_rows = change.get("old_rows")
        new_rows = change.get("new_rows")
        if not isinstance(rule_id, str) or not isinstance(old_rows, list) or not isinstance(new_rows, list):
            raise ValueError(f"malformed change: {rule_id}")
        if any(not isinstance(row, dict) for row in old_rows + new_rows):
            raise ValueError(f"rows must be objects: {rule_id}")
        current_rows = rows_by_rule.get(rule_id)
        if current_rows is None:
            raise ValueError(f"rule {rule_id} not found in CSV")
        if old_rows != current_rows:
            raise ValueError(f"rule {rule_id} old rows do not match CSV")
        if not new_rows:
            raise ValueError(f"rule {rule_id} has no new rows")
        replacement[rule_id] = new_rows
    output: list[dict[str, str]] = []
    emitted: set[str] = set()
    for row in rows:
        rule_id = row["rule_id"]
        if rule_id in replacement:
            if rule_id not in emitted:
                output.extend(replacement[rule_id])
                emitted.add(rule_id)
        else:
            output.append(row)
    _atomic_replace_after_validation(catalog_path, output)


def _atomic_replace_after_validation(path: Path, rows: list[dict[str, str]]) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(
                file, fieldnames=CSV_HEADER.split(","), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        load_correction_catalog(Path(temporary))
        os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plan = compile_correction_plan(args.corrections, args.data, args.decisions)
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    args.plan.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.apply:
        apply_correction_plan(args.corrections, plan)
    print(
        f"schema={plan['schema']} changes={len(plan['changes'])} "
        f"unchanged={len(plan['unchanged'])} deferred={len(plan['deferred'])}"
    )


if __name__ == "__main__":
    main()
