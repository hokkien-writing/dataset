import unittest
from scripts.tests.test_latn_translator_base import TranslatorTestBase


class TestPUJToDP(TranslatorTestBase):
    SOURCE_SYSTEM = "PUJ"
    TARGET_SYSTEM = "DP"

    def test_initials(self):
        self.assert_round_trip(
            [
                ("pang", "bang1"),
                ("phang", "pang1"),
                ("bang", "bhang1"),
                ("tang", "dang1"),
                ("thang", "tang1"),
                ("kang", "gang1"),
                ("khang", "kang1"),
                ("gang", "ghang1"),
                ("tsang", "zang1"),
                ("tshang", "cang1"),
                ("chin", "zin1"),
                ("chhim", "cim1"),
                ("sang", "sang1"),
                ("hang", "hang1"),
                ("lang", "lang1"),
                ("mang", "mang1"),
                ("nang", "nang1"),
                ("ngang", "ngang1"),
            ]
        )

    def test_vowels(self):
        self.assert_round_trip(
            [
                ("sa", "sa1"),
                ("sê", "sê5"),
                ("si", "si1"),
                ("so", "so1"),
                ("su", "su1"),
                ("sṳ", "se1"),
            ]
        )

    def test_nasal_endings(self):
        self.assert_round_trip(
            [
                ("sam", "sam1"),
                ("san", "san1"),
                ("sang", "sang1"),
            ]
        )

    def test_entering_endings(self):
        self.assert_round_trip(
            [
                ("sap", "sab4"),
                ("sat", "sad4"),
                ("sak", "sag4"),
                ("sah", "sah4"),
            ]
        )


if __name__ == "__main__":
    unittest.main()
