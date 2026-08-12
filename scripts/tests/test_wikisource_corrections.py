from __future__ import annotations

import csv
import importlib
import tempfile
import unittest
from pathlib import Path

from scripts.wikisource.corrections import (
    CSV_HEADER,
    CorrectionCatalog,
    CorrectionRule,
    catalog_digest,
    load_correction_catalog,
    rule_id_for,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = (
    PROJECT_ROOT
    / "scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv"
)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADER.split(","), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _base_row(rule_id: str, rule_type: str = "reading", **changes: str) -> dict[str, str]:
    row: dict[str, str] = {
        "rule_id": rule_id,
        "rule_type": rule_type,
        "headword": "",
        "key_reading": "raw",
        "key_gloss": "gloss",
        "page": "25",
        "output_index": "1",
        "replacement_reading": "fixed",
        "replacement_gloss": "",
        "enabled": "true",
        "review_status": "pending",
        "note": "",
    }
    row.update(changes)
    return row


def _all_types_rows() -> list[dict[str, str]]:
    return [
        _base_row(rule_id_for("reading", "", ("raw", "gloss", "25")), "reading"),
        _base_row(
            rule_id_for("gloss", "", ("raw", "gloss", "25")),
            "gloss",
            replacement_reading="",
            replacement_gloss="fixed gloss",
        ),
        _base_row(
            rule_id_for("example_split", "", ("raw", "gloss", "25")),
            "example_split",
            replacement_reading="one",
            replacement_gloss="first.",
            output_index="1",
        ),
        _base_row(
            rule_id_for("example_split", "", ("raw", "gloss", "25")),
            "example_split",
            replacement_reading="two",
            replacement_gloss="second.",
            output_index="2",
        ),
        _base_row(
            rule_id_for("review", "", ("raw", "gloss", "25")),
            "review",
            replacement_reading="fixed",
            replacement_gloss="",
        ),
        _base_row(
            rule_id_for("headword_review", "字", ("raw", "gloss", "25")),
            "headword_review",
            headword="字",
            replacement_reading="fixed",
            replacement_gloss="fixed gloss",
        ),
    ]


class TestLoadCorrectionCatalog(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.fixture = Path(self.temp_dir.name) / "fixture.csv"

    def _load(self, rows: list[dict[str, str]]) -> CorrectionCatalog:
        _write_csv(self.fixture, rows)
        return load_correction_catalog(self.fixture)

    def test_all_rule_types_load_into_indexes(self) -> None:
        catalog = self._load(_all_types_rows())
        self.assertEqual("fixed", catalog.reading[("raw", "gloss", "25")])
        self.assertEqual("fixed gloss", catalog.gloss[("raw", "gloss", "25")])
        self.assertEqual(
            [("one", "first."), ("two", "second.")],
            catalog.example_splits[("raw", "gloss", "25")],
        )
        self.assertEqual(
            ("fixed", None),
            catalog.review[("raw", "gloss", "25")],
        )
        self.assertEqual(
            ("fixed", "fixed gloss"),
            catalog.headword_review[("字", "raw", "gloss", "25")],
        )

    def test_rules_tuple_contains_every_physical_row(self) -> None:
        catalog = self._load(_all_types_rows())
        self.assertEqual(len(catalog.rules), 6)
        split_rows = [rule for rule in catalog.rules if rule.rule_type == "example_split"]
        self.assertEqual([rule.output_index for rule in split_rows], [1, 2])
        self.assertIsInstance(catalog.rules[0], CorrectionRule)

    def test_disabled_rules_stay_in_rules_but_are_excluded_from_indexes(self) -> None:
        rows = _all_types_rows()
        rows[0]["enabled"] = "false"
        rows[0]["review_status"] = "rejected"
        catalog = self._load(rows)
        self.assertEqual(len(catalog.rules), 6)
        self.assertNotIn(("raw", "gloss", "25"), catalog.reading)

    def test_key_bytes_are_preserved_byte_for_byte(self) -> None:
        rows = [
            _base_row(
                rule_id_for("reading", "", ("raw ", "gloss;\t", "25")),
                "reading",
                key_reading="raw ",
                key_gloss="gloss;\t",
            )
        ]
        catalog = self._load(rows)
        self.assertIn(("raw ", "gloss;\t", "25"), catalog.reading)
        self.assertNotIn(("raw", "gloss", "25"), catalog.reading)

    def test_empty_gloss_replacement_becomes_none_in_review(self) -> None:
        catalog = self._load(_all_types_rows())
        self.assertIsNone(catalog.review[("raw", "gloss", "25")][1])
        self.assertEqual(catalog.review[("raw", "gloss", "25")][0], "fixed")


class TestCatalogValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.fixture = Path(self.temp_dir.name) / "fixture.csv"

    def _assert_invalid(self, rows: list[dict[str, str]], pattern: str) -> None:
        _write_csv(self.fixture, rows)
        with self.assertRaisesRegex(ValueError, pattern):
            load_correction_catalog(self.fixture)

    def test_duplicate_rule_id_output_index(self) -> None:
        rows = [
            _base_row("007-reading-aaaa"),
            _base_row("007-reading-aaaa"),
        ]
        self._assert_invalid(rows, "duplicate rule_id/output_index")

    def test_duplicate_logical_key_within_type(self) -> None:
        rows = [
            _base_row("007-reading-aaaa"),
            _base_row("007-reading-bbbb"),
        ]
        self._assert_invalid(rows, "duplicate logical key")

    def test_unknown_rule_type(self) -> None:
        self._assert_invalid([_base_row("007-typo-aaaa", "typo")], "unknown rule_type")

    def test_unknown_review_status(self) -> None:
        self._assert_invalid(
            [_base_row("007-reading-aaaa", review_status="done")],
            "unknown review_status",
        )

    def test_invalid_boolean(self) -> None:
        self._assert_invalid([_base_row("007-reading-aaaa", enabled="yes")], "invalid enabled")

    def test_replacement_rejects_space_before_terminal_punctuation(self) -> None:
        self._assert_invalid(
            [_base_row("007-reading-aaaa", replacement_reading="lṳ́ sĭeⁿ ?")],
            "space before terminal punctuation",
        )

    def test_rule_id_must_match_rule_fields(self) -> None:
        self._assert_invalid(
            [_base_row("007-reading-aaaaaaaaaaaaaaaa")],
            "rule_id does not match rule fields",
        )

    def test_missing_headword(self) -> None:
        self._assert_invalid(
            [
                _base_row(
                    "007-headword_review-aaaa",
                    "headword_review",
                    headword="",
                    replacement_gloss="gloss",
                )
            ],
            "headword_review requires headword",
        )

    def test_forbidden_headword(self) -> None:
        self._assert_invalid(
            [_base_row("007-reading-aaaa", headword="字")],
            "headword must be empty",
        )

    def test_missing_reading_replacement(self) -> None:
        self._assert_invalid(
            [_base_row("007-reading-aaaa", replacement_reading="")],
            "reading requires replacement_reading",
        )

    def test_forbidden_gloss_in_reading(self) -> None:
        self._assert_invalid(
            [_base_row("007-reading-aaaa", replacement_gloss="unexpected")],
            "reading forbids replacement_gloss",
        )

    def test_missing_gloss_replacement(self) -> None:
        self._assert_invalid(
            [
                _base_row(
                    "007-gloss-aaaa",
                    "gloss",
                    replacement_reading="",
                    replacement_gloss="",
                )
            ],
            "gloss requires replacement_gloss",
        )

    def test_review_without_any_replacement(self) -> None:
        self._assert_invalid(
            [
                _base_row(
                    "007-review-aaaa",
                    "review",
                    replacement_reading="",
                    replacement_gloss="",
                )
            ],
            "requires a replacement",
        )

    def test_non_positive_page(self) -> None:
        self._assert_invalid([_base_row("007-reading-aaaa", page="0")], "non-positive page")
        self._assert_invalid([_base_row("007-reading-aaaa", page="-3")], "non-positive page")
        self._assert_invalid([_base_row("007-reading-aaaa", page="abc")], "non-positive page")

    def test_split_group_with_one_row(self) -> None:
        self._assert_invalid(
            [
                _base_row(
                    "007-example_split-aaaa",
                    "example_split",
                    replacement_reading="one",
                    replacement_gloss="first.",
                )
            ],
            "at least two rows",
        )

    def test_split_index_gap(self) -> None:
        rows = [
            _base_row(
                "007-example_split-aaaa",
                "example_split",
                replacement_reading="one",
                replacement_gloss="first.",
                output_index="1",
            ),
            _base_row(
                "007-example_split-aaaa",
                "example_split",
                replacement_reading="three",
                replacement_gloss="third.",
                output_index="3",
            ),
        ]
        self._assert_invalid(rows, "consecutive from 1")

    def test_conflicting_enabled_rows(self) -> None:
        rows = [
            _base_row(
                "007-example_split-aaaa",
                "example_split",
                replacement_reading="one",
                replacement_gloss="first.",
                output_index="1",
            ),
            _base_row(
                "007-example_split-aaaa",
                "example_split",
                replacement_reading="two",
                replacement_gloss="second.",
                output_index="2",
                enabled="false",
            ),
        ]
        self._assert_invalid(rows, "conflicting")

    def test_conflicting_group_fields(self) -> None:
        rows = [
            _base_row(
                "007-example_split-aaaa",
                "example_split",
                replacement_reading="one",
                replacement_gloss="first.",
                output_index="1",
            ),
            _base_row(
                "007-example_split-aaaa",
                "example_split",
                replacement_reading="two",
                replacement_gloss="second.",
                output_index="2",
                page="26",
            ),
        ]
        self._assert_invalid(rows, "conflicting")

    def test_ordinary_rule_requires_output_index_one(self) -> None:
        self._assert_invalid(
            [_base_row("007-reading-aaaa", output_index="2")],
            "requires output_index=1",
        )

    def test_unexpected_header_fails_closed(self) -> None:
        self.fixture.write_text("wrong,columns\n1,2\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected CSV header"):
            load_correction_catalog(self.fixture)


class TestRuleIdFor(unittest.TestCase):
    def test_format_is_type_and_sixteen_hex(self) -> None:
        rule_id = rule_id_for("reading", "", ("a", "b", "1"))
        self.assertRegex(rule_id, r"^007-reading-[0-9a-f]{16}$")

    def test_same_fields_produce_same_id(self) -> None:
        first = rule_id_for("reading", "", ("thâk cṳ", "reads", "100"))
        second = rule_id_for("reading", "", ("thâk cṳ", "reads", "100"))
        self.assertEqual(first, second)

    def test_different_fields_produce_different_ids(self) -> None:
        base = ("thâk cṳ", "reads", "100")
        self.assertNotEqual(
            rule_id_for("reading", "", base),
            rule_id_for("gloss", "", base),
        )
        self.assertNotEqual(
            rule_id_for("reading", "", base),
            rule_id_for("reading", "", ("thâk cṳ", "reads", "101")),
        )
        self.assertNotEqual(
            rule_id_for("reading", "", base),
            rule_id_for("reading", "字", base),
        )


class TestCatalogDigest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _catalog(self, rows: list[dict[str, str]]) -> CorrectionCatalog:
        path = Path(self.temp_dir.name) / "fixture.csv"
        _write_csv(path, rows)
        return load_correction_catalog(path)

    def test_digest_is_stable_under_row_reordering(self) -> None:
        rows = _all_types_rows()
        first = catalog_digest(self._catalog(rows))
        second = catalog_digest(self._catalog(list(reversed(rows))))
        self.assertEqual(first, second)

    def test_digest_changes_when_rules_change(self) -> None:
        rows = _all_types_rows()
        first = catalog_digest(self._catalog(rows))
        rows[0]["replacement_reading"] = "different"
        second = catalog_digest(self._catalog(rows))
        self.assertNotEqual(first, second)

    def test_digest_is_sixty_four_hex(self) -> None:
        digest = catalog_digest(self._catalog(_all_types_rows()))
        self.assertRegex(digest, r"^[0-9a-f]{64}$")


class CorrectionMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = importlib.import_module(
            "scripts.wikisource.007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect"
        )
        cls.catalog = load_correction_catalog(CSV_PATH)

    def test_module_catalog_matches_authoritative_csv(self) -> None:
        self.assertEqual(self.mod.CORRECTION_CATALOG.reading, self.catalog.reading)
        self.assertEqual(self.mod.CORRECTION_CATALOG.gloss, self.catalog.gloss)
        self.assertEqual(self.mod.CORRECTION_CATALOG.example_splits, self.catalog.example_splits)
        self.assertEqual(self.mod.CORRECTION_CATALOG.review, self.catalog.review)
        self.assertEqual(
            self.mod.CORRECTION_CATALOG.headword_review,
            self.catalog.headword_review,
        )

    def test_rule_counts_match_plan(self) -> None:
        counts: dict[str, int] = {}
        seen_ids: set[str] = set()
        for rule in self.catalog.rules:
            if rule.rule_id not in seen_ids:
                seen_ids.add(rule.rule_id)
                counts[rule.rule_type] = counts.get(rule.rule_type, 0) + 1
        self.assertEqual(
            counts,
            {
                "reading": 997,
                "gloss": 2,
                "example_split": 4,
                "review": 2015,
                "headword_review": 3,
            },
        )
        self.assertEqual(len(seen_ids), 3021)
        self.assertEqual(len(self.catalog.rules), 3025)

    def test_all_rule_ids_match_deterministic_formula(self) -> None:
        for rule in self.catalog.rules:
            with self.subTest(rule_id=rule.rule_id):
                self.assertEqual(
                    rule.rule_id,
                    rule_id_for(rule.rule_type, rule.headword, rule.key),
                )

    def test_no_duplicate_logical_keys_within_type(self) -> None:
        seen: dict[str, set[tuple[str, str, str, str]]] = {}
        by_id: dict[str, CorrectionRule] = {rule.rule_id: rule for rule in self.catalog.rules}
        for rule in by_id.values():
            key = (rule.headword, rule.key[0], rule.key[1], rule.key[2])
            type_seen = seen.setdefault(rule.rule_type, set())
            if key in type_seen:
                self.fail(f"duplicate logical key within {rule.rule_type}: {key}")
            type_seen.add(key)

    def test_pages_are_positive_decimal(self) -> None:
        for rule in self.catalog.rules:
            with self.subTest(rule_id=rule.rule_id):
                self.assertGreater(int(rule.key[2]), 0)

    def test_catalog_digest_is_stable_on_reload(self) -> None:
        self.assertEqual(catalog_digest(self.catalog), catalog_digest(self.catalog))


if __name__ == "__main__":
    unittest.main()
