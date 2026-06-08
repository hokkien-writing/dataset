from __future__ import annotations

import unittest
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.processors.dean_to_puj import (
    build_han_index,
    dean_to_latn_norm,
    levenshtein,
    lookup_puj_for_row,
    parse_markdown,
    process_rows,
    split_dean_syllables,
    normalize_dean_syllable,
)


class TestParseMarkdown(unittest.TestCase):

    def test_extracts_table_rows_with_page(self):
        md = "<!-- page:14 -->\n| One | 一 | Chĕk |\n| Two | 二 | Naw |"
        rows = parse_markdown(md)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], ("14", "One", "一", "Chĕk"))
        self.assertEqual(rows[1], ("14", "Two", "二", "Naw"))

    def test_tracks_page_markers(self):
        md = "<!-- page:14 -->\n| A | 嬰 | Hia |\n<!-- page:17 -->\n| B | 靜 | Tiem |"
        rows = parse_markdown(md)
        self.assertEqual(rows[0][0], "14")
        self.assertEqual(rows[1][0], "17")

    def test_skips_non_table_lines(self):
        md = "<!-- page:14 -->\n# VOWEL SOUNDS\n| One | 一 | Chĕk |"
        rows = parse_markdown(md)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], "Chĕk")

    def test_skips_separator_rows(self):
        md = "<!-- page:14 -->\n|---|---|---|\n| One | 一 | Chĕk |"
        rows = parse_markdown(md)
        self.assertEqual(len(rows), 1)

    def test_cleans_ocr_artifacts(self):
        md = "<!-- page:44 -->\n| Six | 六~~丨~~(條)帶 | toa |"
        rows = parse_markdown(md)
        self.assertEqual(rows[0][2], "六條帶")

    def test_handles_phrase_rows(self):
        md = "<!-- page:17 -->\n| Be still | 靜靜 | Tiem tiem |"
        rows = parse_markdown(md)
        self.assertEqual(rows[0], ("17", "Be still", "靜靜", "Tiem tiem"))

    def test_handles_comma_in_dean_latn(self):
        md = "<!-- page:24 -->\n| He lives from hand to mouth | 左手挈、右手去 | Chaw chiw khiĕ,yiw chiw khur |"
        rows = parse_markdown(md)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], "Chaw chiw khiĕ,yiw chiw khur")

    def test_skips_rows_without_han_chars(self):
        md = "<!-- page:54 -->\n| 28 |  | tin chiĕ |"
        rows = parse_markdown(md)
        self.assertEqual(len(rows), 0)


class TestSplitDeanSyllables(unittest.TestCase):

    def test_single_syllable(self):
        self.assertEqual(split_dean_syllables("Chĕk"), ["chĕk"])

    def test_hyphenated(self):
        self.assertEqual(split_dean_syllables("a-nou-kia"), ["a", "nou", "kia"])

    def test_space_separated(self):
        self.assertEqual(split_dean_syllables("Tiem tiem"), ["tiem", "tiem"])

    def test_complex_phrase(self):
        result = split_dean_syllables("Lur a-pey si liou")
        self.assertEqual(result, ["lur", "a", "pey", "si", "liou"])

    def test_special_chars(self):
        self.assertEqual(split_dean_syllables("mʼkheng"), ["mʼkheng"])

    def test_gn_initial(self):
        self.assertEqual(split_dean_syllables("Gñou chap gñou"), ["gñou", "chap", "gñou"])

    def test_c_apostrophe(self):
        self.assertEqual(split_dean_syllables("Cʼhin"), ["cʼhin"])


class TestNormalizeDeanSyllable(unittest.TestCase):

    def test_strip_breve(self):
        self.assertEqual(normalize_dean_syllable("chĕk"), "chek")

    def test_breve_open_syllable_adds_h(self):
        self.assertEqual(normalize_dean_syllable("Pĕ"), "peh")
        self.assertEqual(normalize_dean_syllable("Chĭt"), "chit")
        self.assertEqual(normalize_dean_syllable("Pău"), "pauh")

    def test_gn_to_ng(self):
        self.assertEqual(normalize_dean_syllable("gñou"), "ngou")

    def test_aou_to_au(self):
        self.assertEqual(normalize_dean_syllable("kaou"), "kau")

    def test_aw_to_o(self):
        self.assertEqual(normalize_dean_syllable("naw"), "no")

    def test_ey_to_e(self):
        self.assertEqual(normalize_dean_syllable("pey"), "pe")

    def test_ow_to_ou(self):
        self.assertEqual(normalize_dean_syllable("kaw"), "ko")

    def test_lowercase(self):
        self.assertEqual(normalize_dean_syllable("Chap"), "chap")

    def test_complex(self):
        self.assertEqual(normalize_dean_syllable("Pong"), "pong")


