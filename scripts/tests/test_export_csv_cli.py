from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import export_csv
from scripts.processors.base import Entry


class ExportCsvCliTests(unittest.TestCase):
    def test_parse_args_accepts_repeated_books_and_preserve_order(self) -> None:
        args = export_csv.parse_args(
            ["--book", "007_book", "--book", "008_book", "--preserve-order"]
        )
        self.assertEqual(["007_book", "008_book"], args.books)
        self.assertTrue(args.preserve_order)

    def test_order_entries_sorts_by_default(self) -> None:
        entries = [SimpleNamespace(puj="b", poj=""), SimpleNamespace(puj="a", poj="")]
        self.assertEqual(
            ["a", "b"],
            [entry.puj for entry in export_csv.order_entries(entries, False)],
        )

    def test_order_entries_preserves_processor_order(self) -> None:
        entries = [SimpleNamespace(puj="b", poj=""), SimpleNamespace(puj="a", poj="")]
        result = export_csv.order_entries(entries, True)
        self.assertIs(entries, result)
        self.assertEqual(["b", "a"], [entry.puj for entry in result])

    def test_resolve_books_returns_requested_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            books_dir = Path(directory)
            (books_dir / "second.md").touch()
            (books_dir / "first.md").touch()
            self.assertEqual(
                [books_dir / "second.md", books_dir / "first.md"],
                export_csv.resolve_books(["second", "first"], books_dir),
            )

    def test_resolve_books_rejects_missing_book(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "missing"):
                export_csv.resolve_books(["missing"], Path(directory))

    def test_explicit_book_without_processor_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            books_dir = project_root / "books"
            books_dir.mkdir()
            (books_dir / "missing_processor.md").touch()
            with (
                patch.object(export_csv, "PROJECT_ROOT", project_root),
                patch.object(export_csv, "find_processor", return_value=None),
                self.assertRaisesRegex(SystemExit, "missing_processor"),
            ):
                export_csv.main(["--book", "missing_processor"])

    def test_normalizes_canonical_roman_and_english_fields_only(self) -> None:
        entry = Entry(
            han="",
            han_orig="",
            puj="ŭ nâng lí tham sek：",
            puj_orig="“ŭ nâng lí tham sek：”",
            en="is anybody covetous?",
            en_orig="is anybody covetous?",
            source="book",
        )
        export_csv.normalize_entry_punctuation(entry)
        self.assertEqual("ŭ nâng lí tham sek?", entry.puj)
        self.assertEqual("is anybody covetous?", entry.en)
        self.assertEqual("“ŭ nâng lí tham sek：”", entry.puj_orig)
        self.assertEqual("is anybody covetous?", entry.en_orig)


if __name__ == "__main__":
    unittest.main()
