import unittest
from scripts.latn.config import PhoneticMapping
from scripts.latn.systems.poj import create_config as create_poj_config
from scripts.latn.systems.puj import create_config as create_puj_config
from scripts.latn.converter import LatnConverter
from scripts.latn.translator import LatnTranslator

class TestLatnTranslator(unittest.TestCase):
    def setUp(self):
        self.source_conv = LatnConverter(create_poj_config())
        self.target_conv = LatnConverter(create_puj_config())
        
        # User defined rules: POJ -> PUJ
        # oo -> ou, oa -> ua, oe -> ue
        # tsh/chh logic: chh -> tsh if NOT before i/e
        self.mapping = PhoneticMapping(
            vowel_map={
                "oo": "ou",
                "oa": "ua",
                "oe": "ue"
            },
            conversion_rules=[
                (r"^chh(?![ie])", "tsh"),
                (r"^ch(?![hie])", "ts"),
            ]
        )
        self.translator = LatnTranslator(self.source_conv, self.target_conv, self.mapping)

    def test_basic_translation(self):
        """Test simple vowel group replacements while preserving tones."""
        # 1. oo -> ou (POJ o͘ -> PUJ ou)
        # POJ o͘ (oo1) -> PUJ ou (ou1)
        self.assertEqual(self.translator.translate("o͘"), "ou")
        self.assertEqual(self.translator.translate("ó͘"), "óu") # Tone 2
        
        # 2. oa -> ua
        self.assertEqual(self.translator.translate("oá"), "uá")
        
        # 3. oe -> ue
        self.assertEqual(self.translator.translate("oē"), "uē")

    def test_consonant_conditional_mapping(self):
        """Test contextual mapping for chh/tsh and ch/ts."""
        # chh before 'i' should remain 'chh'
        self.assertEqual(self.translator.translate("chhí"), "chhí")
        # chh before other vowels (like 'a') should become 'tsh'
        self.assertEqual(self.translator.translate("chhá"), "tshá")
        
        # ch before 'i' should remain 'ch'
        self.assertEqual(self.translator.translate("chì"), "chì")
        # ch before others should become 'ts'
        self.assertEqual(self.translator.translate("cha"), "tsa")

    def test_complex_sentence(self):
        """Test translation of a full string with multiple markers."""
        source = "o͘-oá-oē"
        expected = "ou-uá-uē"
        self.assertEqual(self.translator.translate(source), expected)

if __name__ == "__main__":
    unittest.main()
