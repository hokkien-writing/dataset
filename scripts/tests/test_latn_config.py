import unittest
from scripts.latn.config import LatnSystemConfig

class TestLatnConfig(unittest.TestCase):
    def test_simple_vowels_expansion(self):
        """Test that from_simple_vowels correctly expands space-separated strings."""
        config = LatnSystemConfig.from_simple_vowels(
            name="TEST",
            description="Test System",
            vowels={
                "a": "a á à a â ã ā a̍",
                "oo": "o͘ ó͘ ò͘ o͘ ô͘ õ͘ ō͘ o̍͘"
            }
        )
        
        # Check tone 2 (á)
        self.assertEqual(config.vowel_dict["a2"], "á")
        # Check tone 8 (a̍)
        self.assertEqual(config.vowel_dict["a8"], "a̍")
        # Check multi-char base vowel (oo) tone 2 (ó͘)
        self.assertEqual(config.vowel_dict["oo2"], "ó͘")
        
    def test_reverse_mapping_sorting(self):
        """Test that reverse mapping is sorted by key length descending."""
        config = LatnSystemConfig.from_simple_vowels(
            name="TEST",
            description="Test System",
            vowels={
                "o": "o ó ò o ô õ ō o̍",
                "oo": "o͘ ó͘ ò͘ o͘ ô͘ õ͘ ō͘ o̍͘"
            }
        )
        
        # reverse_vowel_map keys should have 'o͘' (length 2) before 'o' (length 1)
        keys = list(config.reverse_vowel_map.keys())
        idx_oo = -1
        idx_o = -1
        for i, k in enumerate(keys):
            if k == "o͘": # o + combining dot
                idx_oo = i
            elif k == "o":
                idx_o = i
        
        self.less_than(idx_oo, idx_o, "Multi-character marked vowel should come first in reverse map")

    def less_than(self, a, b, msg=None):
        if not a < b:
            self.fail(msg or f"{a} is not less than {b}")

if __name__ == "__main__":
    unittest.main()
