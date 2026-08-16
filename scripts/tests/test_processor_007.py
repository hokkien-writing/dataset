import importlib
import unittest

from scripts.latn import create_translator

mod = importlib.import_module(
    "scripts.processors.007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect"
)
_normalize_puj = mod._normalize_puj
Processor = mod.Processor


class TestNormalizePuj(unittest.TestCase):
    def test_c_to_ts(self):
        cases = [
            ("ca", "tsa"),
            ("cí", "chí"),
            ("cîah", "chia̍h"),
            ("cṳ", "tsṳ"),
            ("co̤h", "tsoh"),
            ("cò̤", "tsò"),
        ]
        for book, expected in cases:
            with self.subTest(book=book):
                self.assertEqual(_normalize_puj(book), expected)

    def test_ch_to_chh(self):
        cases = [
            ("chut", "tshut"),
            ("châ", "tshâ"),
            ("cho̤", "tsho"),
            ("chéⁿ", "chhéⁿ"),
            ("chùi", "tshùi"),
        ]
        for book, expected in cases:
            with self.subTest(book=book):
                self.assertEqual(_normalize_puj(book), expected)

    def test_w_to_u(self):
        cases = [
            ("cẃn", "tsuán"),
            ("chŵn", "tshuân"),
            ("bw̄n", "buān"),
            ("che-kẁn", "chhe-kuàn"),
        ]
        for book, expected in cases:
            with self.subTest(book=book):
                self.assertEqual(_normalize_puj(book), expected)

    def test_breve_to_tilde(self):
        cases = [
            ("bĭ", "bĩ"),
            ("sĭm", "sĩm"),
            ("bŭ", "bũ"),
            ("hŭn", "hũn"),
            ("sĭ", "sĩ"),
            ("ṳ̆", "ṳ̃"),
            ("sĭen", "siẽn"),
        ]
        for book, expected in cases:
            with self.subTest(book=book):
                self.assertEqual(_normalize_puj(book), expected)

    def test_no_change(self):
        for text in ["a-hiaⁿ", "jī", "a"]:
            with self.subTest(text=text):
                self.assertEqual(_normalize_puj(text), text)

    def test_mixed_consonants(self):
        cases = [
            ("a-che", "a-chhe"),
            ("ci-ciaⁿ", "chi-chiaⁿ"),
            ("chut-ca", "tshut-tsa"),
        ]
        for book, expected in cases:
            with self.subTest(book=book):
                self.assertEqual(_normalize_puj(book), expected)


class TestBook007PujToLatnNorm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.translator = create_translator("PUJ", "LATN_NORM")

    def _assert(self, book_puj, expected_latn):
        normalized = _normalize_puj(book_puj)
        result = self.translator.translate(normalized).lower()
        self.assertEqual(result, expected_latn)

    def test_c_initial_unaspirated(self):
        self._assert("ca", "cha1")
        self._assert("cí", "chi2")
        self._assert("cîah", "chiah8")
        self._assert("cṳ", "chur1")

    def test_ch_initial_aspirated(self):
        self._assert("chut", "chhut4")
        self._assert("châ", "chha5")
        self._assert("cho̤", "chho1")

    def test_breve_tone6(self):
        self._assert("sĭm", "sim6")
        self._assert("bŭ", "bu6")
        self._assert("hŭn", "hun6")

    def test_o_vowel(self):
        self._assert("co̤h", "choh4")
        self._assert("hô̤", "ho5")
        self._assert("hô̤h", "hoh8")
        self._assert("bŏ̤", "bo6")

    def test_circumflex_tone8_entering(self):
        self._assert("pâk", "pak8")
        self._assert("sîh", "sih8")

    def test_w_to_u(self):
        self._assert("cẃn", "chuan2")
        self._assert("chŵn", "chhuan5")


class TestBook007Processor(unittest.TestCase):
    def test_csv_puj_has_standard_proofread_and_original_forms(self):
        text = (
            "<!-- page:26 -->\n"
            "- **亦** ā (1093|8|4)\n"
            "  - *ā-sĭ; īa-sĭ* — if; should it be; in case that; supposing that.\n"
            "  - *cò̤* — to do."
        )

        entries = Processor().extract_entries(text, "007")

        self.assertEqual(entries[1].puj, "ā-sĩ; iā-sĩ")
        self.assertEqual(entries[1].puj_proofread, "ā-sĭ; īa-sĭ")
        self.assertEqual(entries[1].puj_orig, "ā-sĭ; īa-sĭ")
        self.assertEqual(entries[2].puj, "tsò")
        self.assertEqual(entries[2].puj_proofread, "cò̤")
        self.assertEqual(entries[2].puj_orig, "cò̤")

    def test_first_glossed_example_inherits_headword_without_gloss(self):
        text = (
            "<!-- page:605 -->\n"
            "- **汪** uang (1043|85|4)\n"
            "  - *uang-îang* — a deep and wide expanse of water, the open sea.\n"
            "  - *cêk mō̤ⁿ uang-uang îang-îang* — nothing but an expanse of water to be seen."
        )

        entries = Processor().extract_entries(text, "007")

        self.assertEqual(entries[0].han, "汪")
        self.assertEqual(entries[0].puj, "uang")
        self.assertEqual(entries[0].en, "")
        self.assertEqual(entries[1].han, "汪")
        self.assertEqual(entries[1].puj, "uang-iâng")
        self.assertEqual(
            entries[1].en, "a deep and wide expanse of water, the open sea."
        )
        self.assertEqual(entries[2].han, "")

    def test_headword_reading_or_is_kept_as_slash_separated_single_entry(self):
        text = (
            "<!-- page:479 -->\n"
            "- **辦** phōiⁿ or pōiⁿ (652|160|9) — "
            "To manage, to attend to, to prepare, to provide, to go on with, "
            "to transact business; to act as a factor"
        )

        entries = Processor().extract_entries(text, "007")

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].han, "辦")
        self.assertEqual(entries[0].puj, "phōiⁿ/pōiⁿ")
        self.assertEqual(entries[0].puj_proofread, "phōiⁿ/pōiⁿ")
        self.assertEqual(entries[0].puj_orig, "phōiⁿ/pōiⁿ")
        self.assertEqual(
            entries[0].en,
            "To manage, to attend to, to prepare, to provide, to go on with, "
            "to transact business; to act as a factor",
        )


if __name__ == "__main__":
    unittest.main()
