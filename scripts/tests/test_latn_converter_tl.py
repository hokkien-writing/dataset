import unittest
from scripts.tests.test_converter_base import ConverterTestBase


class TestTLConverter(ConverterTestBase):
    SYSTEM_NAME = "TL"

    def test_vowels(self):
        self.assert_round_trip(
            [
                ("a1", "a"),
                ("a2", "á"),
                ("a3", "à"),
                ("a5", "â"),
                ("a6", "ǎ"),
                ("a7", "ā"),
                ("a8", "a̍"),
                ("e1", "e"),
                ("e2", "é"),
                ("e3", "è"),
                ("e5", "ê"),
                ("e6", "ě"),
                ("e7", "ē"),
                ("e8", "e̍"),
                ("i1", "i"),
                ("i2", "í"),
                ("i3", "ì"),
                ("i5", "î"),
                ("i6", "ǐ"),
                ("i7", "ī"),
                ("i8", "i̍"),
                ("o1", "o"),
                ("o2", "ó"),
                ("o3", "ò"),
                ("o5", "ô"),
                ("o6", "ǒ"),
                ("o7", "ō"),
                ("o8", "o̍"),
                ("oo1", "oo"),
                ("oo2", "óo"),
                ("oo3", "òo"),
                ("oo5", "ôo"),
                ("oo6", "ǒo"),
                ("oo7", "ōo"),
                ("oo8", "o̍o"),
                ("u1", "u"),
                ("u2", "ú"),
                ("u3", "ù"),
                ("u5", "û"),
                ("u6", "ǔ"),
                ("u7", "ū"),
                ("u8", "u̍"),
                ("n1", "n"),
                ("n2", "ń"),
                ("n3", "ǹ"),
                ("n5", "n̂"),
                ("n6", "n\u0303"),
                ("n7", "n̄"),
                ("n8", "n̍"),
                ("m1", "m"),
                ("m2", "ḿ"),
                ("m3", "m̀"),
                ("m5", "m̂"),
                ("m6", "m̃"),
                ("m7", "m̄"),
                ("m8", "m̍"),
            ]
        )

    def test_syllables(self):
        self.assert_round_trip(
            [
                ("li2", "lí"),
                ("tsha5", "tshâ"),
                ("pe7", "pē"),
                ("ku3", "kù"),
                ("tsi2", "tsí"),
                ("bong5", "bông"),
                ("leng7", "lēng"),
                ("lam5", "lâm"),
                ("ku7", "kū"),
                ("su2", "sú"),
                ("bi5", "bî"),
            ]
        )

    def test_syllables_oo(self):
        self.assert_round_trip(
            [
                ("oo1", "oo"),
                ("moo5", "môo"),
                ("soo7", "sōo"),
                ("koo2", "kóo"),
                ("phoo3", "phòo"),
            ]
        )

    def test_entering(self):
        self.assert_round_trip(
            [
                ("ah4", "ah"),
                ("ah8", "a̍h"),
                ("lak4", "lak"),
                ("lak8", "la̍k"),
                ("tik4", "tik"),
                ("tik8", "ti̍k"),
                ("tsap4", "tsap"),
                ("tsap8", "tsa̍p"),
            ]
        )

    def test_nasal_standalone(self):
        self.assert_round_trip(
            [
                ("ng7", "n̄g"),
                ("ng2", "ńg"),
                ("ng5", "n̂g"),
                ("m2", "ḿ"),
                ("m7", "m̄"),
                ("m5", "m̂"),
            ]
        )

    def test_nasalization(self):
        self.assert_round_trip(
            [
                ("sinn1", "siⁿ"),
                ("sinn3", "sìⁿ"),
                ("sinn7", "sīⁿ"),
                ("chuann1", "chuaⁿ"),
                ("chuann3", "chuàⁿ"),
            ]
        )

    def test_capitalization(self):
        self.assert_round_trip([("Li2", "Lí"), ("Tsha5", "Tshâ")])

    def test_hyphenated(self):
        self.assert_round_trip([("tai5-lam5", "tâi-lâm")])


if __name__ == "__main__":
    unittest.main()
