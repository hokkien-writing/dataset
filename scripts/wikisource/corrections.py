from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

CSV_HEADER = (
    "rule_id,rule_type,headword,key_reading,key_gloss,page,output_index,"
    "replacement_reading,replacement_gloss,enabled,review_status,note"
)
ALLOWED_RULE_TYPES = {"reading", "gloss", "example_split", "review", "headword_review"}
ALLOWED_REVIEW_STATUSES = {"pending", "accepted", "rejected", "deferred"}
_SPLIT_TYPES = {"example_split"}
_ORDINARY_TYPES = {"reading", "gloss", "review", "headword_review"}


def rule_id_for(rule_type: str, headword: str, key: tuple[str, str, str]) -> str:
    digest = hashlib.sha256(
        json.dumps(
            [rule_type, headword, list(key)],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"007-{rule_type}-{digest[:16]}"


@dataclass(frozen=True)
class CorrectionRule:
    rule_id: str
    rule_type: str
    headword: str
    key: tuple[str, str, str]
    output_index: int
    replacement_reading: str
    replacement_gloss: str
    enabled: bool
    review_status: str
    note: str


@dataclass(frozen=True)
class CorrectionCatalog:
    rules: tuple[CorrectionRule, ...]
    reading: dict[tuple[str, str, str], str]
    gloss: dict[tuple[str, str, str], str]
    example_splits: dict[tuple[str, str, str], list[tuple[str, str]]]
    review: dict[tuple[str, str, str], tuple[str | None, str | None]]
    headword_review: dict[tuple[str, str, str, str], tuple[str | None, str | None]]


def catalog_digest(catalog: CorrectionCatalog) -> str:
    ordered = sorted(catalog.rules, key=lambda rule: (rule.rule_id, rule.output_index))
    payload = [
        {
            "rule_id": rule.rule_id,
            "rule_type": rule.rule_type,
            "headword": rule.headword,
            "key": list(rule.key),
            "output_index": rule.output_index,
            "replacement_reading": rule.replacement_reading,
            "replacement_gloss": rule.replacement_gloss,
            "enabled": rule.enabled,
            "review_status": rule.review_status,
            "note": rule.note,
        }
        for rule in ordered
    ]
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"invalid enabled value: {value!r}")


def _parse_rule(row: dict[str, str]) -> CorrectionRule:
    rule_type = row["rule_type"]
    if rule_type not in ALLOWED_RULE_TYPES:
        raise ValueError(f"unknown rule_type: {rule_type!r}")
    status = row["review_status"]
    if status not in ALLOWED_REVIEW_STATUSES:
        raise ValueError(f"unknown review_status: {status!r}")
    enabled = _parse_bool(row["enabled"])
    page_text = row["page"]
    if not page_text.isdigit() or int(page_text) < 1:
        raise ValueError(f"non-positive page: {page_text!r}")
    try:
        output_index = int(row["output_index"])
    except ValueError:
        raise ValueError(f"invalid output_index: {row['output_index']!r}")
    if output_index < 1:
        raise ValueError(f"output_index must be positive: {row['rule_id']}")
    headword = row["headword"]
    key = (row["key_reading"], row["key_gloss"], page_text)
    replacement_reading = row["replacement_reading"]
    replacement_gloss = row["replacement_gloss"]
    if rule_type == "headword_review" and not headword:
        raise ValueError(f"headword_review requires headword: {row['rule_id']}")
    if rule_type != "headword_review" and headword:
        raise ValueError(f"headword must be empty for {rule_type}: {row['rule_id']}")
    if rule_type == "reading":
        if not replacement_reading:
            raise ValueError(f"reading requires replacement_reading: {row['rule_id']}")
        if replacement_gloss:
            raise ValueError(f"reading forbids replacement_gloss: {row['rule_id']}")
    elif rule_type == "gloss":
        if not replacement_gloss:
            raise ValueError(f"gloss requires replacement_gloss: {row['rule_id']}")
        if replacement_reading:
            raise ValueError(f"gloss forbids replacement_reading: {row['rule_id']}")
    elif rule_type in _ORDINARY_TYPES:
        if not replacement_reading and not replacement_gloss:
            raise ValueError(f"{rule_type} requires a replacement: {row['rule_id']}")
    if rule_type in _ORDINARY_TYPES and output_index != 1:
        raise ValueError(f"{rule_type} requires output_index=1: {row['rule_id']}")
    if rule_type == "example_split" and (not replacement_reading or not replacement_gloss):
        raise ValueError(f"example_split requires both replacements: {row['rule_id']}")
    return CorrectionRule(
        rule_id=row["rule_id"],
        rule_type=rule_type,
        headword=headword,
        key=key,
        output_index=output_index,
        replacement_reading=replacement_reading,
        replacement_gloss=replacement_gloss,
        enabled=enabled,
        review_status=status,
        note=row["note"],
    )


def _validate_groups(rules: list[CorrectionRule]) -> None:
    groups: dict[str, list[CorrectionRule]] = {}
    for rule in rules:
        groups.setdefault(rule.rule_id, []).append(rule)
    seen_keys: dict[str, set[tuple[str, str, str, str]]] = {}
    for rule_id, group in groups.items():
        group_type = group[0].rule_type
        if any(rule.rule_type != group_type for rule in group):
            raise ValueError(f"mixed rule types in group: {rule_id}")
        shared = [(rule.enabled, rule.review_status, rule.headword, rule.key) for rule in group]
        if any(item != shared[0] for item in shared[1:]):
            raise ValueError(f"conflicting enabled/status/headword/key rows: {rule_id}")
        if group_type == "example_split":
            if len(group) < 2:
                raise ValueError(f"example_split group must have at least two rows: {rule_id}")
            indexes = [rule.output_index for rule in sorted(group, key=lambda r: r.output_index)]
            if indexes != list(range(1, len(indexes) + 1)):
                raise ValueError(f"example_split output_index must be consecutive from 1: {rule_id}")
        rule = group[0]
        key = (rule.headword, rule.key[0], rule.key[1], rule.key[2])
        seen = seen_keys.setdefault(rule.rule_type, set())
        if key in seen:
            raise ValueError(f"duplicate logical key within {rule.rule_type}: {key}")
        seen.add(key)


def _active(rules: list[CorrectionRule]) -> list[CorrectionRule]:
    return [rule for rule in rules if rule.enabled]


def _index_reading(rules: list[CorrectionRule]) -> dict[tuple[str, str, str], str]:
    return {
        rule.key: rule.replacement_reading
        for rule in _active(rules)
        if rule.rule_type == "reading"
    }


def _index_gloss(rules: list[CorrectionRule]) -> dict[tuple[str, str, str], str]:
    return {
        rule.key: rule.replacement_gloss
        for rule in _active(rules)
        if rule.rule_type == "gloss"
    }


def _index_splits(
    rules: list[CorrectionRule],
) -> dict[tuple[str, str, str], list[tuple[str, str]]]:
    splits: dict[tuple[str, str, str], list[tuple[str, str]]] = {}
    for rule in sorted(_active(rules), key=lambda rule: rule.output_index):
        if rule.rule_type == "example_split":
            splits.setdefault(rule.key, []).append(
                (rule.replacement_reading, rule.replacement_gloss)
            )
    return splits


def _index_review(
    rules: list[CorrectionRule],
) -> dict[tuple[str, str, str], tuple[str | None, str | None]]:
    return {
        rule.key: (rule.replacement_reading or None, rule.replacement_gloss or None)
        for rule in _active(rules)
        if rule.rule_type == "review"
    }


def _index_headword_review(
    rules: list[CorrectionRule],
) -> dict[tuple[str, str, str, str], tuple[str | None, str | None]]:
    return {
        (rule.headword, *rule.key): (
            rule.replacement_reading or None,
            rule.replacement_gloss or None,
        )
        for rule in _active(rules)
        if rule.rule_type == "headword_review"
    }


def load_correction_catalog(path: Path) -> CorrectionCatalog:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if list(reader.fieldnames or []) != CSV_HEADER.split(","):
            raise ValueError(f"unexpected CSV header: {reader.fieldnames}")
        rows = list(reader)
    rules: list[CorrectionRule] = []
    seen_rule_index: set[tuple[str, int]] = set()
    for row in rows:
        rule = _parse_rule(row)
        index = (rule.rule_id, rule.output_index)
        if index in seen_rule_index:
            raise ValueError(f"duplicate rule_id/output_index: {index}")
        seen_rule_index.add(index)
        rules.append(rule)
    _validate_groups(rules)
    return CorrectionCatalog(
        rules=tuple(rules),
        reading=_index_reading(rules),
        gloss=_index_gloss(rules),
        example_splits=_index_splits(rules),
        review=_index_review(rules),
        headword_review=_index_headword_review(rules),
    )
