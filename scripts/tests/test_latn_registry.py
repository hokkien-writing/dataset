import unittest
from scripts.latn.registry import ConverterRegistry
from scripts.latn.config import LatnSystemConfig
from scripts.latn.converter import LatnConverter

class TestLatnRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ConverterRegistry()
        self.config = LatnSystemConfig.from_simple_vowels(
            name="POJ",
            description="Test POJ",
            vowels={"a": "a á à a â ã ā a̍"}
        )

    def test_registration_and_creation(self):
        """Test that systems can be registered and converters created."""
        self.registry.register("POJ", self.config)
        
        # Test listing
        systems = self.registry.list_systems()
        self.assertIn("POJ", systems)
        
        # Test creation
        converter = self.registry.create_converter("poj")
        self.assertIsInstance(converter, LatnConverter)
        self.assertEqual(converter.config.name, "POJ")

    def test_unsupported_system(self):
        """Test error handling for unsupported system names."""
        with self.assertRaises(ValueError):
            self.registry.create_converter("UNKNOWN")

if __name__ == "__main__":
    unittest.main()
