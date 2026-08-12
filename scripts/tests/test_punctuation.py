from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.normalize_punctuation import normalize_csv
from scripts.punctuation import (
    normalize_english_gloss,
    normalize_roman_reading,
    to_chinese_punctuation,
    to_roman_punctuation,
)


class PunctuationTests(unittest.TestCase):
    def test_normalizes_english_gloss_punctuation_without_adding_period(self) -> None:
        self.assertEqual("'s", normalize_english_gloss("’s"))
        self.assertEqual(
            "to knock about; to waste uselessly; to treat carelessly",
            normalize_english_gloss(
                "to knock about ; to waste uselessly;to treat carelessly"
            ),
        )
        self.assertEqual(
            "conspire, *for the throne.",
            normalize_english_gloss("conspire,*for the throne."),
        )
        self.assertEqual("dollar, $10,000.", normalize_english_gloss("dollar, $10,000."))
        self.assertEqual('He called it "wrong"', normalize_english_gloss('He called it “wrong”'))

    def test_normalizes_roman_punctuation_and_syncs_terminal_question_mark(self) -> None:
        self.assertEqual('"tŭn síu pài"', normalize_roman_reading("“tŭn síu pài”"))
        self.assertEqual("ŭ nâng lí tham sek:", normalize_roman_reading("ŭ nâng lí tham sek："))
        self.assertEqual("lṳ́ cò̤-nî sĭeⁿ?", normalize_roman_reading("lṳ́ cò̤-nî sĭeⁿ", "Why?"))
        self.assertEqual("cò̤ hó̤", normalize_roman_reading("cò̤ hó̤", "Do it well."))
        self.assertEqual("cò̤ hó̤.", normalize_roman_reading("cò̤ hó̤.", "Do it well."))
    def test_converts_chinese_punctuation_to_roman(self) -> None:
        self.assertEqual(
            "話, 話. 話; 話: 話! 話? (話) \"話\" '話'",
            to_roman_punctuation("話，話。話；話：話！話？（話）“話”‘話’"),
        )

    def test_converts_roman_punctuation_to_chinese(self) -> None:
        self.assertEqual(
            "話，話。話；話：話！話？（話）“話”‘話’",
            to_chinese_punctuation("話, 話. 話; 話: 話! 話? (話) \"話\" '話'"),
        )

    def test_preserves_and_normalizes_word_apostrophes(self) -> None:
        self.assertEqual("don't", to_roman_punctuation("don't"))
        self.assertEqual("don't", to_roman_punctuation("don‘t"))
        self.assertEqual("don't", to_roman_punctuation("don’t"))
        self.assertEqual("don't", to_chinese_punctuation("don't"))

    def test_quotes_and_inner_apostrophe_are_distinct(self) -> None:
        self.assertEqual(
            "He said: 'don't!'",
            to_roman_punctuation("He said：‘don‘t！’"),
        )
        self.assertEqual(
            "伊講：“don't！”",
            to_chinese_punctuation("伊講: \"don't!\""),
        )

    def test_spacing_is_normalized(self) -> None:
        self.assertEqual("one, two; three!", to_roman_punctuation("one ，two；  three ！"))
        self.assertEqual(
            "How can we get down through such a small aperture?",
            to_roman_punctuation("How can we get down through such a small aperture ?"),
        )
        self.assertEqual("word;", to_roman_punctuation("word\u3000;"))
        self.assertEqual("一，二；三！", to_chinese_punctuation("一 , 二 ; 三 !"))
        self.assertEqual("12。5，12：30", to_chinese_punctuation("12.5, 12:30"))
        self.assertEqual("e.g. words and U.S. usage", to_roman_punctuation("e.g. words and U.S. usage"))

    def test_same_direction_is_idempotent(self) -> None:
        roman = "He said: 'don't!' (Really?)"
        chinese = "伊講：‘好！’（真的？）"
        self.assertEqual(roman, to_roman_punctuation(to_roman_punctuation(roman)))
        self.assertEqual(chinese, to_chinese_punctuation(to_chinese_punctuation(chinese)))

    def test_normalizes_csv_by_field_without_reordering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proofread.csv"
            fieldnames = ["字目", "词条", "读音", "释义", "页码"]
            source = [
                {
                    "字目": "話,好!",
                    "词条": "第一,條!",
                    "读音": "ua，ho！",
                    "释义": "say，‘don‘t！’",
                    "页码": "2",
                },
                {
                    "字目": "人",
                    "词条": "第二,條!",
                    "读音": "nâng，",
                    "释义": "person。",
                    "页码": "1",
                },
            ]
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(source)

            summary = normalize_csv(
                path,
                chinese_fields=("字目", "词条"),
                roman_fields=("读音", "释义"),
                roman_reading_fields=("读音",),
            )

            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                self.assertEqual(fieldnames, reader.fieldnames)
            self.assertEqual(["2", "1"], [row["页码"] for row in rows])
            self.assertEqual("話，好！", rows[0]["字目"])
            self.assertEqual("ua, ho!", rows[0]["读音"])
            self.assertEqual("say, 'don't!'", rows[0]["释义"])
            self.assertEqual(2, summary["rows"])
            self.assertEqual(2, summary["changed_rows"])
            self.assertEqual(1, summary["fields"]["字目"])
            self.assertEqual(2, summary["fields"]["词条"])

    def test_csv_rejects_missing_required_fields_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proofread.csv"
            original = "字目,读音\n話,ua\n"
            path.write_text(original, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "词条"):
                normalize_csv(
                    path,
                    chinese_fields=("字目", "词条"),
                    roman_fields=("读音", "释义"),
                    roman_reading_fields=("读音",),
                )
            self.assertEqual(original, path.read_text(encoding="utf-8"))

    def test_csv_removes_only_terminal_reading_semicolon(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proofread.csv"
            path.write_text(
                "字目,词条,读音,释义\n話,話,a; a-nôⁿ　;,words;\n",
                encoding="utf-8",
            )
            normalize_csv(
                path,
                chinese_fields=("字目", "词条"),
                roman_fields=("读音", "释义"),
                roman_reading_fields=("读音",),
            )
            with path.open(encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual("a; a-nôⁿ", row["读音"])
            self.assertEqual("words;", row["释义"])


if __name__ == "__main__":
    unittest.main()
