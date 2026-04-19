import unittest
from scripts.tests.test_latn_translator_base import TranslatorTestBase


class TestPOJToBP(TranslatorTestBase):
    SOURCE_SYSTEM = "POJ"
    TARGET_SYSTEM = "BP"

    def test_initials(self):
        self.assert_round_trip(
            [
                ("pâng", "báng"),
                ("phâng", "páng"),
                ("bâng", "bbáng"),
                ("tâng", "dáng"),
                ("thâng", "táng"),
                ("kâng", "gáng"),
                ("khâng", "káng"),
                ("gâng", "ggáng"),
                ("châng", "záng"),
                ("chhâng", "cáng"),
                ("jâng", "zzáng"),
                ("sâng", "sáng"),
                ("hâng", "háng"),
                ("lâng", "láng"),
                ("mâng", "bbnáng"),
                ("nâng", "lnáng"),
                ("ngâng", "ggnáng"),
            ]
        )

    def test_vowels(self):
        self.assert_round_trip(
            [
                ("o͘", "ōo"),
                ("ó͘", "ǒo"),
                ("ò͘", "òo"),
                ("o̍͘k", "óok"),
            ]
        )

    def test_nasal_endings(self):
        self.assert_round_trip(
            [
                ("kam", "gām"),
                ("kan", "gān"),
                ("kang", "gāng"),
                ("kham", "kām"),
                ("khan", "kān"),
                ("khang", "kāng"),
            ]
        )

    def test_entering_endings(self):
        self.assert_round_trip(
            [
                ("ka̍p", "gáp"),
                ("ka̍t", "gát"),
                ("ka̍k", "gák"),
                ("ka̍h", "gáh"),
            ]
        )

    def test_sentences(self):
        self.assert_round_trip(
            [
                ("ha̍k-sing", "hák-sīng"),
                ("lán-lâng", "lǎn-láng"),
            ]
        )


if __name__ == "__main__":
    unittest.main()
