from __future__ import annotations

import unittest

from scripts.proofread_review.left_writeback import compile_left_plan
from scripts.proofread_review.models import ReviewDataset, ReviewRecord


class LeftWritebackTests(unittest.TestCase):
    def test_mismatch_is_skipped_and_normal_decision_preserves_reading_style(self) -> None:
        source = [
            self._source("a", "old", "new"),
            self._source("b", "old", "new"),
        ]
        target = [self._target("a", "old"), self._target("b", "old")]
        records = [self._record(0), self._record(1)]
        dataset = ReviewDataset.from_records(
            [ReviewRecord.from_dict(record) for record in records]
        )
        exported_records = list(dataset.to_dict()["records"])
        payload = {
            "schema": "proofread-review-decisions/v1",
            "data_version": dataset.data_version,
            "decisions": [
                self._decision(exported_records[0], "mismatch", "kept", "ignored"),
                self._decision(exported_records[1], "normal_match", "fixed", "chosen"),
            ],
        }
        plan = compile_left_plan(
            source,
            target,
            dataset.to_dict(),
            payload,
        )
        self.assertEqual(1, len(plan["skipped"]))
        self.assertEqual("fixed ;", plan["changes"][0]["fields"]["读音"]["new"])
        self.assertEqual("chosen", plan["changes"][0]["fields"]["释义"]["new"])

    @staticmethod
    def _source(term: str, gloss: str, proofread_gloss: str) -> dict[str, str]:
        row = LeftWritebackTests._target(term, gloss)
        row.update(
            {
                "Proofread_字目": "",
                "Proofread_词条": "",
                "Proofread_读音": "fixed ;",
                "Proofread_释义": proofread_gloss,
                "Proofread_释义_2": "",
                "Proofread_页码": "",
            }
        )
        return row

    @staticmethod
    def _target(term: str, gloss: str) -> dict[str, str]:
        return {
            "字目": term,
            "词条": term,
            "读音": "old ;",
            "释义": gloss,
            "字段1": "",
            "字段2": "",
            "页码": "1",
        }

    @staticmethod
    def _record(row: int) -> dict[str, object]:
        return {
            "row": row,
            "page": row + 1,
            "issues": ["cross_type"],
            "table_key": [f"key-{row}", "old", str(row + 1)],
            "current": {"reading": "old", "gloss": "old"},
            "proposal": {"reading": "fixed", "gloss": "new"},
            "context": {},
        }

    @staticmethod
    def _decision(
        record: dict[str, object], disposition: str, reading: str, gloss: str
    ) -> dict[str, object]:
        return {
            "id": record["id"],
            "source_digest": record["source_digest"],
            "status": "accepted",
            "disposition": disposition,
            "final": {"reading": reading, "gloss": gloss},
            "note": "",
        }


if __name__ == "__main__":
    unittest.main()
