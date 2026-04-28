#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.importers.dieghv import DieghvImporter


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

    def test_basic_import(self):
        path = self._write_dict_yaml(
            [
                ("巴", "ba1"),
                ("爸", "ba1"),
                ("把", "ba2"),
            ]
        )
        entries = self.importer.import_file(path, "dictionary")
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].dp, "ba¹")
        self.assertEqual(entries[0].han, "巴")
        self.assertEqual(entries[1].han, "爸")
        self.assertEqual(entries[2].han, "把")

    def test_skips_empty_han(self):
        path = self._write_dict_yaml(
            [
                ("巴", "ba1"),
                ("", "ba2"),
            ]
        )
        entries = self.importer.import_file(path, "dictionary")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].han, "巴")

    def test_skips_comment_lines(self):
        path = self._write_dict_yaml(
            [
                ("巴", "ba1"),
                ("#把", "ba2"),
            ]
        )
        entries = self.importer.import_file(path, "dictionary")
        self.assertEqual(len(entries), 1)

    def test_get_source_name(self):
        self.assertEqual(self.importer.get_source_name(), "dieghv")

    def test_missing_file(self):
        path = self.tmpdir / "nonexistent.dict.yaml"
        entries = self.importer.import_file(path, "dictionary")
        self.assertEqual(len(entries), 0)

    def test_to_dp_conversion(self):
        path = self._write_dict_yaml(
            [
                ("巴", "ba1"),
            ]
        )
        entries = self.importer.import_file(path, "dictionary")
        self.assertEqual(len(entries), 1)
        self.assertIn("¹", entries[0].dp)

    def test_file_extension_resolution(self):
        self._write_dict_yaml(
            [
                ("巴", "ba1"),
            ]
        )
        tsv_path = self.tmpdir / "dieziu.tsv"
        tsv_path.write_text("", encoding="utf-8")
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 1)


if __name__ == "__main__":
    unittest.main()
