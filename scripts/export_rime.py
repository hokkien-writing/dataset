#!/usr/bin/env python3
"""Export Rime input schema files from merged.csv."""

import csv
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.latn import create_translator, create_converter

MERGED_CSV = PROJECT_ROOT / "export" / "merged.csv"
OUTPUT_DIR = PROJECT_ROOT / "export" / "rime"

PACKAGE_SYSTEMS = {
    "hokkien": {
        "systems": ["bp", "tl", "poj"],
        "require": ["poj", "bp"],
    },
    "teochew": {
        "systems": ["puj", "dp"],
        "require": ["puj", "dp"],
    },
}

SYSTEM_NAMES = {
    "poj": "閩南語・白話字",
    "tl": "閩南語・台羅",
    "bp": "閩南語・閩南話拼音",
    "puj": "潮州語・白話字",
    "dp": "潮州語・潮州話拼音",
}


def load_entries(csv_path: Path, require_systems: Optional[list] = None):
    """Load and deduplicate entries from merged.csv.

    Returns: dict of (latn_norm, han) -> weight (int)
    Base weight per occurrence: 100. Variants: 50, 25, 12, ...

    require_systems: if set, only include rows where at least one of these
    system columns has a non-empty value (e.g. ["puj", "dp"] for teochew).
    """
    counts = Counter()
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            latn_norm = (row.get("latn_norm") or "").strip()
            han = (row.get("han") or "").strip()
            han_variants = (row.get("han_variants") or "").strip()
            if not latn_norm or not han:
                continue
            if re.search(r'[,.?!"\']', latn_norm):
                continue
            syllable_count = len(re.findall(r"\d", latn_norm))
            if syllable_count > 10:
                continue
            if require_systems:
                if not any((row.get(s) or "").strip() for s in require_systems):
                    continue
            clean_han = re.sub(r"\[[^\]]*\]", "", han)
            if clean_han:
                counts[(latn_norm, clean_han)] += 100
            if han_variants:
                w = 100
                for variant in han_variants.split("|"):
                    v = variant.strip()
                    if v:
                        clean_v = re.sub(r"\[[^\]]*\]", "", v)
                        if clean_v:
                            w = w // 2
                            if w > 0:
                                counts[(latn_norm, clean_v)] += w
    return counts


def write_base_dict(entries: dict, pkg: str, output_dir: Path):
    """Write {pkg}.dict.yaml (latn_norm -> han with weights)."""
    lines = [
        f"# Rime dictionary: {pkg}",
        "# Generated from merged.csv - do not edit manually",
        "---",
        f"name: {pkg}",
        'version: "0.1"',
        "sort: by_weight",
        "...",
        "",
    ]
    for (latn_norm, han), count in sorted(entries.items()):
        code = latn_norm.replace("-", " ")
        lines.append(f"{han}\t{code}\t{count}")
    path = output_dir / f"{pkg}.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {path}")


SYSTEM_ALGEBRA = {
    "puj": [
        "derive/-/ /",
        "derive/[1-8]//",
        "xform/tsh/chh/",
        "xform/ts/ch/",
    ],
    "poj": [
        "derive/-/ /",
        "derive/[1-8]//",
        "xform/oo/ou/",
        "xform/oa/ua/",
        "xform/oe/ue/",
    ],
    "tl": [
        "derive/-/ /",
        "derive/[1-8]//",
        "xform/ts/ch/",
        "xform/tsh/chh/",
    ],
    "bp": [
        "derive/-/ /",
        "derive/[1-8]//",
        "xform/bb/p/",
        "xform/gg/k/",
        "xform/dd/t/",
        "xform/ggn/ng/",
        "xform/bbn/m/",
        "xform/ln/n/",
        "xform/b/p/",
        "xform/p/ph/",
        "xform/g/k/",
        "xform/k/kh/",
        "xform/d/t/",
        "xform/t/th/",
        "xform/z/ch/",
        "xform/c/chh/",
        "xform/zz/j/",
        "xform/oo/ou/",
    ],
    "dp": [
        "derive/-/ /",
        "derive/[1-8]//",
        "xform/bh/b/",
        "xform/gh/g/",
        "xform/b/p/",
        "xform/p/ph/",
        "xform/d/t/",
        "xform/t/th/",
        "xform/g/k/",
        "xform/k/kh/",
        "xform/z/ch/",
        "xform/c/chh/",
        "xform/r/j/",
        "xform/nn$/nn/",
        "xform/^e(?!$)/ur/",
        "derive/ê/e/",
    ],
}

