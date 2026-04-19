import unittest
from scripts.tests.test_converter_base import ConverterTestBase


class TestDPConverter(ConverterTestBase):
    SYSTEM_NAME = "DP"

    def test_vowels(self):
        self.assert_round_trip(
            [(f"a{t}", f"a{t}") for t in range(1, 9)]
            + [(f"e{t}", f"e{t}") for t in range(1, 9)]
            + [(f"ê{t}", f"ê{t}") for t in range(1, 9)]
            + [(f"i{t}", f"i{t}") for t in range(1, 9)]
            + [(f"o{t}", f"o{t}") for t in range(1, 9)]
            + [(f"u{t}", f"u{t}") for t in range(1, 9)]
        )

    def test_e_vs_e_circumflex(self):
        self.assertNotEqual(
            self.converter.to_keyboard("ê5"),
            self.converter.to_keyboard("e5"),
        )

    def test_syllables(self):
        self.assert_round_trip(
            [
                ("diang5", "diang5"),
                ("zung1", "zung1"),
                ("huêng5", "huêng5"),
                ("lo6", "lo6"),
                ("bhung7", "bhung7"),
                ("ziah8", "ziah8"),
                ("ghu3", "ghu3"),
                ("cê5", "cê5"),
                ("ri5", "ri5"),
            ]
        )

    def test_entering(self):
        self.assert_round_trip(
            [
                ("ab4", "ab4"),
                ("ad4", "ad4"),
                ("ag4", "ag4"),
                ("ah4", "ah4"),
                ("ab8", "ab8"),
                ("ad8", "ad8"),
                ("ag8", "ag8"),
                ("ah8", "ah8"),
                ("ziab4", "ziab4"),
                ("lod4", "lod4"),
                ("bhag4", "bhag4"),
            ]
        )

    def test_capitalization(self):
        self.assertEqual(self.converter.to_handwriting("Diang5"), "Diang5")

    def test_hyphenated(self):
        self.assert_round_trip([("diang5-huêng5", "diang5-huêng5")])


if __name__ == "__main__":
    unittest.main()
