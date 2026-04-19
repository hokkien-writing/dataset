import unittest
from scripts.tests.test_converter_base import ConverterTestBase


class TestBPConverter(ConverterTestBase):
    SYSTEM_NAME = "BP"

    def test_vowels(self):
        self.assert_round_trip(
            [
                ("a1", "ā"),
                ("a2", "ǎ"),
                ("a3", "à"),
                ("a5", "á"),
                ("a7", "â"),
                ("e1", "ē"),
                ("e2", "ě"),
                ("e3", "è"),
                ("e5", "é"),
                ("e7", "ê"),
                ("i1", "ī"),
                ("i2", "ǐ"),
                ("i3", "ì"),
                ("i5", "í"),
                ("i7", "î"),
                ("o1", "ō"),
                ("o2", "ǒ"),
                ("o3", "ò"),
                ("o5", "ó"),
                ("o7", "ô"),
                ("oo1", "ōo"),
                ("oo2", "ǒo"),
                ("oo3", "òo"),
                ("oo5", "óo"),
                ("oo7", "ôo"),
                ("u1", "ū"),
                ("u2", "ǔ"),
                ("u3", "ù"),
                ("u5", "ú"),
                ("u7", "û"),
                ("n2", "ň"),
                ("n3", "ǹ"),
                ("n5", "ń"),
                ("n7", "n̂"),
                ("m2", "m̌"),
                ("m3", "m̀"),
                ("m5", "ḿ"),
                ("m7", "m̂"),
            ]
        )

    def test_entering_disambiguation(self):
        self.assert_round_trip(
            [
                ("ah4", "āh"),
                ("ah8", "áh"),
                ("lak4", "lāk"),
                ("lak8", "lák"),
                ("tik4", "tīk"),
                ("tik8", "tík"),
                ("ek4", "ēk"),
                ("ek8", "ék"),
                ("it4", "īt"),
                ("it8", "ít"),
            ]
        )

    def test_syllables(self):
        self.assert_round_trip(
            [
                ("li2", "lǐ"),
                ("ca5", "cá"),
                ("pe7", "pê"),
                ("ku3", "kù"),
                ("tsi2", "tsǐ"),
                ("bang5", "báng"),
                ("leng7", "lêng"),
                ("lam5", "lám"),
                ("ku7", "kû"),
                ("su2", "sǔ"),
                ("bi5", "bí"),
            ]
        )

    def test_nasal_standalone(self):
        self.assert_round_trip(
            [
                ("ng7", "n̂g"),
                ("ng2", "ňg"),
                ("m2", "m̌"),
                ("m7", "m̂"),
                ("m5", "ḿ"),
            ]
        )

    def test_capitalization(self):
        self.assert_round_trip([("Li2", "Lǐ"), ("Ca5", "Cá")])

    def test_hyphenated(self):
        self.assert_round_trip([("bang5-lam5", "báng-lám")])


if __name__ == "__main__":
    unittest.main()