SCHEMA_TEMPLATE = """\
# Rime schema: {schema_id}
# Generated from merged.csv - do not edit manually

schema:
  schema_id: {schema_id}
  name: {name}
  version: "0.1"
  author:
    - Hokkien Writing Project

engine:
  processors:
    - ascii_composer
    - speller
    - punctuator
    - selector
    - navigator
    - express_editor
  segmentors:
    - abc_segmentor
    - punct_segmentor
    - fallback_segmentor
  translators:
    - script_translator
    - script_translator@latn
  filters:
    - uniquifier

speller:
  alphabet: zyxwvutsrqponmlkjihgfedba12345678-
  algebra:
{algebra}

translator:
  dictionary: {pkg}

latn:
  dictionary: {latn_dict}
  enable_completion: true
"""

DEFAULT_CUSTOM_TEMPLATE = """\
# Rime default settings customization
# Generated from merged.csv - do not edit manually

patch:
  schema_list:
{schema_list}
"""


def write_latn_dict(entries: dict, system: str, pkg: str, output_dir: Path):
    """Write {pkg}_{system}_latn.dict.yaml (romanization output dictionary).

    Aggregates by latn_norm so variants don't create duplicates.
    """
    translator = create_translator("LATN_NORM", system.upper())

    latn_weights = Counter()
    for (latn_norm, _han), weight in entries.items():
        latn_weights[latn_norm] += weight

    lines = [
        f"# Rime dictionary: {pkg}_{system}_latn",
        "# Generated from merged.csv - do not edit manually",
        "---",
        f"name: {pkg}_{system}_latn",
        'version: "0.1"',
        "sort: by_weight",
        "...",
        "",
    ]

    for latn_norm, weight in sorted(latn_weights.items()):
        code = latn_norm.replace("-", " ")
        try:
            handwriting = translator.translate(latn_norm.replace("-", " "))
            romanized = handwriting.replace(" ", "-")
        except Exception:
            continue
        if not romanized.strip():
            continue
        lines.append(f"{romanized}\t{code}\t{weight}")

    path = output_dir / f"{pkg}_{system}_latn.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def format_algebra(rules: list) -> str:
    return "\n".join(f"    - {r}" for r in rules)


def write_schema(system: str, pkg: str, output_dir: Path):
    """Write {pkg}_{system}.schema.yaml."""
    schema_id = f"{pkg}_{system}"
    name = SYSTEM_NAMES[system]
    latn_dict = f"{pkg}_{system}_latn"
    algebra = format_algebra(SYSTEM_ALGEBRA[system])

    content = SCHEMA_TEMPLATE.format(
        schema_id=schema_id,
        name=name,
        algebra=algebra,
        latn_dict=latn_dict,
        pkg=pkg,
    )
    path = output_dir / f"{schema_id}.schema.yaml"
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")


def write_default_custom(systems: list, pkg: str, output_dir: Path):
    """Write default.custom.yaml registering all schemas for a package."""
    schema_list = "\n".join(f"    - schema: {pkg}_{s}" for s in systems)
    content = DEFAULT_CUSTOM_TEMPLATE.format(schema_list=schema_list)
    path = output_dir / "default.custom.yaml"
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")


def main():
    for pkg, cfg in PACKAGE_SYSTEMS.items():
        systems = cfg["systems"]
        entries = load_entries(MERGED_CSV, require_systems=cfg["require"])
        if not entries:
            print(f"[{pkg}] No entries, skipping.")
            continue
        pkg_dir = OUTPUT_DIR / f"rime-{pkg}"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        write_base_dict(entries, pkg, pkg_dir)
        for system in systems:
            write_latn_dict(entries, system, pkg, pkg_dir)
            write_schema(system, pkg, pkg_dir)
        write_default_custom(systems, pkg, pkg_dir)
        print(f"[{pkg}] Done.")

    print(f"\nDone. Rime files exported to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
