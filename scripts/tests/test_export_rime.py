#!/usr/bin/env python3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.export_rime import (
    _load_merged_rows,
    load_entries,
    write_base_dict,
    write_system_dict,
    write_syllables_dict,
    write_schema,
    write_default_custom,
    generate_latn_norm_syllables,
    MERGED_CSV,
    PACKAGE_SYSTEMS,
)


def _load_test_rows():
    return _load_merged_rows(MERGED_CSV)


class TestExportRime(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def test_load_entries_dedup_with_counts(self):
        all_rows = _load_test_rows()
        entries, _ = load_entries(all_rows)
        self.assertTrue(len(entries) > 0)
        for (latn_norm, han), count in entries.items():
            self.assertTrue(latn_norm)
            self.assertTrue(han)
            self.assertGreaterEqual(count, 1)

    def test_load_entries_no_punctuation(self):
        all_rows = _load_test_rows()
        entries, _ = load_entries(all_rows)
        for (latn_norm, _), _ in entries.items():
            for ch in ",.?!\"'":
                self.assertNotIn(ch, latn_norm)

    def test_load_entries_max_syllables(self):
        all_rows = _load_test_rows()
        entries, _ = load_entries(all_rows)
        for (latn_norm, _), _ in entries.items():
            self.assertLessEqual(len(__import__("re").findall(r"\d", latn_norm)), 10)

    def test_load_entries_no_bracket_markers(self):
        all_rows = _load_test_rows()
        entries, _ = load_entries(all_rows)
        for (_, han), _ in entries.items():
            self.assertNotIn("[訓]", han)
            self.assertNotIn("[音]", han)

    def test_load_entries_variant_weights(self):
        all_rows = _load_test_rows()
        entries, _ = load_entries(all_rows)
        self.assertTrue(all(c >= 1 for c in entries.values()))

    def test_write_base_dict_format(self):
        entries = {("a1-bo2", "阿母"): 100, ("a1-bo5", "亞無"): 200}
        write_base_dict(entries, "hokkien", self.tmpdir)
        path = self.tmpdir / "hokkien.dict.yaml"
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("阿母\ta1  bo2\t100", content)
        self.assertIn("亞無\ta1  bo5\t200", content)
        self.assertIn("name: hokkien", content)

    def test_write_base_dict_hyphen_to_space(self):
        entries = {("a1-che2", "阿姐"): 100}
        write_base_dict(entries, "teochew", self.tmpdir)
        content = (self.tmpdir / "teochew.dict.yaml").read_text(encoding="utf-8")
        self.assertIn("a1  che2", content)
        self.assertNotIn("a1-che2", content)

    def test_write_syllables_dict_puj(self):
        entries = {("a1-bo2", "阿母"): 100}
        write_syllables_dict(entries, "puj", "teochew", self.tmpdir)
        path = self.tmpdir / "teochew_puj_syllables.dict.yaml"
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("name: teochew_puj_syllables", content)

    def test_write_system_dict_puj(self):
        entries = {("a1-bo2", "阿母"): 100}
        systems_data = {}
        write_system_dict(entries, systems_data, "puj", "teochew", self.tmpdir)
        path = self.tmpdir / "teochew_puj.dict.yaml"
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("name: teochew_puj", content)
        self.assertIn("import_tables:", content)

    def test_write_system_dict_all_systems(self):
        all_rows = _load_test_rows()
        entries, systems_data = load_entries(all_rows, require_systems=["puj", "dp"])
        for pkg, cfg in PACKAGE_SYSTEMS.items():
            for system in cfg["systems"]:
                write_system_dict(entries, systems_data, system, pkg, self.tmpdir)
                path = self.tmpdir / f"{pkg}_{system}.dict.yaml"
                self.assertTrue(path.exists(), f"Missing dict for {pkg}_{system}")

    def test_write_schema_puj(self):
        write_schema("puj", "teochew", self.tmpdir)
        path = self.tmpdir / "teochew_puj.schema.yaml"
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("schema_id: teochew_puj", content)

    def test_write_schema_all_systems(self):
        for pkg, cfg in PACKAGE_SYSTEMS.items():
            for system in cfg["systems"]:
                write_schema(system, pkg, self.tmpdir)
                path = self.tmpdir / f"{pkg}_{system}.schema.yaml"
                self.assertTrue(path.exists(), f"Missing schema for {pkg}_{system}")

    def test_write_default_custom(self):
        write_default_custom(["bp", "tl", "poj"], "hokkien", self.tmpdir)
        path = self.tmpdir / "default.custom.yaml"
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("hokkien_bp", content)
        self.assertIn("hokkien_tl", content)
        self.assertIn("hokkien_poj", content)

    def test_full_pipeline(self):
        all_rows = _load_test_rows()
        for pkg, cfg in PACKAGE_SYSTEMS.items():
            entries, systems_data = load_entries(
                all_rows, require_systems=cfg["require"]
            )
            if not entries:
                continue
            systems = cfg["systems"]
            pkg_dir = self.tmpdir / f"rime-{pkg}"
            pkg_dir.mkdir(parents=True, exist_ok=True)
            write_base_dict(entries, pkg, pkg_dir)
            for system in systems:
                write_syllables_dict(entries, system, pkg, pkg_dir)
                write_system_dict(entries, systems_data, system, pkg, pkg_dir)
                write_schema(system, pkg, pkg_dir)
            write_default_custom(systems, pkg, pkg_dir)

    def test_generate_syllables_no_mn_as_vowel(self):
        all_rows = _load_test_rows()
        entries, _ = load_entries(all_rows)
        syllables = generate_latn_norm_syllables(entries)
        for s in syllables:
            base = __import__("re").sub(r"\d$", "", s)
            if base.startswith(("pm", "nm", "bm", "bn")):
                self.fail(f"Invalid syllable with m/n as vowel: {s}")

    def test_generate_syllables_syllabic_nasals(self):
        all_rows = _load_test_rows()
        entries, _ = load_entries(all_rows)
        syllables = generate_latn_norm_syllables(entries)
        self.assertIn("m1", syllables)
        self.assertIn("ng1", syllables)

    def test_load_entries_require_systems(self):
        all_rows = _load_test_rows()
        teochew, _ = load_entries(all_rows, require_systems=["puj", "dp"])
        hokkien, _ = load_entries(all_rows, require_systems=["poj", "bp"])
        self.assertGreater(len(teochew), 0)
        self.assertGreater(len(hokkien), 0)


if __name__ == "__main__":
    unittest.main()
