from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.proofread_review.correction_review import (
    build_correction_review_dataset,
    build_source_entries,
)
from scripts.proofread_review.models import ReviewDataset, ReviewRecord
from scripts.wikisource.corrections import (
    CSV_HEADER,
    catalog_digest,
    load_correction_catalog,
    rule_id_for,
)

SOURCE = (
    "<!-- page:1 -->\n"
    "- **字** raw — gloss\n"
    "  - *ex1* — example one\n"
)


def _correction_row(rule_id: str, rule_type: str = "reading", **changes: str) -> dict[str, str]:
    row: dict[str, str] = {
        "rule_id": rule_id,
        "rule_type": rule_type,
        "headword": "",
        "key_reading": "raw",
        "key_gloss": "gloss",
        "page": "1",
        "output_index": "1",
        "replacement_reading": "fixed",
        "replacement_gloss": "",
        "enabled": "true",
        "review_status": "pending",
        "note": "",
    }
    row.update(changes)
    return row


def _write_correction_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADER.split(","), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_correction_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _decision(
    dataset: ReviewDataset,
    index: int = 0,
    status: str = "accepted",
    final: dict[str, str] | None = None,
    note: str = "",
) -> dict[str, object]:
    record = dataset.records[index]
    return {
        "id": record.id,
        "source_digest": record.source_digest,
        "status": status,
        "final": dict(record.proposal) if final is None else final,
        "note": note,
    }


