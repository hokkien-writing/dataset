import unittest
from scripts.tests.test_latn_translator_base import TranslatorTestBase


class TestPUJToDP(TranslatorTestBase):
    SOURCE_SYSTEM = "PUJ"
    TARGET_SYSTEM = "DP"

    def test_initials(self):
        self.assert_round_trip(
            [
                ("pang", "bang¹"),
                ("phang", "pang¹"),
                ("bang", "bhang¹"),
                ("tang", "dang¹"),
                ("thang", "tang¹"),
                ("kang", "gang¹"),
                ("khang", "kang¹"),
                ("gang", "ghang¹"),
                ("tsang", "zang¹"),
                ("tshang", "cang¹"),
                ("chin", "zin¹"),
                ("chhim", "cim¹"),
                ("sang", "sang¹"),
                ("hang", "hang¹"),
                ("lang", "lang¹"),
                ("mang", "mang¹"),
                ("nang", "nang¹"),
                ("ngang", "ngang¹"),
            ]
        )

    def test_vowels(self):
        self.assert_round_trip(
            [
                ("sa", "sa¹"),
                ("sê", "sê⁵"),
                ("si", "si¹"),
                ("so", "so¹"),
                ("su", "su¹"),
                ("sṳ", "se¹"),
            ]
        )

    def test_nasal_endings(self):
        self.assert_round_trip(
            [
                ("sam", "sam¹"),
                ("san", "san¹"),
                ("sang", "sang¹"),
            ]
        )

    def test_entering_endings(self):
        self.assert_round_trip(
            [
                ("sap", "sab⁴"),
                ("sat", "sad⁴"),
                ("sak", "sag⁴"),
                ("sah", "sah⁴"),
            ]
        )


if __name__ == "__main__":
    unittest.main()
