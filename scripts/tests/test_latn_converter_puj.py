import unittest
from scripts.tests.test_converter_base import ConverterTestBase


class TestPUJConverter(ConverterTestBase):
    SYSTEM_NAME = "PUJ"

    def test_vowels(self):
        self.assert_round_trip(
            [
                ("a1", "a"),
                ("a2", "á"),
                ("a3", "à"),
                ("a5", "â"),
                ("a6", "ã"),
                ("a7", "ā"),
                ("a8", "a̍"),
                ("e1", "e"),
                ("e2", "é"),
                ("e3", "è"),
                ("e5", "ê"),
                ("e6", "ẽ"),
                ("e7", "ē"),
                ("e8", "e̍"),
                ("i1", "i"),
                ("i2", "í"),
                ("i3", "ì"),
                ("i5", "î"),
                ("i6", "ĩ"),
                ("i7", "ī"),
                ("i8", "i̍"),
                ("o1", "o"),
                ("o2", "ó"),
                ("o3", "ò"),
                ("o5", "ô"),
                ("o6", "õ"),
                ("o7", "ō"),
                ("o8", "o̍"),
                ("u1", "u"),
                ("u2", "ú"),
                ("u3", "ù"),
                ("u5", "û"),
                ("u6", "ũ"),
                ("u7", "ū"),
                ("u8", "u̍"),
                ("ur1", "ṳ"),
                ("ur2", "ṳ́"),
                ("ur3", "ṳ̀"),
                ("ur5", "ṳ̂"),
                ("ur6", "ṳ̃"),
                ("ur7", "ṳ̄"),
                ("ur8", "ṳ̍"),
                ("n1", "n"),
                ("n2", "ń"),
                ("n3", "ǹ"),
                ("n5", "n̂"),
                ("n6", "ñ"),
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
                ("tsa5", "tsâ"),
                ("pe7", "pē"),
                ("ku3", "kù"),
                ("chhi2", "chhí"),
                ("bung5", "bûng"),
                ("leng7", "lēng"),
                ("lam5", "lâm"),
                ("ku7", "kū"),
                ("su2", "sú"),
                ("bi5", "bî"),
                ("jip8", "ji̍p"),
                ("he2", "hé"),
                ("go5", "gô"),
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
                ("phah4", "phah"),
                ("phah8", "pha̍h"),
            ]
        )

    def test_nasal_standalone(self):
        self.assert_round_trip(
            [
                ("ng7", "n̄g"),
                ("ng2", "ńg"),
                ("ng5", "n̂g"),
                ("ng3", "ǹg"),
                ("ng6", "ñg"),
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
                ("tsuann1", "tsuaⁿ"),
                ("tsuann3", "tsuàⁿ"),
                ("pinn5", "pîⁿ"),
            ]
        )

    def test_ur_syllables(self):
        self.assert_round_trip(
            [
                ("kur5", "kṳ̂"),
                ("tur2", "tṳ́"),
                ("sur7", "sṳ̄"),
                ("tsur3", "tsṳ̀"),
            ]
        )

    def test_capitalization(self):
        self.assert_round_trip([("Li2", "Lí"), ("Tsa5", "Tsâ")])

    def test_hyphenated(self):
        self.assert_round_trip(
            [
                ("Peh8-ue7-ji7", "Pe̍h-uē-jī"),
                ("lai5--lo7", "lâi--lō")
            ]
        )


if __name__ == "__main__":
    unittest.main()
