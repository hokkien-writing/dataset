#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.importers.dieghv import (
    DieghvImporter,
    _parse_initial_from_code,
    _parse_tone_from_code,
    _is_dieziu,
)


class TestParseInitialFromCode(unittest.TestCase):
    def test_null_initial(self):
        self.assertEqual(_parse_initial_from_code("a1"), "null")

    def test_simple_initial(self):
        self.assertEqual(_parse_initial_from_code("ba1"), "b")

    def test_digraph_initial(self):
        self.assertEqual(_parse_initial_from_code("bho2"), "bh")
        self.assertEqual(_parse_initial_from_code("ngang5"), "ng")

    def test_entering_tone(self):
        self.assertEqual(_parse_initial_from_code("dah8"), "d")
        self.assertEqual(_parse_initial_from_code("ah4"), "null")


class TestParseToneFromCode(unittest.TestCase):
    def test_single_digit(self):
        self.assertEqual(_parse_tone_from_code("ba1"), 1)
        self.assertEqual(_parse_tone_from_code("dah8"), 8)

    def test_no_tone(self):
        self.assertIsNone(_parse_tone_from_code("ba"))


class TestIsDieziu(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(_is_dieziu(""))

    def test_dieziu_yes(self):
        self.assertTrue(_is_dieziu("11111"))
        self.assertTrue(_is_dieziu("00001"))

    def test_dieziu_no(self):
        self.assertFalse(_is_dieziu("11110"))
        self.assertFalse(_is_dieziu("00000"))


class TestDieghvImporter(unittest.TestCase):
    def setUp(self):
        self.importer = DieghvImporter()
        self.tmpdir = Path(tempfile.mkdtemp())

    def _write_dict_yaml(self, entries: list[tuple[str, str]]):
        path = self.tmpdir / "dieziu.dict.yaml"
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Rime dictionary\n")
            f.write("---\nname: dieziu\n...\n")
            for char, code in entries:
                f.write(f"{char}\t{code}\n")
        return path

    def _write_tsv(self, rows: list[list[str]]):
        path = self.tmpdir / "dictionary.tsv"
        with open(path, "w", encoding="utf-8") as f:
            f.write("韻母\t聲母\t聲調\t字頭\t異體\t安澄饒揭潮\t附加語音特徵\n")
            for row in rows:
                f.write("\t".join(row) + "\n")
        return path

    def test_basic_import(self):
        self._write_dict_yaml(
            [
                ("巴", "ba1"),
                ("爸", "ba1"),
                ("把", "ba2"),
            ]
        )
        tsv_path = self._write_tsv(
            [
                ["亞", "b", "1", "巴", "", "", ""],
                ["", "", "", "爸", "", "", ""],
                ["", "", "2", "把", "", "", ""],
            ]
        )
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].dp, "ba1")
        self.assertEqual(entries[0].han, "巴")
        self.assertEqual(entries[1].dp, "ba1")
        self.assertEqual(entries[1].han, "爸")
        self.assertEqual(entries[2].dp, "ba2")
        self.assertEqual(entries[2].han, "把")

    def test_dialect_filter(self):
        self._write_dict_yaml(
            [
                ("澳", "au3"),
            ]
        )
        tsv_path = self._write_tsv(
            [
                ["窩", "null", "3", "澳", "", "11110", ""],
                ["", "", "", "澳", "", "00001", ""],
            ]
        )
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].han, "澳")
        self.assertIn("dieghv", entries[0].source)

    def test_variant_characters(self):
        self._write_dict_yaml(
            [
                ("叩", "kau3"),
            ]
        )
        tsv_path = self._write_tsv(
            [
                ["亞", "k", "3", "扣", "釦", "", ""],
                ["", "", "", "叩", "", "", ""],
            ]
        )
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertTrue(any(e.han == "叩" for e in entries))

    def test_state_inheritance(self):
        self._write_dict_yaml(
            [
                ("巴", "ba1"),
                ("疤", "ba1"),
                ("把", "ba2"),
                ("打", "da2"),
            ]
        )
        tsv_path = self._write_tsv(
            [
                ["亞", "b", "1", "巴", "", "", ""],
                ["", "", "", "疤", "", "", ""],
                ["", "", "2", "把", "", "", ""],
                ["", "d", "", "打", "", "", ""],
            ]
        )
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 4)
        self.assertEqual(entries[3].dp, "da2")

    def test_missing_code_skipped(self):
        self._write_dict_yaml([])
        tsv_path = self._write_tsv(
            [
                ["亞", "b", "1", "巴", "", "", ""],
            ]
        )
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 0)

    def test_null_initial(self):
        self._write_dict_yaml(
            [
                ("亞", "a1"),
                ("阿", "a1"),
            ]
        )
        tsv_path = self._write_tsv(
            [
                ["亞", "null", "1", "亞", "", "", ""],
                ["", "", "", "阿", "", "", ""],
            ]
        )
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].dp, "a1")

    def test_get_source_name(self):
        self.assertEqual(self.importer.get_source_name(), "dieghv")

    def test_missing_dict_yaml(self):
        self._write_dict_yaml([])
        tsv_path = self._write_tsv(
            [
                ["亞", "null", "1", "亞", "", "", ""],
            ]
        )
        (self.tmpdir / "dieziu.dict.yaml").unlink(missing_ok=True)
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 0)


if __name__ == "__main__":
    unittest.main()
