#!/usr/bin/env python3

import csv
import tempfile
import unittest
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.importers.chhoetaigi import ChhoeTaigiImporter, extract_han_chars


class TestExtractHanChars(unittest.TestCase):
    def test_pure_han(self):
        self.assertEqual(extract_han_chars("國語"), "國語")

    def test_mixed_hanlo(self):
        self.assertEqual(extract_han_chars("出外 chhut-gōa"), "出外")

    def test_no_han(self):
        self.assertEqual(extract_han_chars("chhut-gōa"), "")

    def test_empty(self):
        self.assertEqual(extract_han_chars(""), "")


class TestChhoeTaigiImporter(unittest.TestCase):
    def setUp(self):
        self.importer = ChhoeTaigiImporter()
        self.tmpdir = Path(tempfile.mkdtemp())

    def _write_csv(self, filename: str, fieldnames: list, rows: list):
        path = self.tmpdir / filename
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return path

    def test_basic_import(self):
        path = self._write_csv(
            "test.csv",
            [
                "DictWordID",
                "PojUnicode",
                "KipUnicode",
                "HanLoTaibunPoj",
                "HoaBun",
                "EngBun",
            ],
            [
                {
                    "DictWordID": "1",
                    "PojUnicode": "chhùi",
                    "KipUnicode": "tshuì",
                    "HanLoTaibunPoj": "喙",
                    "HoaBun": "嘴巴",
                    "EngBun": "mouth",
                },
            ],
        )
        entries = self.importer.import_file(path, "test")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].poj, "chhùi")
        self.assertEqual(entries[0].tl, "tshuì")
        self.assertEqual(entries[0].han, "喙")
        self.assertEqual(entries[0].en, "mouth")
        self.assertEqual(entries[0].zh_TW, "嘴巴")
        self.assertIn("ChhoeTaigi", entries[0].source)

    def test_fallback_to_kip_for_han(self):
        path = self._write_csv(
            "test.csv",
            ["DictWordID", "PojUnicode", "KipUnicode", "HanLoTaibunKip"],
            [
                {
                    "DictWordID": "1",
                    "PojUnicode": "kóng",
                    "KipUnicode": "kóng",
                    "HanLoTaibunKip": "講",
                },
            ],
        )
        entries = self.importer.import_file(path, "test")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].han, "講")

    def test_skip_no_han(self):
        path = self._write_csv(
            "test.csv",
            ["DictWordID", "PojUnicode", "KipUnicode", "HanLoTaibunPoj"],
            [
                {
                    "DictWordID": "1",
                    "PojUnicode": "chhut-gōa",
                    "KipUnicode": "",
                    "HanLoTaibunPoj": "",
                },
            ],
        )
        entries = self.importer.import_file(path, "test")
        self.assertEqual(len(entries), 1)

    def test_skip_no_romanization(self):
        path = self._write_csv(
            "test.csv",
            ["DictWordID", "PojUnicode", "KipUnicode", "HanLoTaibunPoj"],
            [
                {
                    "DictWordID": "1",
                    "PojUnicode": "",
                    "KipUnicode": "",
                    "HanLoTaibunPoj": "測試",
                },
            ],
        )
        entries = self.importer.import_file(path, "test")
        self.assertEqual(len(entries), 0)

    def test_get_source_name(self):
        self.assertEqual(self.importer.get_source_name(), "ChhoeTaigi")

    def test_mixed_hanlo_extraction(self):
        path = self._write_csv(
            "test.csv",
            ["DictWordID", "PojUnicode", "KipUnicode", "HanLoTaibunPoj", "HoaBun"],
            [
                {
                    "DictWordID": "1",
                    "PojUnicode": "chhut-gōa",
                    "KipUnicode": "tshut-guā",
                    "HanLoTaibunPoj": "出外",
                    "HoaBun": "外出",
                },
            ],
        )
        entries = self.importer.import_file(path, "test")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].han, "出外")

    def test_missing_optional_fields(self):
        path = self._write_csv(
            "test.csv",
            ["DictWordID", "PojUnicode", "HanLoTaibunPoj"],
            [
                {
                    "DictWordID": "1",
                    "PojUnicode": "kóng",
                    "HanLoTaibunPoj": "講",
                },
            ],
        )
        entries = self.importer.import_file(path, "test")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].tl, "")
        self.assertEqual(entries[0].en, "")
        self.assertEqual(entries[0].zh_TW, "")


if __name__ == "__main__":
    unittest.main()
