import unittest
from scripts.tests.test_latn_translator_base import TranslatorTestBase


class TestPOJToTL(TranslatorTestBase):
    SOURCE_SYSTEM = "POJ"
    TARGET_SYSTEM = "TL"

    def test_initials(self):
        self.assert_round_trip(
            [
                ("chá", "tsá"),
                ("chhá", "tshá"),
                ("ché", "tsé"),
                ("chhé", "tshé"),
                ("chí", "tsí"),
                ("chhí", "tshí"),
                ("chó", "tsó"),
                ("chhó", "tshó"),
                ("chú", "tsú"),
                ("chhú", "tshú"),
                ("pang", "pang"),
                ("phang", "phang"),
                ("sang", "sang"),
                ("hang", "hang"),
                ("lang", "lang"),
                ("ngang", "ngang"),
            ]
        )

    def test_vowels(self):
        self.assert_round_trip(
            [
                ("óa", "uá"),
                ("òe", "uè"),
                ("ōe", "uē"),
                ("oàn", "uàn"),
            ]
        )

    def test_nasal_endings(self):
        self.assert_round_trip(
            [
                ("cham", "tsam"),
                ("chan", "tsan"),
                ("chang", "tsang"),
                ("chham", "tsham"),
                ("chhan", "tshan"),
                ("chhang", "tshang"),
            ]
        )

    def test_entering_endings(self):
        self.assert_round_trip(
            [
                ("cha̍p", "tsa̍p"),
                ("cha̍t", "tsa̍t"),
                ("chha̍p", "tsha̍p"),
                ("chha̍t", "tsha̍t"),
            ]
        )

    def test_sentences(self):
        self.assert_round_trip(
            [
                ("sió-chiá", "sió-tsiá"),
                ("tâi-oân", "tâi-uân"),
                ("chiah-pùn", "tsiah-pùn"),
            ]
        )


if __name__ == "__main__":
    unittest.main()
