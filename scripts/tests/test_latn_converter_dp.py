import unittest
from scripts.tests.test_converter_base import ConverterTestBase


class TestDPConverter(ConverterTestBase):
    SYSTEM_NAME = "DP"

    def test_vowels(self):
        s = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
        self.assert_round_trip(
            [(f"a{t}", f"a{str(t).translate(s)}") for t in range(1, 9)]
            + [(f"e{t}", f"e{str(t).translate(s)}") for t in range(1, 9)]
            + [(f"ê{t}", f"ê{str(t).translate(s)}") for t in range(1, 9)]
            + [(f"i{t}", f"i{str(t).translate(s)}") for t in range(1, 9)]
            + [(f"o{t}", f"o{str(t).translate(s)}") for t in range(1, 9)]
            + [(f"u{t}", f"u{str(t).translate(s)}") for t in range(1, 9)]
        )

    def test_e_vs_e_circumflex(self):
        self.assertNotEqual(
            self.converter.to_keyboard("ê⁵"),
            self.converter.to_keyboard("e⁵"),
        )

    def test_syllables(self):
        self.assert_round_trip(
            [
                ("diang5", "diang⁵"),
                ("zung1", "zung¹"),
                ("huêng5", "huêng⁵"),
                ("lo6", "lo⁶"),
                ("bhung7", "bhung⁷"),
                ("ziah8", "ziah⁸"),
                ("ghu3", "ghu³"),
                ("cê5", "cê⁵"),
                ("ri5", "ri⁵"),
            ]
        )

    def test_entering(self):
        self.assert_round_trip(
            [
                ("ab4", "ab⁴"),
                ("ad4", "ad⁴"),
                ("ag4", "ag⁴"),
                ("ah4", "ah⁴"),
                ("ab8", "ab⁸"),
                ("ad8", "ad⁸"),
                ("ag8", "ag⁸"),
                ("ah8", "ah⁸"),
                ("ziab4", "ziab⁴"),
                ("lod4", "lod⁴"),
                ("bhag4", "bhag⁴"),
            ]
        )

    def test_capitalization(self):
        self.assertEqual(self.converter.to_handwriting("Diang5"), "Diang⁵")

    def test_hyphenated(self):
        self.assert_round_trip([("diang5-huêng5", "diang⁵-huêng⁵")])

    def test_nasalized(self):
        self.assert_round_trip(
            [
                ("uann3", "uaⁿ³"),
                ("inn5", "iⁿ⁵"),
            ]
        )


if __name__ == "__main__":
    unittest.main()
