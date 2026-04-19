import unittest
from scripts.latn.variants import get_variants


class TestPUJVariants(unittest.TestCase):
    def test_ur_variants(self):
        results = get_variants("sṳ", "PUJ")
        self.assertEqual(sorted(results), sorted(["sṳ", "su", "si"]))

    def test_t_to_k_ending(self):
        results = get_variants("sat", "PUJ")
        self.assertEqual(sorted(results), sorted(["sak"]))

    def test_oinn_variants(self):
        results = get_variants("soiⁿ", "PUJ")
        self.assertEqual(sorted(results), sorted(["soiⁿ", "saiⁿ"]))

    def test_combination_ur_and_t(self):
        results = get_variants("sṳt", "PUJ")
        self.assertEqual(
            sorted(results),
            sorted(["sṳk", "suk", "sik"]),
        )

    def test_sync_across_syllables(self):
        results = get_variants("sṳt-sṳt", "PUJ")
        self.assertEqual(
            sorted(results),
            sorted(["sṳk-sṳk", "suk-suk", "sik-sik"]),
        )

    def test_no_rules_returns_original(self):
        results = get_variants("sa", "PUJ")
        self.assertEqual(results, ["sa"])

    def test_n_to_ng_ending(self):
        results = get_variants("kan", "PUJ")
        self.assertEqual(sorted(results), sorted(["kang"]))


if __name__ == "__main__":
    unittest.main()
