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


def _to_latn_norm(puj_handwriting: str) -> str:
    puj_converter = create_converter("PUJ")
    keyboard = puj_converter.to_keyboard(puj_handwriting)
    return keyboard.replace("-", " ")


def load_entries(csv_path: Path, require_systems: Optional[list] = None):
    """Load and deduplicate entries from merged.csv.

    Returns: dict of (latn_norm, han) -> weight (int)
    Base weight per occurrence: 100. Variants: 50, 25, 12, ...

    require_systems: if set, only include rows where at least one of these
    system columns has a non-empty value (e.g. ["puj", "dp"] for teochew).
    """
    counts = Counter()
    systems_data = {} # (latn_norm, han) -> { "puj": str, "dp": str }
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            latn_norm = (row.get("latn_norm") or "").strip()
            if not latn_norm:
                puj_val = (row.get("puj") or "").strip()
                if puj_val:
                    try:
                        latn_norm = _to_latn_norm(puj_val)
                    except Exception:
                        continue
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
                key = (latn_norm, clean_han)
                counts[key] += 100
                if key not in systems_data:
                    systems_data[key] = {
                        "puj": (row.get("puj") or "").strip(),
                        "dp": (row.get("dp") or "").strip()
                    }
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
    return counts, systems_data


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


CASE_FOLD = [f"derive/{c.lower()}/{c}/" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

SYSTEM_ALGEBRA = {
    "puj": CASE_FOLD
    + [
        "derive/ /-/",
        "derive/[1-8]//",
        "xform/tsh/chh/",
        "xform/ts/ch/",
    ],
    "poj": CASE_FOLD
    + [
        "derive/ /-/",
        "derive/[1-8]//",
        "xform/oo/ou/",
        "xform/oa/ua/",
        "xform/oe/ue/",
    ],
    "tl": CASE_FOLD
    + [
        "derive/ /-/",
        "derive/[1-8]//",
        "xform/ts/ch/",
        "xform/tsh/chh/",
    ],
    "bp": CASE_FOLD
    + [
        "derive/ /-/",
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
    "dp": CASE_FOLD
    + [
        "derive/ /-/",
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
  filters:
    - lua_filter@puj_filter
    - uniquifier

speller:
  alphabet: zyxwvutsrqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA12345678-
  initials: zyxwvutsrqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA12345678
  delimiter: " -"
  algebra:
{algebra}

translator:
  dictionary: {schema_id}
  enable_completion: true
  enable_sentence: true
"""

DEFAULT_CUSTOM_TEMPLATE = """\
# Rime default settings customization
# Generated from merged.csv - do not edit manually

patch:
  schema_list:
{schema_list}
"""

LUA_FILTER_TEMPLATE = """\
-- Rime Lua filter: puj_filter
-- Generated from scripts/export_rime.py - do not edit manually

local function capitalize_first(text)
    if not text or text == "" then return text end
    return text:gsub("^%l", function(c) return c:upper() end)
end

-- Elegant segmentation using Rime's Phrase components
local function apply_user_separators(cand, env)
    local genuine = cand:get_genuine()
    if not genuine then return cand.text end
    
    -- Defensive check: Only 'phrase' or 'sentence' types usually have components
    if type(genuine.size) ~= "function" or type(genuine.at) ~= "function" then
        return cand.text
    end
    
    local input = env.engine.context.input or ""
    local res = ""
    
    -- Use pcall to safely call Rime C++ methods
    local status, size = pcall(function() return genuine:size() end)
    if not status or size <= 1 then return cand.text end
    
    local parts = {}
    for i = 0, size - 1 do
        local sub_ok, sub = pcall(function() return genuine:at(i) end)
        if not sub_ok or not sub then break end
        
        res = res .. sub.text
        
        if i < size - 1 then
            local next_ok, next_sub = pcall(function() return genuine:at(i + 1) end)
            if next_ok and next_sub then
                -- Extract separator from the gap in the input buffer
                local sep_start = sub._end
                local sep_end = next_sub.start
                if sep_end > sep_start then
                    local sep = input:sub(sep_start + 1, sep_end)
                    res = res .. sep
                end
            end
        end
    end
    
    if res ~= "" then return res end
    return cand.text
end

local function filter(translation, env)
    local input = env.engine.context.input or ""
    
    for cand in translation:iter() do
        local text = cand.text
        local genuine = cand:get_genuine()
        
        -- Remove debug markers and apply logic
        if cand.type == "sentence" or cand.type == "user_phrase" or cand.type == "dictionary" then
            -- Remove any existing debug markers if present (from previous versions)
            text = text:gsub("^⟪[^⟫]*⟫ ", "")
            
            -- For sentence candidates, try to preserve user separators (dashes)
            if cand.type == "sentence" or cand.type == "phrase" then
                text = apply_user_separators(cand, env)
            end
            
            -- Capitalization logic
            if input and input:match("^%u") then
                text = capitalize_first(text)
            end
            
            yield(Candidate(cand.type, cand.start, cand._end, text, cand.comment))
        else
            yield(cand)
        end
    end
end

return filter
"""


def _extract_syllable_bases(csv_path: Path) -> set[str]:
    """Extract all unique syllable bases (without tone) from merged.csv."""
    import re

    converter = create_converter("PUJ")
    bases = set()
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            puj = (row.get("puj") or "").strip()
            if not puj:
                continue
            try:
                kb = converter.to_keyboard(puj)
            except Exception:
                continue
            for syl in kb.replace("--", " ").split():
                syl = syl.strip(",.?!")
                m = re.match(r"^([a-z]+?)(\d)$", syl)
                if m:
                    bases.add(m.group(1))
    return bases


def generate_latn_norm_syllables(csv_path: Path = MERGED_CSV):
    """Generate all valid LATN_NORM syllables from actual data + tone expansion."""
    bases = _extract_syllable_bases(csv_path)
    syllables = set()
    for base in bases:
        for tone in range(1, 9):
            syllables.add(f"{base}{tone}")
    return sorted(syllables)


def write_syllables_dict(system: str, pkg: str, output_dir: Path):
    """Write {pkg}_{system}_syllables.dict.yaml with all valid single-syllable romanizations."""
    translator = create_translator("LATN_NORM", system.upper())

    lines = [
        f"# Rime dictionary: {pkg}_{system}_syllables",
        "# Generated - all valid syllables - do not edit manually",
        "---",
        f"name: {pkg}_{system}_syllables",
        'version: "0.1"',
        "sort: by_weight",
        "...",
        "",
    ]

    for syllable in generate_latn_norm_syllables():
        try:
            handwriting = translator.translate(syllable)
        except Exception:
            continue
        if handwriting.strip():
            lines.append(f"{handwriting}\t{syllable}\t1")

    path = output_dir / f"{pkg}_{system}_syllables.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def write_system_dict(entries: dict, systems_data: dict, system: str, pkg: str, output_dir: Path):
    """Write {pkg}_{system}.dict.yaml with romanization entries + han via import.

    Single translator design: romanization entries are first-class dictionary entries
    alongside han entries (imported from base dict via import_tables).
    """
    translator = create_translator("LATN_NORM", system.upper())

    latn_weights = Counter()
    preferred_handwriting = {} # latn_norm -> str

    for (latn_norm, han), weight in entries.items():
        latn_weights[latn_norm] += weight
        hw = systems_data.get((latn_norm, han), {}).get(system.lower())
        if hw and latn_norm not in preferred_handwriting:
            preferred_handwriting[latn_norm] = hw

    lines = [
        f"# Rime dictionary: {pkg}_{system}",
        "# Generated from merged.csv - do not edit manually",
        "---",
        f"name: {pkg}_{system}",
        'version: "0.1"',
        "sort: by_weight",
        "import_tables:",
        f"  - {pkg}",
        f"  - {pkg}_{system}_syllables",
        "...",
        "",
    ]

    for latn_norm, weight in sorted(latn_weights.items()):
        code = latn_norm.replace("-", " ")
        handwriting = preferred_handwriting.get(latn_norm)
        if not handwriting:
            try:
                handwriting = translator.translate(code)
            except Exception:
                continue
        romanized = handwriting # Preserve original spaces/dashes if found in CSV
        if romanized.strip():
            lines.append(f"{romanized}\t{code}\t{weight}")

    path = output_dir / f"{pkg}_{system}.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def format_algebra(rules: list) -> str:
    return "\n".join(f"    - {r}" for r in rules)


def write_schema(system: str, pkg: str, output_dir: Path):
    """Write {pkg}_{system}.schema.yaml."""
    schema_id = f"{pkg}_{system}"
    name = SYSTEM_NAMES[system]
    algebra = format_algebra(SYSTEM_ALGEBRA[system])

    content = SCHEMA_TEMPLATE.format(
        schema_id=schema_id,
        name=name,
        algebra=algebra,
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


def write_lua_filter(output_dir: Path):
    """Write lua/puj_filter.lua."""
    lua_dir = output_dir / "lua"
    lua_dir.mkdir(parents=True, exist_ok=True)
    path = lua_dir / "puj_filter.lua"
    path.write_text(LUA_FILTER_TEMPLATE, encoding="utf-8")
    print(f"Wrote {path}")


def main():
    for pkg, cfg in PACKAGE_SYSTEMS.items():
        systems = cfg["systems"]
        entries, systems_data = load_entries(MERGED_CSV, require_systems=cfg["require"])
        if not entries:
            print(f"[{pkg}] No entries, skipping.")
            continue
        pkg_dir = OUTPUT_DIR / f"rime-{pkg}"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        write_base_dict(entries, pkg, pkg_dir)
        for system in systems:
            write_syllables_dict(system, pkg, pkg_dir)
            write_system_dict(entries, systems_data, system, pkg, pkg_dir)
            write_schema(system, pkg, pkg_dir)
        write_default_custom(systems, pkg, pkg_dir)
        if pkg == "teochew":
            write_lua_filter(pkg_dir)
        print(f"[{pkg}] Done.")

    print(f"\nDone. Rime files exported to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
