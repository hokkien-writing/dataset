from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from scripts.proofread_review.models import ReviewDataset, ReviewRecord, validate_decision_export


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ACTIONS = Path(__file__).resolve().parent / "review_actions_source.json"
DEFAULT_DATA = Path(__file__).resolve().parent / "review_data.json"
DEFAULT_DECISIONS = PROJECT_ROOT / "tmp/007-proofread-decisions.json"
DEFAULT_TARGET = (
    PROJECT_ROOT
    / "scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.py"
)
DEFAULT_PLAN = PROJECT_ROOT / "tmp/007-proofread-writeback-plan.json"
CONTEXT_REQUIRED_KEYS = {("ūi", "", "635")}


def _literal(value: object) -> str:
    return repr(value)


def _table_body(
    values: dict[tuple[str, ...], tuple[str | None, str | None]],
) -> str:
    if not values:
        return "{}"
    lines = ["{"]
    for key, replacement in sorted(values.items()):
        lines.append(f"    {_literal(key)}: {_literal(replacement)},")
    lines.append("}")
    return "\n".join(lines)


def compile_plan(
    actions_path: Path,
    data_path: Path,
    decisions_path: Path,
) -> dict[str, object]:
    actions = json.loads(actions_path.read_text(encoding="utf-8"))
    data = json.loads(data_path.read_text(encoding="utf-8"))
    payload = json.loads(decisions_path.read_text(encoding="utf-8"))
    dataset = ReviewDataset.from_records([ReviewRecord.from_dict(row) for row in data["records"]])
    decisions = validate_decision_export(dataset, payload)
    records = {record["id"]: record for record in data["records"]}
    decisions_by_row = {
        records[decision["id"]]["row"]: decision for decision in decisions
    }
    records_by_row = {record["row"]: record for record in data["records"]}
    actions_by_row: dict[int, list[dict[str, object]]] = defaultdict(list)
    for action in actions:
        if action.get("type") in {"t7_reading", "t7_gloss"}:
            actions_by_row[action["row"]].append(action)

    corrections: dict[tuple[str, str, str], tuple[str | None, str | None]] = {}
    contextual: dict[tuple[str, str, str, str], tuple[str | None, str | None]] = {}
    skipped: list[dict[str, object]] = []
    collisions: list[dict[str, object]] = []
    candidates: list[tuple[int, tuple[str, str, str], tuple[str | None, str | None]]] = []
    for row, row_actions in actions_by_row.items():
        key = tuple(str(part) for part in row_actions[0]["tbl_key"])
        if any(tuple(str(part) for part in action["tbl_key"]) != key for action in row_actions):
            raise ValueError(f"row {row} has inconsistent table keys")
        decision = decisions_by_row.get(row)
        record = records_by_row.get(row)
        if decision is not None:
            if decision["disposition"] != "normal_match":
                skipped.append({
                    "row": row,
                    "key": list(key),
                    "disposition": decision["disposition"],
                    "note": decision.get("note", ""),
                })
                continue
            current = record["current"]
            final = decision["final"]
            if final.get("reading", "") == current.get("reading", "") and final.get("gloss", "") == current.get("gloss", ""):
                continue
            replacement = (final.get("reading", ""), final.get("gloss", ""))
        else:
            reading = next((str(action["replacement"]) for action in row_actions if action["type"] == "t7_reading"), None)
            gloss = next((str(action["replacement"]) for action in row_actions if action["type"] == "t7_gloss"), None)
            replacement = (reading, gloss)
        candidates.append((row, key, replacement))

    grouped: dict[tuple[str, str, str], list[tuple[int, tuple[str | None, str | None]]]] = defaultdict(list)
    for row, key, replacement in candidates:
        grouped[key].append((row, replacement))
    for key, items in grouped.items():
        if len(items) == 1 and key not in CONTEXT_REQUIRED_KEYS:
            corrections[key] = items[0][1]
            continue
        for row, replacement in items:
            record = records_by_row.get(row)
            headword = (record or {}).get("context", {}).get("term") or (record or {}).get("context", {}).get("headword")
            if not headword:
                collisions.append({"key": list(key), "row": row})
                continue
            contextual[(str(headword), *key)] = replacement
    if collisions:
        raise ValueError(f"unresolved correction collisions: {collisions}")
    return {
        "schema": "007-proofread-writeback-plan/v1",
        "decision_count": len(decisions),
        "generic_count": len(corrections),
        "contextual_count": len(contextual),
        "skipped": skipped,
        "corrections": [[list(key), list(value)] for key, value in sorted(corrections.items())],
        "contextual": [[list(key), list(value)] for key, value in sorted(contextual.items())],
    }


def apply_plan(target: Path, plan: dict[str, object]) -> None:
    generic = {tuple(key): tuple(value) for key, value in plan["corrections"]}
    contextual = {tuple(key): tuple(value) for key, value in plan["contextual"]}
    text = target.read_text(encoding="utf-8")
    generic_pattern = re.compile(
        r"(_BOOK_REVIEW_CORRECTIONS: dict\[\n    tuple\[str, str, str\], tuple\[str \| None, str \| None\]\n\] = )\{.*?\}(\n\n_BOOK_HEADWORD_REVIEW_CORRECTIONS:)",
        re.DOTALL,
    )
    contextual_pattern = re.compile(
        r"(_BOOK_HEADWORD_REVIEW_CORRECTIONS: dict\[\n    tuple\[str, str, str, str\], tuple\[str \| None, str \| None\]\n\] = )\{.*?\}(\n\n\n_BOOK_CORRECTION_PRE_KEYS:)",
        re.DOTALL,
    )
    text, generic_count = generic_pattern.subn(
        lambda match: f"{match.group(1)}{_table_body(generic)}{match.group(2)}", text
    )
    text, contextual_count = contextual_pattern.subn(
        lambda match: f"{match.group(1)}{_table_body(contextual)}{match.group(2)}", text
    )
    if generic_count != 1 or contextual_count != 1:
        raise ValueError("review correction table anchors not found exactly once")
    target.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actions", type=Path, default=DEFAULT_ACTIONS)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--apply-007", action="store_true")
    args = parser.parse_args()
    plan = compile_plan(args.actions, args.data, args.decisions)
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    args.plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.apply_007:
        apply_plan(args.target, plan)
    print(
        f"decisions={plan['decision_count']} generic={plan['generic_count']} "
        f"contextual={plan['contextual_count']} skipped={len(plan['skipped'])}"
    )


if __name__ == "__main__":
    main()
