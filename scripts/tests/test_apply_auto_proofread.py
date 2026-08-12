from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TARGET_FIELDS = [
    "字目",
    "词条",
    "读音",
    "斐_line",
    "007_puj_orig",
    "diff_韻母",
    "diff_連字號",
    "diff_標調符號",
    "diff_詳情",
]


class TestApplyAutoProofread(unittest.TestCase):
    def test_repaired_rows_replace_reading_and_clear_only_their_diffs(self) -> None:
        target_rows = [
            {
                "字目": "拗",
                "词条": "拗折",
                "读音": "á-cîh ;",
                "斐_line": "57",
                "007_puj_orig": "á cîh",
                "diff_韻母": "",
                "diff_連字號": "Y",
                "diff_標調符號": "",
                "diff_詳情": "連字號: 分隔形式不同",
            },
            {
                "字目": "椏",
                "词条": "路分做两桠",
                "读音": "lō pun cò̤ nŏ̤ a ;",
                "斐_line": "28",
                "007_puj_orig": "lŏ pun cò̤ nŏ̤ a",
                "diff_韻母": "Y",
                "diff_連字號": "",
                "diff_標調符號": "",
                "diff_詳情": "韻母: o/ŏ",
            },
            {
                "字目": "梯",
                "词条": "我张梯在墙块",
                "读音": "úa tieⁿ thui tŏ̤ chîeⁿ kò̤ ;",
                "斐_line": "47238",
                "007_puj_orig": "úa thieⁿ thui tŏ̤ chîeⁿ kò̤",
                "diff_韻母": "Y",
                "diff_連字號": "",
                "diff_標調符號": "",
                "diff_詳情": "聲母: t/th",
            },
        ]
        proofread_rows = [
            {
                "斐_line": "57",
                "校對_puj": "á cîh",
                "校對_詞條": "",
                "校對_來源": "007_puj_orig",
            },
            {"斐_line": "28", "校對_puj": "", "校對_詞條": ""},
            {
                "斐_line": "47238",
                "校對_puj": "",
                "校對_詞條": "倚张梯在墙块",
                "校對_來源": "",
            },
        ]

        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            target_path = directory_path / "target.csv"
            proofread_path = directory_path / "proofread.csv"
            output_path = directory_path / "output.csv"
            with target_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=TARGET_FIELDS)
                writer.writeheader()
                writer.writerows(target_rows)
            with proofread_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=["斐_line", "校對_puj", "校對_詞條", "校對_來源"],
                )
                writer.writeheader()
                writer.writerows(proofread_rows)

            result = subprocess.run(
                [
                    sys.executable,
                    "apply_auto_proofread.py",
                    "--target",
                    str(target_path),
                    "--proofread",
                    str(proofread_path),
                    "--output",
                    str(output_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            with output_path.open(encoding="utf-8", newline="") as file:
                output_rows = list(csv.DictReader(file))

        self.assertEqual(output_rows[0]["读音"], target_rows[0]["读音"])
        self.assertEqual(output_rows[0]["Proofread_读音"], "á cîh")
        self.assertEqual(output_rows[0]["007_puj_orig"], "á cîh")
        self.assertEqual(output_rows[0]["diff_連字號"], "")
        self.assertEqual(output_rows[0]["diff_詳情"], "")
        for field, value in target_rows[1].items():
            self.assertEqual(output_rows[1][field], value)
        self.assertEqual(output_rows[1]["Proofread_读音"], "")
        self.assertEqual(output_rows[1]["Proofread_词条"], "")
        self.assertEqual(output_rows[2]["词条"], target_rows[2]["词条"])
        self.assertEqual(output_rows[2]["Proofread_词条"], "倚张梯在墙块")
        self.assertEqual(output_rows[2]["读音"], target_rows[2]["读音"])
        self.assertEqual(output_rows[2]["diff_詳情"], "聲母: t/th")


if __name__ == "__main__":
    unittest.main()
