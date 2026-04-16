import unittest
from scripts.tests.test_converter_base import ConverterTestBase


class TestPOJConverter(ConverterTestBase):
    SYSTEM_NAME = "POJ"

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
                ("oo1", "o͘"),
                ("oo2", "ó͘"),
                ("oo3", "ò͘"),
                ("oo5", "ô͘"),
                ("oo6", "õ͘"),
                ("oo7", "ō͘"),
                ("oo8", "o̍͘"),
                ("u1", "u"),
                ("u2", "ú"),
                ("u3", "ù"),
                ("u5", "û"),
                ("u6", "ũ"),
                ("u7", "ū"),
                ("u8", "u̍"),
                ("ui1", "ui"),
                ("ui2", "uí"),
                ("ui3", "uì"),
                ("ui5", "uî"),
                ("ui6", "uĩ"),
                ("ui7", "uī"),
                ("ui8", "ui̍"),
                ("iu1", "iu"),
                ("iu2", "iú"),
                ("iu3", "iù"),
                ("iu5", "iû"),
                ("iu6", "iũ"),
                ("iu7", "iū"),
                ("iu8", "iu̍"),
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
                ("cha5", "châ"),
                ("pe7", "pē"),
                ("ku3", "kù"),
                ("chhi2", "chhí"),
                ("cheng5", "chêng"),
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
                ("oo1", "o͘"),
                ("moo5", "mô͘"),
                ("soo7", "sō͘"),
                ("koo2", "kó͘"),
                ("phoo3", "phò͘"),
            ]
        )

    def test_syllables_ui(self):
        self.assert_round_trip(
            [
                ("tui3", "tuì"),
                ("hui5", "huî"),
                ("chui7", "chuī"),
                ("sui2", "suí"),
            ]
        )

    def test_syllables_iu(self):
        self.assert_round_trip(
            [
                ("chiu5", "chiû"),
                ("giu2", "giú"),
                ("liu7", "liū"),
                ("siu3", "siù"),
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
                ("chap4", "chap"),
                ("chap8", "cha̍p"),
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
        self.assert_round_trip([("Li2", "Lí"), ("Cha5", "Châ")])

    def test_hyphenated(self):
        self.assert_round_trip([("peh8-oe7-ji7", "pe̍h-oē-jī")])


if __name__ == "__main__":
    unittest.main()
