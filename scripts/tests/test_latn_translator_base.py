import unittest
from scripts.latn import create_translator


class TranslatorTestBase(unittest.TestCase):
    SOURCE_SYSTEM: str = ""
    TARGET_SYSTEM: str = ""

    @classmethod
    def setUpClass(cls):
        cls.forward = create_translator(cls.SOURCE_SYSTEM, cls.TARGET_SYSTEM)
        cls.reverse = create_translator(cls.TARGET_SYSTEM, cls.SOURCE_SYSTEM)

    def assert_round_trip(self, cases):
        for source, target in cases:
            with self.subTest(source=source):
                self.assertEqual(self.forward.translate(source), target)
                self.assertEqual(self.reverse.translate(target), source)
