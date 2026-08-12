from __future__ import annotations

import csv
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = PROJECT_ROOT / "books" / "斐姑娘詞典_真實讀音差異_最終.csv"
MERGED_PATH = PROJECT_ROOT / "books" / "斐姑娘詞典_帶漢字詞條2.csv"


class TestMatchByEnglishDiffClassification(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(
            [sys.executable, "match_by_en.py"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        with OUTPUT_PATH.open(encoding="utf-8", newline="") as file:
            cls.rows = {
                row["斐_line"]: row
                for row in csv.DictReader(file)
            }

    def test_hyphen_difference_has_its_own_column(self) -> None:
        row = self.rows["57"]

        self.assertEqual(row["读音"], "á-cîh")
        self.assertEqual(row["007_puj_orig"], "á cîh")
        self.assertEqual(row["diff_連字號"], "Y")
        self.assertEqual(row["diff_韻母"], "")
        self.assertEqual(row["diff_音節數"], "")

    def test_tone_mark_placement_difference_has_its_own_column(self) -> None:
        row = self.rows["98"]

        self.assertEqual(row["读音"], "sĭ úa ā")
        self.assertEqual(row["007_puj_orig"], "sĭ uá ā")
        self.assertEqual(row["diff_標調符號"], "Y")
        self.assertEqual(row["diff_第六調"], "")
        self.assertEqual(row["diff_拼寫"], "")

    def test_hyphen_and_tone_mark_differences_can_coexist(self) -> None:
        row = self.rows["25225"]

        self.assertEqual(row["diff_連字號"], "Y")
        self.assertEqual(row["diff_標調符號"], "Y")
        self.assertEqual(row["diff_拼寫"], "")

    def test_sixth_tone_symbol_difference_remains_separate(self) -> None:
        row = self.rows["9001"]

        self.assertEqual(row["diff_第六調"], "Y")
        self.assertEqual(row["diff_標調符號"], "")

    def test_genuine_tone_difference_remains_phonological(self) -> None:
        row = self.rows["58"]

        self.assertEqual(row["diff_聲調"], "Y")
        self.assertEqual(row["diff_標調符號"], "")

    def test_breve_is_sixth_tone_not_part_of_final(self) -> None:
        row = self.rows["26887"]

        self.assertEqual(row["读音"], "ût m̄ lā")
        self.assertEqual(row["007_puj_orig"], "ût m̄ lă")
        self.assertEqual(row["diff_聲調"], "Y")
        self.assertEqual(row["diff_韻母"], "")
        self.assertEqual(row["diff_詳情"], "聲調: 7/6")

    def test_standalone_question_mark_is_not_a_syllable(self) -> None:
        row = self.rows["27291"]

        self.assertEqual(row["diff_音節數"], "")
        self.assertEqual(row["diff_韻母"], "")
        self.assertEqual(row["diff_聲調"], "Y")
        self.assertEqual(row["diff_詳情"], "聲調: 5/3")

    def test_fullwidth_exclamation_mark_is_not_part_of_final(self) -> None:
        row = self.rows["28633"]

        self.assertEqual(row["diff_韻母"], "")
        self.assertEqual(row["diff_拼寫"], "Y")
        self.assertEqual(row["diff_詳情"], "拼寫/標點差異")

    def test_tone_difference_after_hyphen_is_not_spelling(self) -> None:
        row = self.rows["31465"]

        self.assertEqual(row["读音"], "ńg-khàu")
        self.assertEqual(row["007_puj_orig"], "ńg-kháu")
        self.assertEqual(row["diff_聲調"], "Y")
        self.assertEqual(row["diff_拼寫"], "")
        self.assertEqual(row["diff_詳情"], "聲調: 3/2")

    def test_breve_overrides_entering_tone_default(self) -> None:
        row = self.rows["41518"]

        self.assertEqual(row["读音"], "tam-ĭen ke kúi jĭt")
        self.assertEqual(row["007_puj_orig"], "tam-ĭen ke kúi jît")
        self.assertEqual(row["diff_聲調"], "Y")
        self.assertEqual(row["diff_詳情"], "聲調: 6/8")

    def test_c_initial_is_not_misclassified_as_part_of_rhyme(self) -> None:
        row = self.rows["38217"]

        self.assertEqual(row["diff_聲母"], "Y")
        self.assertEqual(row["diff_韻母"], "")
        self.assertEqual(row["diff_詳情"], "聲母: c/s")


class TestMergeBackDiffColumns(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(
            [sys.executable, "merge_back.py"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        with MERGED_PATH.open(encoding="utf-8", newline="") as file:
            cls.all_rows = list(csv.DictReader(file))
        cls.rows = {
            row["斐_line"]: row
            for row in cls.all_rows
            if row["斐_line"]
        }
        with OUTPUT_PATH.open(encoding="utf-8", newline="") as file:
            cls.diff_rows = list(csv.DictReader(file))

    def test_hyphen_column_is_merged_back(self) -> None:
        row = self.rows["57"]

        self.assertEqual(row["diff_連字號"], "Y")
        self.assertEqual(row["diff_標調符號"], "")

    def test_tone_mark_column_is_merged_back(self) -> None:
        row = self.rows["98"]

        self.assertEqual(row["diff_連字號"], "")
        self.assertEqual(row["diff_標調符號"], "Y")

    def test_each_diff_is_merged_to_its_source_line_only(self) -> None:
        for column in ("diff_連字號", "diff_標調符號"):
            expected = sum(row[column] == "Y" for row in self.diff_rows)
            actual = sum(row[column] == "Y" for row in self.all_rows)
            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
