import unittest
from scripts.tests.test_latn_translator_base import TranslatorTestBase


class TestPOJToPUJ(TranslatorTestBase):
    SOURCE_SYSTEM = "POJ"
    TARGET_SYSTEM = "PUJ"

    def test_initials(self):
        self.assert_round_trip(
            [
                ("pang", "pang"),
                ("phang", "phang"),
                ("bang", "bang"),
                ("tang", "tang"),
                ("thang", "thang"),
                ("kang", "kang"),
                ("khang", "khang"),
                ("gang", "gang"),
                ("sang", "sang"),
                ("hang", "hang"),
                ("lang", "lang"),
                ("mang", "mang"),
                ("nang", "nang"),
                ("ngang", "ngang"),
            ]
        )

    def test_vowels(self):
        self.assert_round_trip(
            [
                ("o͘", "ou"),
                ("óa", "uá"),
                ("ōe", "uē"),
            ]
        )

    def test_consonant_conditional(self):
        self.assert_round_trip(
            [
                ("chhí", "chhí"),
                ("chhá", "tshá"),
                ("chì", "chì"),
                ("cha", "tsa"),
                ("jí", "jí"),
                ("jó", "zó"),
            ]
        )

    def test_nasal_endings(self):
        self.assert_round_trip(
            [
                ("sam", "sam"),
                ("san", "san"),
                ("sang", "sang"),
                ("chham", "tsham"),
                ("chhim", "chhim"),
                ("chan", "tsan"),
                ("chin", "chin"),
            ]
        )

    def test_entering_endings(self):
        self.assert_round_trip(
            [
                ("sa̍p", "sa̍p"),
                ("sa̍t", "sa̍t"),
                ("cha̍p", "tsa̍p"),
                ("cha̍t", "tsa̍t"),
            ]
        )

    def test_sentences(self):
        self.assert_round_trip(
            [
                ("o͘-óa-ōe", "ou-uá-uē"),
            ]
        )


if __name__ == "__main__":
    unittest.main()