class TestCorrectionWriteback(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.catalog_path = Path(self.temp_dir.name) / "fixture.csv"
        self.data_path = Path(self.temp_dir.name) / "data.json"
        self.decisions_path = Path(self.temp_dir.name) / "decisions.json"

    def _dataset(self, rows: list[dict[str, str]]) -> ReviewDataset:
        _write_correction_csv(self.catalog_path, rows)
        entries = build_source_entries(SOURCE)
        dataset = build_correction_review_dataset(
            load_correction_catalog(self.catalog_path), entries
        )
        self.data_path.write_text(
            json.dumps(dataset.to_dict(), ensure_ascii=False), encoding="utf-8"
        )
        return dataset

    def _decisions_file(self, dataset: ReviewDataset, decisions: list[dict[str, object]]) -> Path:
        payload = {
            "schema": "proofread-review-decisions/v1",
            "data_version": dataset.data_version,
            "decisions": decisions,
        }
        self.decisions_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        return self.decisions_path

    def _compile(self, dataset: ReviewDataset, decisions: list[dict[str, object]]) -> dict[str, object]:
        from scripts.proofread_review.correction_writeback import compile_correction_plan

        return compile_correction_plan(
            self.catalog_path,
            self.data_path,
            self._decisions_file(dataset, decisions),
        )

    def test_plan_schema_and_digest(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        plan = self._compile(dataset, [_decision(dataset)])
        self.assertEqual(plan["schema"], "007-correction-csv-writeback-plan/v1")
        self.assertEqual(
            plan["catalog_digest"], catalog_digest(load_correction_catalog(self.catalog_path))
        )

    def test_accepted_proposal_enables_and_accepts(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        plan = self._compile(dataset, [_decision(dataset)])
        [change] = plan["changes"]
        [old_row] = change["old_rows"]
        [new_row] = change["new_rows"]
        self.assertEqual(old_row["enabled"], "true")
        self.assertEqual(old_row["review_status"], "pending")
        self.assertEqual(new_row["enabled"], "true")
        self.assertEqual(new_row["review_status"], "accepted")
        self.assertEqual(new_row["replacement_reading"], "fixed")
        self.assertEqual(new_row["replacement_gloss"], "")
        self.assertEqual(new_row["rule_id"], old_row["rule_id"])
        self.assertEqual(new_row["key_reading"], "raw")
        self.assertEqual(new_row["page"], "1")
        self.assertEqual(new_row["output_index"], "1")

    def test_accepted_current_disables_and_rejects(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        final = {"reading": "raw", "gloss": "gloss"}
        plan = self._compile(dataset, [_decision(dataset, final=final)])
        [change] = plan["changes"]
        [new_row] = change["new_rows"]
        self.assertEqual(new_row["enabled"], "false")
        self.assertEqual(new_row["review_status"], "rejected")
        self.assertEqual(new_row["replacement_reading"], "fixed")
        self.assertEqual(new_row["replacement_gloss"], "")

    def test_rejected_disables_and_rejects(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        plan = self._compile(dataset, [_decision(dataset, status="rejected")])
        [change] = plan["changes"]
        [new_row] = change["new_rows"]
        self.assertEqual(new_row["enabled"], "false")
        self.assertEqual(new_row["review_status"], "rejected")
        self.assertEqual(new_row["replacement_reading"], "fixed")
        self.assertEqual(new_row["replacement_gloss"], "")

    def test_deferred_never_mutates(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        plan = self._compile(dataset, [_decision(dataset, status="deferred")])
        self.assertEqual(plan["changes"], [])
        self.assertEqual(plan["deferred"], [dataset.records[0].context["rule_id"]])
        from scripts.proofread_review.correction_writeback import apply_correction_plan

        apply_correction_plan(self.catalog_path, plan)
        [row] = _read_correction_csv(self.catalog_path)
        self.assertEqual(row["enabled"], "true")
        self.assertEqual(row["review_status"], "pending")

    def test_custom_ordinary_values_are_written(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        final = {"reading": "custom", "gloss": "gloss"}
        plan = self._compile(dataset, [_decision(dataset, final=final)])
        [change] = plan["changes"]
        [new_row] = change["new_rows"]
        self.assertEqual(new_row["enabled"], "true")
        self.assertEqual(new_row["review_status"], "accepted")
        self.assertEqual(new_row["replacement_reading"], "custom")

    def test_reading_rule_does_not_write_a_custom_gloss(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        final = {"reading": "custom", "gloss": "custom gloss"}
        plan = self._compile(dataset, [_decision(dataset, final=final)])
        [change] = plan["changes"]
        [new_row] = change["new_rows"]
        self.assertEqual(new_row["replacement_reading"], "custom")
        self.assertEqual(new_row["replacement_gloss"], "")

    def test_gloss_rule_maps_final_back_to_replacement_field(self) -> None:
        rule_id = rule_id_for("gloss", "", ("raw", "gloss", "1"))
        dataset = self._dataset(
            [_correction_row(
                rule_id,
                "gloss",
                replacement_reading="",
                replacement_gloss="fixed gloss",
            )]
        )
        final = {"reading": "raw", "gloss": "fixed gloss"}
        plan = self._compile(dataset, [_decision(dataset, final=final)])
        [change] = plan["changes"]
        [new_row] = change["new_rows"]
        self.assertEqual(new_row["replacement_reading"], "")
        self.assertEqual(new_row["replacement_gloss"], "fixed gloss")
        self.assertEqual(new_row["review_status"], "accepted")

    def test_split_custom_rows_are_expanded(self) -> None:
        rule_id = rule_id_for("example_split", "", ("raw", "gloss", "1"))
        rows = [
            _correction_row(
                rule_id,
                "example_split",
                replacement_reading="one",
                replacement_gloss="first.",
                output_index="1",
            ),
            _correction_row(
                rule_id,
                "example_split",
                replacement_reading="two",
                replacement_gloss="second.",
                output_index="2",
            ),
        ]
        dataset = self._dataset(rows)
        final = {"reading": "uno\ndos", "gloss": "primera.\nsegunda."}
        plan = self._compile(dataset, [_decision(dataset, final=final)])
        [change] = plan["changes"]
        self.assertEqual(len(change["old_rows"]), 2)
        self.assertEqual(len(change["new_rows"]), 2)
        first, second = change["new_rows"]
        self.assertEqual(first["output_index"], "1")
        self.assertEqual(first["replacement_reading"], "uno")
        self.assertEqual(first["replacement_gloss"], "primera.")
        self.assertEqual(second["output_index"], "2")
        self.assertEqual(second["replacement_reading"], "dos")
        self.assertEqual(second["replacement_gloss"], "segunda.")
        self.assertEqual(first["enabled"], "true")
        self.assertEqual(first["review_status"], "accepted")

    def test_split_rejected_preserves_all_rows(self) -> None:
        rule_id = rule_id_for("example_split", "", ("raw", "gloss", "1"))
        rows = [
            _correction_row(
                rule_id,
                "example_split",
                replacement_reading="one",
                replacement_gloss="first.",
                output_index="1",
            ),
            _correction_row(
                rule_id,
                "example_split",
                replacement_reading="two",
                replacement_gloss="second.",
                output_index="2",
            ),
        ]
        dataset = self._dataset(rows)
        plan = self._compile(dataset, [_decision(dataset, status="rejected")])
        [change] = plan["changes"]
        self.assertEqual(
            [row["replacement_reading"] for row in change["new_rows"]], ["one", "two"]
        )
        self.assertEqual([row["enabled"] for row in change["new_rows"]], ["false", "false"])
        self.assertEqual(
            [row["review_status"] for row in change["new_rows"]], ["rejected", "rejected"]
        )

    def test_split_mismatched_line_counts_fail_closed(self) -> None:
        rule_id = rule_id_for("example_split", "", ("raw", "gloss", "1"))
        rows = [
            _correction_row(
                rule_id,
                "example_split",
                replacement_reading="one",
                replacement_gloss="first.",
                output_index="1",
            ),
            _correction_row(
                rule_id,
                "example_split",
                replacement_reading="two",
                replacement_gloss="second.",
                output_index="2",
            ),
        ]
        dataset = self._dataset(rows)
        final = {"reading": "one\ntwo", "gloss": "first."}
        with self.assertRaisesRegex(ValueError, "line counts"):
            self._compile(dataset, [_decision(dataset, final=final)])

    def test_note_is_written_to_changed_rows(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        plan = self._compile(dataset, [_decision(dataset, note="查核 PDF 後確認")])
        [change] = plan["changes"]
        [new_row] = change["new_rows"]
        self.assertEqual(new_row["note"], "查核 PDF 後確認")

    def test_stale_source_digest_fails(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        decision = _decision(dataset)
        decision["source_digest"] = "stale"
        with self.assertRaisesRegex(ValueError, "source digest"):
            self._compile(dataset, [decision])

    def test_stale_catalog_digest_fails(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        _write_correction_csv(
            self.catalog_path,
            [_correction_row(
                rule_id_for("reading", "", ("raw", "gloss", "1")),
                replacement_reading="changed",
            )],
        )
        with self.assertRaisesRegex(ValueError, "catalog digest"):
            self._compile(dataset, [_decision(dataset)])

    def test_missing_rule_id_fails(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        data = json.loads(self.data_path.read_text(encoding="utf-8"))
        data["records"][0]["context"]["rule_id"] = "bogus-rule"
        self.data_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tampered = ReviewDataset.from_records(
            [ReviewRecord.from_dict(row) for row in data["records"]]
        )
        with self.assertRaisesRegex(ValueError, "not found"):
            self._compile(tampered, [_decision(tampered)])

    def test_duplicate_decisions_fail(self) -> None:
        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        decision = _decision(dataset)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self._compile(dataset, [decision, dict(decision)])

    def test_apply_writes_changes_and_revalidates(self) -> None:
        from scripts.proofread_review.correction_writeback import apply_correction_plan

        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        plan = self._compile(dataset, [_decision(dataset)])
        apply_correction_plan(self.catalog_path, plan)
        [row] = _read_correction_csv(self.catalog_path)
        self.assertEqual(row["enabled"], "true")
        self.assertEqual(row["review_status"], "accepted")
        catalog = load_correction_catalog(self.catalog_path)
        self.assertEqual(catalog.reading[("raw", "gloss", "1")], "fixed")

    def test_apply_preserves_unrelated_rows(self) -> None:
        from scripts.proofread_review.correction_writeback import apply_correction_plan

        reading_rule = rule_id_for("reading", "", ("raw", "gloss", "1"))
        example_rule = rule_id_for("example_split", "", ("ex1", "example one", "1"))
        dataset = self._dataset(
            [
                _correction_row(reading_rule),
                _correction_row(
                    example_rule,
                    "example_split",
                    key_reading="ex1",
                    key_gloss="example one",
                    replacement_reading="ex2",
                    replacement_gloss="example two.",
                    output_index="1",
                ),
                _correction_row(
                    example_rule,
                    "example_split",
                    key_reading="ex1",
                    key_gloss="example one",
                    replacement_reading="ex3",
                    replacement_gloss="example three.",
                    output_index="2",
                ),
            ]
        )
        plan = self._compile(dataset, [_decision(dataset)])
        apply_correction_plan(self.catalog_path, plan)
        rows = _read_correction_csv(self.catalog_path)
        self.assertEqual(rows[0]["rule_id"], reading_rule)
        self.assertEqual(rows[0]["review_status"], "accepted")
        self.assertEqual(rows[1]["rule_id"], example_rule)
        self.assertEqual(rows[1]["review_status"], "pending")
        self.assertEqual(rows[1]["enabled"], "true")
        self.assertEqual(rows[2]["review_status"], "pending")

    def test_apply_fails_on_stale_catalog_digest(self) -> None:
        from scripts.proofread_review.correction_writeback import apply_correction_plan

        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        plan = self._compile(dataset, [_decision(dataset)])
        _write_correction_csv(
            self.catalog_path,
            [_correction_row(
                rule_id_for("reading", "", ("raw", "gloss", "1")),
                replacement_reading="changed",
            )],
        )
        with self.assertRaisesRegex(ValueError, "catalog digest"):
            apply_correction_plan(self.catalog_path, plan)

    def test_apply_rejects_exact_old_value_conflict(self) -> None:
        from scripts.proofread_review.correction_writeback import apply_correction_plan

        dataset = self._dataset(
            [_correction_row(rule_id_for("reading", "", ("raw", "gloss", "1")))]
        )
        plan = self._compile(dataset, [_decision(dataset)])
        [change] = plan["changes"]
        change["old_rows"] = [
            {
                **row,
                "replacement_reading": "different",
            }
            for row in change["old_rows"]
        ]
        with self.assertRaisesRegex(ValueError, "old rows"):
            apply_correction_plan(self.catalog_path, plan)


if __name__ == "__main__":
    unittest.main()
