import unittest
from scripts.latn import create_converter


class ConverterTestBase(unittest.TestCase):
    SYSTEM_NAME: str = ""

    @classmethod
    def setUpClass(cls):
        cls.converter = create_converter(cls.SYSTEM_NAME)

    def assert_round_trip(self, cases):
        """Assert kb→hw and hw→kb for each (keyboard, handwriting) pair."""
        for kb, hw in cases:
            with self.subTest(kb=kb):
                self.assertEqual(self.converter.to_handwriting(kb), hw)
                self.assertEqual(self.converter.to_keyboard(hw), kb)
