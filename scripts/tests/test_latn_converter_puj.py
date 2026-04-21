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

    def test_entering_before_ending(self):
        """入聲標於韻尾前一個元音: tsuah8 → tsua̍h (標於 a, h 前)"""
        self.assert_round_trip(
            [
                ("tsuah8", "tsua̍h"),
                ("kuah8", "kua̍h"),
                ("kuaih8", "kuai̍h"),
                ("auh8", "au̍h"),
                ("ih8", "i̍h"),
                ("ueh8", "ue̍h"),
                ("oah8", "oa̍h"),
                ("mnh8", "mn̍h"),
                ("iuhnn8", "iu̍hⁿ"),
                ("ieh8", "ie̍h"),
                ("iah8", "ia̍h"),
                ("oih8", "oi̍h"),
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
        """鼻化 ⁿ：有声母标 u，无声母标 a"""
        self.assert_round_trip(
            [
                ("sinn1", "siⁿ"),
                ("sinn3", "sìⁿ"),
                ("sinn7", "sīⁿ"),
                ("tsuann1", "tsuaⁿ"),
                ("tsuann3", "tsùaⁿ"),  # vowel-initial: mark on a
                ("pinn5", "pîⁿ"),
                ("uann2", "uáⁿ"),  # vowel-initial: mark on a
                ("kuann5", "kûaⁿ"),  # consonant-initial: mark on u
                ("ainn2", "áiⁿ"),
                ("oinn2", "óiⁿ"),
                ("iunn2", "iúⁿ"),
            ]
        )

    def test_ua_bare(self):
        """ua（裸，無韻尾）→ 有聲母標 u，無聲母標 a"""
        self.assert_round_trip(
            [
                ("ua2", "uá"),
                ("ua3", "uà"),
                ("ua5", "uâ"),
                ("ua7", "uā"),
                ("kua2", "kúa"),
                ("hua2", "húa"),
            ]
        )

    def test_ua_with_ending(self):
        """ua + 韻尾 (i/n/ng) → 標於 a"""
        self.assert_round_trip(
            [
                ("uai2", "uái"),
                ("uai3", "uài"),
                ("uai5", "uâi"),
                ("kuai2", "kuái"),
                ("uan5", "uân"),
                ("kuan2", "kuán"),
                ("uang2", "uáng"),
                ("suang5", "suâng"),
            ]
        )

    def test_a_priority(self):
        """含 a 的複合韻 → 標於 a (a > o > u > e > i)，但 au 需區分有無聲母"""
        self.assert_round_trip(
            [
                ("ai2", "ái"),
                ("au2", "aú"),  # vowel-initial: mark on u (our discovery!)
                ("au5", "aû"),
                ("ia2", "iá"),
                ("iam2", "iám"),
                ("iang5", "iâng"),
                ("iap8", "ia̍p"),
                ("ia5", "iâ"),
                ("kau2", "káu"),  # consonant-initial: mark on a
            ]
        )

    def test_ie_series(self):
        """ie 系列 → 標於 e"""
        self.assert_round_trip(
            [
                ("ie2", "ié"),
                ("ie5", "iê"),
                ("kie5", "kiê"),
                ("ien2", "ién"),
                ("ie8", "ie̍"),
            ]
        )

    def test_dual_vowel_priority(self):
        """無 a 雙元音 → 有聲母標前元音，au/ua/ue 無聲母時標後元音"""
        self.assert_round_trip(
            [
                ("iu2", "iú"),
                ("ui2", "úi"),
                ("hue2", "húe"),  # consonant-initial: mark on u
                ("ou2", "óu"),
                ("oi2", "ói"),
                ("au2", "aú"),  # vowel-initial: mark on u
                ("ue2", "ué"),  # vowel-initial: mark on e
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
                ("lai5--lo7", "lâi--lō"),
            ]
        )


if __name__ == "__main__":
    unittest.main()
