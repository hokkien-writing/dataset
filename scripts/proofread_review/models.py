from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


SCHEMA_VERSION = "proofread-review-decisions/v1"
PDF_PAGE_OFFSET = 0
COMPATIBLE_DATA_VERSIONS = (
    "f1df90a4a641d94d184f42b0cf21bb068c7d15e5b772e922673100dc167ce2e1",
)
VALID_ISSUES = {
    "cross_type",
    "empty_key",
    "existing_key_conflict",
    "truncated_gloss",
    "rule_review",
}
VALID_STATUSES = {"accepted", "deferred", "rejected"}
VALID_DISPOSITIONS = {
    "normal_match",
    "mismatch",
    "left_only",
    "source_007_only",
    "separate_actions",
    "split_entries",
    "rematch",
}


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _identity_value(value: dict[str, object]) -> dict[str, object]:
    result = dict(value)
    issues = result.get("issues")
    if isinstance(issues, list):
        result["issues"] = sorted(issues)
    return result


def stable_record_id(value: dict[str, object]) -> str:
    return f"review-{_digest(_identity_value(value))[:20]}"


@dataclass(frozen=True)
class ReviewRecord:
    id: str
    row: int
    page: int
    pdf_page: int
    issues: tuple[str, ...]
    table_key: tuple[str, str, str]
    current: dict[str, str]
    proposal: dict[str, str]
    context: dict[str, str]
    source_digest: str

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> ReviewRecord:
        row = value.get("row")
        page = value.get("page")
        issues = value.get("issues")
        table_key = value.get("table_key")
        current = value.get("current")
        proposal = value.get("proposal")
        context = value.get("context")
        if not isinstance(row, int) or row < 0:
            raise ValueError("row must be a non-negative integer")
        if not isinstance(page, int) or page < 1:
            raise ValueError("page must be a positive integer")
        if not isinstance(issues, list) or not issues:
            raise ValueError("issues must be a non-empty list")
        if any(issue not in VALID_ISSUES for issue in issues):
            raise ValueError(f"unknown issue: {issues}")
        if not isinstance(table_key, list) or len(table_key) != 3:
            raise ValueError("table_key must contain reading, gloss, and page")
        mappings = {"current": current, "proposal": proposal, "context": context}
        if any(
            not isinstance(mapping, dict)
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items())
            for mapping in mappings.values()
        ):
            raise ValueError("current, proposal, and context must map strings to strings")
        source = {
            "row": row,
            "page": page,
            "issues": sorted(set(issues)),
            "table_key": [str(item) for item in table_key],
            "current": current,
            "proposal": proposal,
            "context": context,
        }
        return cls(
            id=stable_record_id(source),
            row=row,
            page=page,
            pdf_page=page + PDF_PAGE_OFFSET,
            issues=tuple(sorted(set(issues))),
            table_key=tuple(str(item) for item in table_key),
            current=dict(current),
            proposal=dict(proposal),
            context=dict(context),
            source_digest=_digest(source),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "row": self.row,
            "page": self.page,
            "pdf_page": self.pdf_page,
            "issues": list(self.issues),
            "table_key": list(self.table_key),
            "current": self.current,
            "proposal": self.proposal,
            "context": self.context,
            "source_digest": self.source_digest,
        }


@dataclass(frozen=True)
class ReviewDataset:
    records: tuple[ReviewRecord, ...]
    data_version: str
    issue_counts: dict[str, int]

    @classmethod
    def from_records(cls, records: list[ReviewRecord]) -> ReviewDataset:
        ids = [record.id for record in records]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate stable id")
        ordered = tuple(sorted(records, key=lambda record: (record.page, record.row, record.id)))
        counts = {issue: 0 for issue in sorted(VALID_ISSUES)}
        for record in ordered:
            for issue in record.issues:
                counts[issue] += 1
        version = _digest([record.to_dict() for record in ordered])
        return cls(records=ordered, data_version=version, issue_counts=counts)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "proofread-review-data/v1",
            "data_version": self.data_version,
            "compatible_data_versions": list(COMPATIBLE_DATA_VERSIONS),
            "record_count": len(self.records),
            "issue_count": sum(self.issue_counts.values()),
            "issue_counts": self.issue_counts,
            "records": [record.to_dict() for record in self.records],
        }


def validate_decision_export(
    dataset: ReviewDataset, payload: dict[str, Any]
) -> list[dict[str, Any]]:
    if payload.get("schema") != SCHEMA_VERSION:
        raise ValueError("unsupported decision schema")
    if payload.get("data_version") not in {dataset.data_version, *COMPATIBLE_DATA_VERSIONS}:
        raise ValueError("stale data version")
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("decisions must be a list")
    records = {record.id: record for record in dataset.records}
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("decision must be an object")
        record_id = decision.get("id")
        if not isinstance(record_id, str) or record_id not in records:
            raise ValueError("unknown decision id")
        if record_id in seen:
            raise ValueError("duplicate decision id")
        seen.add(record_id)
        if decision.get("source_digest") != records[record_id].source_digest:
            raise ValueError("stale source digest")
        if decision.get("status") not in VALID_STATUSES:
            raise ValueError("invalid decision status")
        final = decision.get("final")
        if not isinstance(final, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in final.items()
        ):
            raise ValueError("final values must map strings to strings")
        if not isinstance(decision.get("note", ""), str):
            raise ValueError("note must be a string")
        disposition = decision.get("disposition", "normal_match")
        if disposition not in VALID_DISPOSITIONS:
            raise ValueError("invalid match disposition")
        legacy_treatment = {
            key: decision.get(key, "")
            for key in ("left_action", "source_007_action", "rematch_target")
        }
        if any(not isinstance(value, str) for value in legacy_treatment.values()):
            raise ValueError("treatment instructions must be strings")
        note = decision.get("note", "")
        legacy_lines = [
            f"{label}：{legacy_treatment[key].strip()}"
            for key, label in (
                ("left_action", "左側 CSV"),
                ("source_007_action", "007"),
                ("rematch_target", "改配目標"),
            )
            if legacy_treatment[key].strip()
        ]
        if legacy_lines:
            note = "\n".join(part for part in (note.strip(), *legacy_lines) if part)
        if (
            decision["status"] == "accepted"
            and disposition not in {"normal_match", "mismatch"}
            and not note.strip()
        ):
            raise ValueError("non-normal match requires a semantic note")
        result = {**decision, "disposition": disposition, "note": note}
        for key in legacy_treatment:
            result.pop(key, None)
        normalized.append(result)
    return normalized
