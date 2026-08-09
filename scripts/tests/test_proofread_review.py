from __future__ import annotations

import unittest
import csv
import json
import re
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

from scripts.proofread_review.build_data import build_review_dataset
from scripts.proofread_review.correction_review import (
    build_correction_review_dataset,
    build_pre_correction_markdown,
    build_source_entries,
)
from scripts.proofread_review.models import (
    ReviewDataset,
    ReviewRecord,
    stable_record_id,
    validate_decision_export,
)
from scripts.proofread_review.server import DocumentConfig, create_server
from scripts.wikisource.corrections import (
    CSV_HEADER,
    load_correction_catalog,
    rule_id_for,
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


class TestReviewModels(unittest.TestCase):
    def _record(self, **changes: object) -> dict[str, object]:
        value: dict[str, object] = {
            "row": 42,
            "page": 32,
            "issues": ["cross_type"],
            "table_key": ["au", "To cudgel; to maul.", "32"],
            "current": {"reading": "au", "gloss": "To cudgel; to maul."},
            "proposal": {
                "reading": "áu",
                "gloss": "To fight with sticks or fists.",
            },
            "context": {"headword": "殴", "kind": "example"},
        }
        value.update(changes)
        return value

    def test_stable_id_ignores_mapping_and_issue_order(self) -> None:
        first = self._record(issues=["truncated_gloss", "cross_type"])
        second = {
            "context": {"kind": "example", "headword": "殴"},
            "proposal": {
                "gloss": "To fight with sticks or fists.",
                "reading": "áu",
            },
            "current": {"gloss": "To cudgel; to maul.", "reading": "au"},
            "table_key": ["au", "To cudgel; to maul.", "32"],
            "issues": ["cross_type", "truncated_gloss"],
            "page": 32,
            "row": 42,
        }
        self.assertEqual(stable_record_id(first), stable_record_id(second))

    def test_007_page_is_already_the_pdf_page(self) -> None:
        record = ReviewRecord.from_dict(self._record())
        self.assertEqual(record.pdf_page, 32)

    def test_duplicate_record_ids_fail_closed(self) -> None:
        record = ReviewRecord.from_dict(self._record())
        with self.assertRaisesRegex(ValueError, "duplicate stable id"):
            ReviewDataset.from_records([record, record])

    def test_stale_source_digest_is_rejected(self) -> None:
        dataset = ReviewDataset.from_records(
            [ReviewRecord.from_dict(self._record())]
        )
        payload = {
            "schema": "proofread-review-decisions/v1",
            "data_version": dataset.data_version,
            "decisions": [
                {
                    "id": dataset.records[0].id,
                    "source_digest": "stale",
                    "status": "accepted",
                    "final": {"reading": "áu"},
                    "note": "",
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "source digest"):
            validate_decision_export(dataset, payload)

    def test_old_normal_match_decision_remains_compatible(self) -> None:
        dataset = ReviewDataset.from_records([ReviewRecord.from_dict(self._record())])
        record = dataset.records[0]
        payload = {
            "schema": "proofread-review-decisions/v1",
            "data_version": dataset.data_version,
            "decisions": [{
                "id": record.id,
                "source_digest": record.source_digest,
                "status": "accepted",
                "final": {"reading": "áu", "gloss": "updated"},
                "note": "",
            }],
        }
        [decision] = validate_decision_export(dataset, payload)
        self.assertEqual(decision["disposition"], "normal_match")

    def test_non_normal_match_requires_semantic_note(self) -> None:
        dataset = ReviewDataset.from_records([ReviewRecord.from_dict(self._record())])
        record = dataset.records[0]
        payload = {
            "schema": "proofread-review-decisions/v1",
            "data_version": dataset.data_version,
            "decisions": [{
                "id": record.id,
                "source_digest": record.source_digest,
                "status": "accepted",
                "disposition": "rematch",
                "final": {"reading": "áu", "gloss": "updated"},
                "note": "",
                "left_action": "",
                "source_007_action": "",
                "rematch_target": "",
            }],
        }
        with self.assertRaisesRegex(ValueError, "semantic note"):
            validate_decision_export(dataset, payload)

        payload["decisions"][0]["note"] = "這兩條錯配；左側保留，不回寫。"
        [decision] = validate_decision_export(dataset, payload)
        self.assertEqual(decision["disposition"], "rematch")
        self.assertEqual(decision["note"], "這兩條錯配；左側保留，不回寫。")

    def test_legacy_treatment_fields_are_folded_into_note(self) -> None:
        dataset = ReviewDataset.from_records([ReviewRecord.from_dict(self._record())])
        record = dataset.records[0]
        payload = {
            "schema": "proofread-review-decisions/v1",
            "data_version": dataset.data_version,
            "decisions": [{
                "id": record.id,
                "source_digest": record.source_digest,
                "status": "accepted",
                "disposition": "mismatch",
                "final": {"reading": "áu", "gloss": "updated"},
                "note": "原備註",
                "left_action": "保留左側",
                "source_007_action": "取消修正",
                "rematch_target": "p33 áu",
            }],
        }
        [decision] = validate_decision_export(dataset, payload)
        self.assertIn("原備註", decision["note"])
        self.assertIn("左側 CSV：保留左側", decision["note"])
        self.assertIn("007：取消修正", decision["note"])
        self.assertIn("改配目標：p33 áu", decision["note"])

    def test_mismatch_is_complete_without_note_and_never_implies_writeback(self) -> None:
        dataset = ReviewDataset.from_records([ReviewRecord.from_dict(self._record())])
        record = dataset.records[0]
        payload = {
            "schema": "proofread-review-decisions/v1",
            "data_version": dataset.data_version,
            "decisions": [{
                "id": record.id,
                "source_digest": record.source_digest,
                "status": "accepted",
                "disposition": "mismatch",
                "final": {"reading": "áu", "gloss": "updated"},
                "note": "",
            }],
        }
        [decision] = validate_decision_export(dataset, payload)
        self.assertEqual(decision["disposition"], "mismatch")

    def test_previous_offset_dataset_version_remains_importable(self) -> None:
        dataset = ReviewDataset.from_records([ReviewRecord.from_dict(self._record())])
        payload = {
            "schema": "proofread-review-decisions/v1",
            "data_version": "f1df90a4a641d94d184f42b0cf21bb068c7d15e5b772e922673100dc167ce2e1",
            "decisions": [],
        }
        self.assertEqual(validate_decision_export(dataset, payload), [])


class TestReviewDatasetBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = build_review_dataset(
            actions_path=Path("scripts/proofread_review/review_actions_source.json"),
            proofread_path=Path("books/（合併校對&修正讀音）斐姑娘詞典.csv"),
            corrections_path=Path(
                "scripts/wikisource/"
                "007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv"
            ),
        )

    def test_builds_131_unique_entries_with_133_issues(self) -> None:
        self.assertEqual(len(self.dataset.records), 131)
        self.assertEqual(sum(self.dataset.issue_counts.values()), 133)
        self.assertEqual(
            self.dataset.issue_counts,
            {
                "cross_type": 93,
                "empty_key": 27,
                "existing_key_conflict": 1,
                "rule_review": 0,
                "truncated_gloss": 12,
            },
        )
        self.assertEqual(
            sum(len(record.issues) == 2 for record in self.dataset.records), 2
        )

    def test_records_preserve_review_evidence(self) -> None:
        record = next(
            record
            for record in self.dataset.records
            if record.table_key == ("au", "To cudgel; to maul.", "32")
        )
        self.assertEqual(record.pdf_page, 32)
        self.assertEqual(record.current["reading"], "au")
        self.assertEqual(record.proposal["reading"], "áu")
        self.assertEqual(
            record.proposal["gloss"], "To fight with sticks or fists."
        )
        self.assertTrue(record.context["headword"])


class TestReviewServer(unittest.TestCase):
    PDF_PATH = Path(
        "/Users/lim/Desktop/A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.pdf"
    )
    DATASET_PATH = Path("scripts/proofread_review/review_data.json")

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.server = create_server(
            dataset_path=self.DATASET_PATH,
            config=DocumentConfig(pdf_path=self.PDF_PATH, page_field="page", page_offset=0),
            cache_dir=Path(self.temp_dir.name),
            host="127.0.0.1",
            port=0,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def test_health_and_data_are_available_on_loopback(self) -> None:
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        with urllib.request.urlopen(f"{self.base_url}/api/health") as response:
            self.assertEqual(json.load(response)["status"], "ok")
        with urllib.request.urlopen(f"{self.base_url}/api/data") as response:
            data = json.load(response)
        self.assertEqual(data["record_count"], 131)
        self.assertEqual(data["issue_count"], 133)

    def test_pdf_page_is_rendered_and_cached(self) -> None:
        with urllib.request.urlopen(f"{self.base_url}/api/page/56.jpg") as response:
            first = response.read()
            self.assertEqual(response.headers.get_content_type(), "image/jpeg")
        cache_file = Path(self.temp_dir.name) / "page-0056.jpg"
        self.assertTrue(cache_file.exists())
        self.assertGreater(len(first), 10_000)
        first_mtime = cache_file.stat().st_mtime_ns
        with urllib.request.urlopen(f"{self.base_url}/api/page/56.jpg") as response:
            self.assertEqual(response.read(), first)
        self.assertEqual(cache_file.stat().st_mtime_ns, first_mtime)

    def test_invalid_page_and_unknown_paths_fail_closed(self) -> None:
        for path in ("/api/page/0.jpg", "/api/page/649.jpg", "/../etc/passwd"):
            with self.subTest(path=path):
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(f"{self.base_url}{path}")
                self.assertIn(raised.exception.code, {400, 404})


class TestReviewServerPageMapping(unittest.TestCase):
    PDF_PATH = Path(
        "/Users/lim/Desktop/A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.pdf"
    )

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _fixture(self, page: int = 25) -> Path:
        record = ReviewRecord.from_dict(
            {
                "row": 0,
                "page": page,
                "issues": ["rule_review"],
                "table_key": ["raw", "gloss", str(page)],
                "current": {"reading": "raw", "gloss": "gloss"},
                "proposal": {"reading": "fixed", "gloss": "gloss"},
                "context": {
                    "rule_id": "reading-raw-gloss-page",
                    "rule_type": "reading",
                    "headword": "",
                    "key_reading": "raw",
                    "key_gloss": "gloss",
                    "key_page": str(page),
                    "resolved_page": str(page),
                    "output_count": "1",
                    "catalog_digest": "fixture",
                },
            }
        )
        dataset = ReviewDataset.from_records([record]).to_dict()
        path = Path(self.temp_dir.name) / f"dataset-{page}.json"
        path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
        return path

    def _server(self, page_field: str = "page", page_offset: int = 0):
        return create_server(
            dataset_path=self._fixture(),
            config=DocumentConfig(
                pdf_path=self.PDF_PATH,
                page_field=page_field,
                page_offset=page_offset,
            ),
            cache_dir=Path(self.temp_dir.name),
            port=0,
        )

    def _fetch_json(self, server, path: str) -> dict[str, object]:
        base = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(f"{base}{path}") as response:
            return json.load(response)

    def test_page_field_page_zero_offset_maps_record_page_directly(self) -> None:
        server = self._server(page_field="page", page_offset=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            data = self._fetch_json(server, "/api/data")
            self.assertEqual(data["records"][0]["pdf_page"], 25)
            health = self._fetch_json(server, "/api/health")
            self.assertEqual(health["page_field"], "page")
            self.assertEqual(health["page_offset"], 0)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_page_offset_24_preserves_left_csv_reuse(self) -> None:
        server = self._server(page_field="page", page_offset=24)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            data = self._fetch_json(server, "/api/data")
            self.assertEqual(data["records"][0]["pdf_page"], 49)
            health = self._fetch_json(server, "/api/health")
            self.assertEqual(health["page_offset"], 24)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_non_integer_offset_is_rejected_before_launch(self) -> None:
        with self.assertRaisesRegex(ValueError, "offset"):
            create_server(
                dataset_path=self._fixture(),
                config=DocumentConfig(
                    pdf_path=self.PDF_PATH,
                    page_field="page",
                    page_offset="24",
                ),
                cache_dir=Path(self.temp_dir.name),
            )

    def test_unavailable_page_field_is_rejected_before_launch(self) -> None:
        with self.assertRaisesRegex(ValueError, "page field"):
            create_server(
                dataset_path=self._fixture(),
                config=DocumentConfig(
                    pdf_path=self.PDF_PATH,
                    page_field="missing_field",
                    page_offset=0,
                ),
                cache_dir=Path(self.temp_dir.name),
            )


class TestReviewStaticApp(unittest.TestCase):
    STATIC_DIR = Path("scripts/proofread_review/static")

    def test_page_has_review_landmarks_and_accessible_controls(self) -> None:
        html = (self.STATIC_DIR / "index.html").read_text(encoding="utf-8")
        for value in (
            'id="source-viewer"',
            'id="review-form"',
            'id="record-list"',
            'id="error-banner"',
            'aria-label="放大原书"',
            'aria-label="缩小原书"',
            'aria-live="polite"',
            'id="match-disposition"',
            'id="decision-note"',
        ):
            self.assertIn(value, html)
        for value in ('id="left-action"', 'id="source-007-action"', 'id="rematch-target"'):
            self.assertNotIn(value, html)
        self.assertNotIn("onclick=", html)

    def test_script_has_required_review_and_viewer_behaviors(self) -> None:
        script = (self.STATIC_DIR / "app.js").read_text(encoding="utf-8")
        for value in (
            "proofread-review-decisions/v1",
            "localStorage.setItem",
            "preventDefault()",
            'addEventListener("wheel"',
            'addEventListener("pointerdown"',
            'addEventListener("dblclick"',
            "isEditableTarget",
            "source_digest",
            "data_version",
            "normal_match",
            "migrateLegacyTreatment",
        ):
            self.assertIn(value, script)

    def test_wide_sidebar_constrains_height_for_inner_list_scrolling(self) -> None:
        css = (self.STATIC_DIR / "styles.css").read_text(encoding="utf-8")
        self.assertRegex(
            css,
            r"\.record-sidebar\s*\{[^}]*min-height:\s*0;[^}]*overflow:\s*hidden;",
        )

    def test_character_diff_uses_graphemes_and_distinct_add_remove_styles(self) -> None:
        script = (self.STATIC_DIR / "app.js").read_text(encoding="utf-8")
        css = (self.STATIC_DIR / "styles.css").read_text(encoding="utf-8")
        for value in ("Intl.Segmenter", "renderDiffPair", "`diff-${part.type}`"):
            self.assertIn(value, script)
        self.assertIn(".diff-add", css)
        self.assertIn(".diff-remove", css)
        self.assertIn("white-space: pre-wrap", css)
        strong_rule = re.search(r"\.choice-button strong\s*\{([^}]*)\}", css)
        self.assertIsNotNone(strong_rule)
        self.assertNotIn("overflow-wrap: anywhere", strong_rule.group(1))


class TestCorrectionReviewResolution(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.source = (
            "<!-- page:1 -->\n"
            "- **字** raw — gloss\n"
            "  - *ex1* — example one\n"
        )
        self.entries = build_source_entries(self.source)

    def _catalog(self, rows: list[dict[str, str]]):
        path = Path(self.temp_dir.name) / "fixture.csv"
        _write_correction_csv(path, rows)
        return load_correction_catalog(path)

    def _dataset(self, rows: list[dict[str, str]]):
        return build_correction_review_dataset(self._catalog(rows), self.entries)

    def test_all_five_rule_types_resolve_to_source_entries(self) -> None:
        cases = [
            ("reading", "fixed", "", "fixed", "gloss"),
            ("gloss", "", "fixed gloss", "raw", "fixed gloss"),
            ("review", "áu", "To fight with sticks or fists.", "áu", "To fight with sticks or fists."),
        ]
        for rule_type, reading_repl, gloss_repl, proposal_reading, proposal_gloss in cases:
            with self.subTest(rule_type=rule_type):
                rule_id = rule_id_for(rule_type, "", ("raw", "gloss", "1"))
                dataset = self._dataset(
                    [_correction_row(
                        rule_id,
                        rule_type,
                        replacement_reading=reading_repl,
                        replacement_gloss=gloss_repl,
                    )]
                )
                self.assertEqual(len(dataset.records), 1)
                record = dataset.records[0]
                self.assertEqual(record.issues, ("rule_review",))
                self.assertEqual(record.current, {"reading": "raw", "gloss": "gloss"})
                self.assertEqual(
                    record.proposal,
                    {"reading": proposal_reading, "gloss": proposal_gloss},
                )
                self.assertEqual(record.page, 1)
                self.assertEqual(record.pdf_page, 1)
                self.assertEqual(record.table_key, ("raw", "gloss", "1"))
                self.assertEqual(record.context["key_page"], "1")
                self.assertEqual(record.context["resolved_page"], "1")
                self.assertEqual(record.context["output_count"], "1")
                self.assertIn("catalog_digest", record.context)

    def test_headword_review_rule_resolves_by_headword(self) -> None:
        rule_id = rule_id_for("headword_review", "字", ("raw", "gloss", "1"))
        dataset = self._dataset(
            [_correction_row(
                rule_id,
                "headword_review",
                headword="字",
                replacement_reading="字 result",
                replacement_gloss="",
            )]
        )
        self.assertEqual(len(dataset.records), 1)
        self.assertEqual(dataset.records[0].proposal["reading"], "字 result")
        self.assertEqual(dataset.records[0].context["headword"], "字")

    def test_example_line_rule_resolves_to_example_entry(self) -> None:
        rule_id = rule_id_for("reading", "", ("ex1", "example one", "1"))
        dataset = self._dataset(
            [_correction_row(
                rule_id,
                "reading",
                key_reading="ex1",
                key_gloss="example one",
                replacement_reading="ex2",
            )]
        )
        record = dataset.records[0]
        self.assertEqual(record.current, {"reading": "ex1", "gloss": "example one"})
        self.assertEqual(record.proposal["reading"], "ex2")
        self.assertEqual(record.context["headword"], "")

    def test_split_proposal_is_aligned_ordered_lines(self) -> None:
        rule_id = rule_id_for("example_split", "", ("raw", "gloss", "1"))
        dataset = self._dataset(
            [
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
        )
        record = dataset.records[0]
        self.assertEqual(record.proposal["reading"], "one\ntwo")
        self.assertEqual(record.proposal["gloss"], "first.\nsecond.")
        self.assertEqual(record.context["output_count"], "2")
        self.assertEqual(record.context["output_indexes"], "1,2")
        self.assertEqual(record.issues, ("rule_review",))

    def test_split_with_mismatched_newline_counts_is_rejected(self) -> None:
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
                replacement_reading="two\nthree",
                replacement_gloss="second.",
                output_index="2",
            ),
        ]
        with self.assertRaisesRegex(ValueError, "proposal line"):
            self._dataset(rows)

    def test_nearby_rule_resolves_within_two_pages(self) -> None:
        rule_id = rule_id_for("reading", "", ("raw", "gloss", "3"))
        dataset = self._dataset(
            [_correction_row(rule_id, "reading", page="3", replacement_reading="fixed")]
        )
        record = dataset.records[0]
        self.assertEqual(record.page, 1)
        self.assertEqual(record.pdf_page, 1)
        self.assertEqual(record.context["key_page"], "3")
        self.assertEqual(record.context["resolved_page"], "1")

    def test_fragment_key_resolves_by_suffix_within_two_pages(self) -> None:
        source = (
            "<!-- page:1 -->\n"
            "- **字** raw — gloss\n"
            "  - *lṳ́ cò̤-nî sĭeⁿ?* — What do you think about it.\n"
        )
        entries = build_source_entries(source)
        rule_id = rule_id_for("reading", "", ("sĭeⁿ?", "What do you think about it.", "2"))
        rows = [
            _correction_row(
                rule_id,
                "reading",
                key_reading="sĭeⁿ?",
                key_gloss="What do you think about it.",
                page="2",
                replacement_reading="lṳ́ cò̤̀-nî sĭeⁿ ?",
            )
        ]
        dataset = build_correction_review_dataset(self._catalog(rows), entries)
        record = dataset.records[0]
        self.assertEqual(record.page, 1)
        self.assertEqual(record.context["key_page"], "2")
        self.assertEqual(record.current["reading"], "lṳ́ cò̤-nî sĭeⁿ?")
        self.assertEqual(record.proposal["reading"], "lṳ́ cò̤̀-nî sĭeⁿ ?")

    def test_unresolved_rule_fails_closed(self) -> None:
        rule_id = rule_id_for("reading", "", ("missing", "missing", "1"))
        rows = [_correction_row(rule_id, "reading", key_reading="missing", key_gloss="missing")]
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self._dataset(rows)

    def test_ambiguous_rule_without_headword_fails_closed(self) -> None:
        source = "<!-- page:1 -->\n- **甲** raw — gloss\n- **乙** raw — gloss\n"
        entries = build_source_entries(source)
        rule_id = rule_id_for("reading", "", ("raw", "gloss", "1"))
        rows = [_correction_row(rule_id, "reading")]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            build_correction_review_dataset(self._catalog(rows), entries)

    def test_ambiguous_nearby_rule_fails_closed(self) -> None:
        source = "<!-- page:1 -->\n- **甲** raw — gloss\n<!-- page:2 -->\n- **乙** raw — gloss\n"
        entries = build_source_entries(source)
        rule_id = rule_id_for("reading", "", ("raw", "gloss", "3"))
        rows = [_correction_row(rule_id, "reading", page="3")]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            build_correction_review_dataset(self._catalog(rows), entries)

    def test_stable_ids_are_unchanged_by_csv_row_reordering(self) -> None:
        rows = [
            _correction_row(
                rule_id_for("example_split", "", ("raw", "gloss", "1")),
                "example_split",
                replacement_reading="one",
                replacement_gloss="first.",
                output_index="1",
            ),
            _correction_row(
                rule_id_for("example_split", "", ("raw", "gloss", "1")),
                "example_split",
                replacement_reading="two",
                replacement_gloss="second.",
                output_index="2",
            ),
            _correction_row(
                rule_id_for("review", "", ("ex1", "example one", "1")),
                "review",
                key_reading="ex1",
                key_gloss="example one",
                replacement_reading="ex2",
                replacement_gloss="example two.",
            ),
            _correction_row(
                rule_id_for("headword_review", "字", ("raw", "gloss", "1")),
                "headword_review",
                headword="字",
                replacement_reading="字 result",
            ),
        ]
        first = build_correction_review_dataset(self._catalog(rows), self.entries)
        second = build_correction_review_dataset(self._catalog(list(reversed(rows))), self.entries)
        self.assertEqual(
            [record.id for record in first.records],
            [record.id for record in second.records],
        )
        self.assertEqual(
            [record.to_dict() for record in first.records],
            [record.to_dict() for record in second.records],
        )


class TestCorrectionReviewQueue(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        project_root = Path(__file__).resolve().parent.parent.parent
        cache_dir = project_root / "tmp" / "dictionary_of_the_swatow_dialect"
        pages: dict[int, str] = {}
        for n in range(1, 649):
            path = cache_dir / f"p{n:03d}.wikitext"
            if path.exists():
                pages[n] = path.read_text(encoding="utf-8")
        if not pages:
            raise unittest.SkipTest("offline wikisource cache not available")
        title = "Dictionary of the Swatow dialect.djvu"
        pre = build_pre_correction_markdown(pages, 1, 648, title)
        cls.source_entries = build_source_entries(pre)
        cls.catalog = load_correction_catalog(
            project_root
            / "scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv"
        )
        cls.dataset = build_correction_review_dataset(cls.catalog, cls.source_entries)

    def test_queue_accounts_for_all_3034_rules(self) -> None:
        self.assertEqual(len(self.dataset.records), 3034)
        counts: dict[str, int] = {}
        for record in self.dataset.records:
            rule_type = record.context["rule_type"]
            counts[rule_type] = counts.get(rule_type, 0) + 1
        self.assertEqual(
            counts,
            {
                "reading": 1002,
                "gloss": 2,
                "example_split": 11,
                "review": 2016,
                "headword_review": 3,
            },
        )
        self.assertEqual(sum(self.dataset.issue_counts.values()), 3034)
        self.assertEqual(self.dataset.issue_counts["rule_review"], 3034)

    def test_every_record_resolves_with_page_metadata(self) -> None:
        self.assertGreater(len(self.source_entries), 0)
        for record in self.dataset.records:
            with self.subTest(record_id=record.id):
                self.assertEqual(record.issues, ("rule_review",))
                self.assertEqual(record.page, int(record.context["resolved_page"]))
                self.assertEqual(record.pdf_page, record.page)
                self.assertEqual(record.table_key[2], str(record.page))
                self.assertEqual(record.context["key_page"], record.context["key_page"])
                for key in (
                    "rule_id",
                    "rule_type",
                    "key_reading",
                    "key_gloss",
                    "key_page",
                    "resolved_page",
                    "output_count",
                    "catalog_digest",
                ):
                    self.assertIn(key, record.context)


if __name__ == "__main__":
    unittest.main()
