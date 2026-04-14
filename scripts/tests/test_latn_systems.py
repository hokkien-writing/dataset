import unittest
from scripts.latn.systems.poj import create_config as create_poj_config
from scripts.latn.systems.puj import create_config as create_puj_config
from scripts.latn.converter import LatnConverter

class TestLatnSystems(unittest.TestCase):
    def test_poj_system_logic(self):
        """Integration test for POJ system configuration."""
        config = create_poj_config()
        converter = LatnConverter(config)
        
        # Test oo cluster (literal o͘)
        self.assertEqual(converter.to_keyboard("o͘"), "oo1")
        self.assertEqual(converter.to_handwriting("oo2"), "ó͘")
        
        # Test nasalization
        self.assertEqual(converter.to_keyboard("siⁿ"), "sinn1")
        self.assertEqual(converter.to_handwriting("sinn1"), "siⁿ")

    def test_puj_system_logic(self):
        """Integration test for PUJ system configuration."""
        config = create_puj_config()
        converter = LatnConverter(config)
        
        # Test ur cluster
        self.assertEqual(converter.to_keyboard("ṳ"), "ur1")
        self.assertEqual(converter.to_handwriting("ur2"), "ṳ́")
        
        # Test entering tone inference
        self.assertEqual(converter.to_keyboard("ṳ̍h"), "urh8")
        self.assertEqual(converter.to_handwriting("urh8"), "ṳ̍h")

if __name__ == "__main__":
    unittest.main()
