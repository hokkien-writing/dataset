import unittest
from scripts.latn.systems import register_default_systems, get_system_module
from scripts.latn.registry import LatnRegistry

SYSTEMS = ["poj", "puj", "tl", "bp", "dp"]


class TestSystemModules(unittest.TestCase):
    def test_all_modules_have_required_functions(self):
        for name in SYSTEMS:
            mod = get_system_module(name)
            self.assertTrue(hasattr(mod, "SYSTEM_NAME"), f"{name} missing SYSTEM_NAME")
            self.assertTrue(hasattr(mod, "create_config"), f"{name} missing create_config")
            self.assertTrue(hasattr(mod, "create_latn_norm_mapping"), f"{name} missing create_latn_norm_mapping")
            self.assertTrue(hasattr(mod, "create_reverse_mapping"), f"{name} missing create_reverse_mapping")
            self.assertTrue(hasattr(mod, "create_rime_algebra"), f"{name} missing create_rime_algebra")

    def test_system_name_matches(self):
        for name in SYSTEMS:
            mod = get_system_module(name)
            self.assertEqual(mod.SYSTEM_NAME, name.upper())

    def test_rime_algebra_returns_list(self):
        for name in SYSTEMS:
            mod = get_system_module(name)
            algebra = mod.create_rime_algebra()
            self.assertIsInstance(algebra, list)
            self.assertTrue(len(algebra) > 0)
            for rule in algebra:
                self.assertIsInstance(rule, str)

    def test_mapping_round_trip(self):
        registry = LatnRegistry()
        register_default_systems(registry)
        for name in SYSTEMS:
            mod = get_system_module(name)
            fwd = mod.create_latn_norm_mapping()
            rev = mod.create_reverse_mapping()
            self.assertIsNotNone(fwd)
            self.assertIsNotNone(rev)


if __name__ == "__main__":
    unittest.main()