class TestLevenshtein(unittest.TestCase):

    def test_identical(self):
        self.assertEqual(levenshtein("chap", "chap"), 0)

    def test_one_substitution(self):
        self.assertEqual(levenshtein("chap", "tsap"), 2)

    def test_different_lengths(self):
        self.assertEqual(levenshtein("chhit", "chit"), 1)

    def test_empty_strings(self):
        self.assertEqual(levenshtein("", ""), 0)
        self.assertEqual(levenshtein("a", ""), 1)


class TestBuildHanIndex(unittest.TestCase):

    def setUp(self):
        import csv, io
        csv_text = "latn_norm,puj,dp,han,han_variants,en,zh_CN,zh_TW,source\n"
        csv_text += "a1,a,,阿,,,,,\n"
        csv_text += "nng6,nng6,,二,,,,,\n"
        csv_text += "no6,no6,,二,,,,,\n"
        csv_text += "chek8,chek8,,一,,,,,\n"
        csv_text += "it8,it8,,一,,,,,\n"
        csv_text += "kau2,kau2,,九,,,,,\n"
        csv_text += "ou5,ou5,,黑,,,,,\n"
        self.reader = csv.DictReader(io.StringIO(csv_text))
        self.index = build_han_index(self.reader)

    def test_index_has_entries(self):
        self.assertIn("一", self.index)
        self.assertIn("二", self.index)
        self.assertIn("九", self.index)

    def test_index_returns_list_of_puj(self):
        entries = self.index["一"]
        self.assertIsInstance(entries, list)
        self.assertIn(("chek8", "chek8"), entries)

    def test_multiple_readings(self):
        entries = self.index["二"]
        pujs = [p for p, _ in entries]
        self.assertIn("nng6", pujs)
        self.assertIn("no6", pujs)


class TestLookupPujForRow(unittest.TestCase):

    def setUp(self):
        import csv, io
        csv_text = "latn_norm,puj,dp,han,han_variants,en,zh_CN,zh_TW,source\n"
        csv_text += "nng6,nng6,,二,,,,,\n"
        csv_text += "no6,no6,,二,,,,,\n"
        csv_text += "chek8,chek8,,一,,,,,\n"
        csv_text += "it8,it8,,一,,,,,\n"
        csv_text += "kau2,kau2,,九,,,,,\n"
        csv_text += "ou5,ou5,,黑,,,,,\n"
        csv_text += "nang5,nang5,,人,,,,,\n"
        csv_text += "hueh4,hueh4,,血,,,,,\n"
        self.reader = csv.DictReader(io.StringIO(csv_text))
        self.index = build_han_index(self.reader)

    def test_single_char_exact_match(self):
        han_chars = ["一"]
        dean_syllables = ["chĕk"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertEqual(result, ["chek8"])

    def test_ambiguous_selects_closest(self):
        han_chars = ["二"]
        dean_syllables = ["naw"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertEqual(result, ["no6"])

    def test_multiple_chars(self):
        han_chars = ["人"]
        dean_syllables = ["nang"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertEqual(result, ["nang5"])

    def test_char_not_in_index_returns_none(self):
        han_chars = ["X"]
        dean_syllables = ["foo"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertIsNone(result)

    def test_same_pre_coda_picks_best(self):
        han_chars = ["三"]
        dean_syllables = ["Sa"]
        sam_index: dict[str, list[tuple[str, str]]] = {
            "三": [("sam", "sam1"), ("saⁿ", "sann1")],
        }
        result = lookup_puj_for_row(han_chars, dean_syllables, sam_index)
        self.assertEqual(result, ["sam"])

    def test_mismatched_counts_ties_returns_none_per_syllable(self):
        han_chars = ["一", "二"]
        dean_syllables = ["chĕk"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertEqual(result, [None])

    def test_extra_syllables_returns_none(self):
        han_chars = ["一"]
        dean_syllables = ["foo", "chĕk", "bar"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertIsNone(result)
