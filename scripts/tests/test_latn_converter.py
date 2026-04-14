import unittest
from scripts.latn.config import LatnSystemConfig
from scripts.latn.converter import LatnConverter

class TestLatnConverter(unittest.TestCase):
    def setUp(self):
        # Generic config for testing
        self.config = LatnSystemConfig.from_simple_vowels(
            name="TEST",
            description="Test system",
            vowels={
                "a": "a á à a â ã ā a̍",
                "oo": "o͘ ó͘ ò͘ o͘ ô͘ õ͘ ō͘ o̍͘"
            },
            tone_mark_priority=["a", "oo"],
            syllable_mappings={"ⁿ": "nn"}
        )
        self.converter = LatnConverter(self.config)

    def test_to_keyboard_tones(self):
        """Test basic tone detection in handwriting to keyboard conversion."""
        self.assertEqual(self.converter.to_keyboard("á"), "a2")
        self.assertEqual(self.converter.to_keyboard("a̍"), "a8")

    def test_to_handwriting_tones(self):
        """Test basic tone marking in keyboard to handwriting conversion."""
        self.assertEqual(self.converter.to_handwriting("a2"), "á")
        self.assertEqual(self.converter.to_handwriting("a8"), "a̍")

    def test_multi_char_vowel_oo(self):
        """Test multi-character vowel (o͘) handling."""
        # To keyboard
        self.assertEqual(self.converter.to_keyboard("o͘"), "oo1")
        self.assertEqual(self.converter.to_keyboard("ó͘"), "oo2")
        
        # To handwriting
        self.assertEqual(self.converter.to_handwriting("oo1"), "o͘")
        self.assertEqual(self.converter.to_handwriting("oo2"), "ó͘")

    def test_nasalization_mapping(self):
        """Test syllable mappings like ⁿ <-> nn."""
        self.assertEqual(self.converter.to_keyboard("siⁿ"), "sinn1")
        self.assertEqual(self.converter.to_handwriting("sinn1"), "siⁿ")

    def test_entering_tone_detection(self):
        """Test that tone 4 is inferred for entering endings."""
        # 'ah' should be tone 4, even if unmarked
        self.assertEqual(self.converter.to_keyboard("ah"), "ah4")
        self.assertEqual(self.converter.to_keyboard("a̍h"), "ah8")
        
        # 'a' should still be tone 1
        self.assertEqual(self.converter.to_keyboard("a"), "a1")

if __name__ == "__main__":
    unittest.main()
