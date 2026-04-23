#!/usr/bin/env python3
"""Export Rime input schema files from merged.csv."""

import csv
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.latn import create_translator, create_converter

MERGED_CSV = PROJECT_ROOT / "export" / "merged.csv"
OUTPUT_DIR = PROJECT_ROOT / "export" / "rime"
BUILD_VERSION = datetime.now().strftime("%Y%m%d.%H%M%S")

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
    "poj": "白話字",
    "puj": "潮州白話字",
    "tl": "台羅",
    "dp": "潮州話拼音",
    "bp": "閩南話拼音",
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
    systems_data = {}  # (latn_norm, han) -> { "puj": str, "dp": str }
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
                        "dp": (row.get("dp") or "").strip(),
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


def load_all_entries_for_chars(csv_path: Path) -> Counter:
    """Load all rows from merged.csv and return Counter of (syllable, char) -> weight.

    Decompose entries into individual (syllable, char) pairs by:
    1. Splitting into word segments
    2. Skipping segments with Chinese punctuation (not whole row)
    3. Matching syllable count to char count 1:1
    """
    punct = '。，、！？；：，「」『』""《》'
    # Flower code numerals (花碼) to exclude
    flower_code = "〇〡〢〣〤〥〦〧〨〩〪〭〮〯〫〬〰〱〲〳〴〵〶〷〸〹〺〻〼〽〾〿"
    char_counts = Counter()
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
            if not latn_norm:
                continue
            han = (row.get("han") or "").strip()
            han_variants = (row.get("han_variants") or "").strip()
            if not han:
                continue

            # Clean han: remove text in brackets
            clean_han = re.sub(r"\[[^\]]*\]", "", han)

            # Strategy: expand latn to individual syllables (split by '-'),
            # then match each syllable to corresponding character

            # Split latn by comma first (to handle comma-separated phrases)
            latn_parts = re.split(r",", latn_norm)

            # Initialize all_syllables list
            all_syllables = []

            # Split each part by space, then expand by hyphen
            for part in latn_parts:
                part = part.strip()
                if not part:
                    continue
                for word in part.split():
                    word = word.strip()
                    # Remove quotes from word
                    word = re.sub(r'["\']', "", word)
                    if not word:
                        continue
                    # Expand by hyphen to get individual syllables
                    for syl in word.split("-"):
                        syl = syl.strip()
                        # Remove punctuation from syllable (., ?, !, etc.)
                        syl = re.sub(r"[.?!]", "", syl)
                        if syl:
                            all_syllables.append(syl)

            # Split han into segments, then combine (excluding punctuation)
            han_raw_segments = [
                s.strip()
                for s in re.split(r'[，。、！？；：「」『』""《》\s]+', clean_han)
                if s.strip()
            ]

            # Skip if no syllables
            if not all_syllables:
                continue

            # Combine all han segments (skip those with Chinese punctuation)
            all_chars = ""
            for seg in han_raw_segments:
                if not any(p in seg for p in punct):
                    all_chars += seg

            # Skip if has flower code
            if any(c in flower_code for c in all_chars):
                continue

            chars_list = list(all_chars)

            # Must match syllable count to character count 1:1
            if len(all_syllables) != len(chars_list):
                continue

            base_weight = 100
            for syl, ch in zip(all_syllables, chars_list):
                if (syl, ch) not in char_counts:
                    char_counts[(syl, ch)] = base_weight
                else:
                    char_counts[(syl, ch)] += base_weight

            if han_variants:
                last_weight = base_weight
                for variant in han_variants.split("|"):
                    v = variant.strip()
                    if v:
                        clean_v = re.sub(r"\[[^\]]*\]", "", v)
                        var_segments = [
                            s.strip()
                            for s in re.split(
                                r'[，。、！？；：「」『』""《》\s]+', clean_v
                            )
                            if s.strip()
                        ]
                        # Use SAME syllables as main entry
                        all_chars_var = "".join(var_segments)
                        if any(p in all_chars_var for p in punct):
                            all_chars_var = ""
                            for seg in var_segments:
                                if not any(p in seg for p in punct):
                                    all_chars_var += seg
                        # Skip variants with flower code
                        if any(c in all_chars_var for c in flower_code):
                            continue
                        chars_var_list = list(all_chars_var)
                        if len(all_syllables) == len(chars_var_list):
                            last_weight = last_weight // 2
                            for syl, ch in zip(all_syllables, chars_var_list):
                                if (syl, ch) not in char_counts:
                                    char_counts[(syl, ch)] = last_weight
                                else:
                                    char_counts[(syl, ch)] += last_weight
    return char_counts


def write_char_dict_from_counts(char_counts: Counter, pkg: str, output_dir: Path):
    """Write {pkg}_chars.dict.yaml from precomputed (syllable, char) -> weight Counter."""
    if not char_counts:
        return
    lines = [
        f"# Rime dictionary: {pkg}_chars",
        "# Generated from merged.csv - decomposed character table",
        "---",
        f"name: {pkg}_chars",
        f'version: "{BUILD_VERSION}"',
        "sort: by_weight",
        "...",
        "",
    ]
    for (syl, ch), count in sorted(char_counts.items()):
        code = _strip_brackets(syl).replace("--", "   ").replace("-", "  ")
        ch = _strip_brackets(ch)
        if not ch or not code:
            continue
        lines.append(f"{ch}\t{code}\t{count}")
    path = output_dir / f"{pkg}_chars.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(char_counts)} char entries to {path}")


def write_base_dict(entries: dict, pkg: str, output_dir: Path):
    """Write {pkg}.dict.yaml (latn_norm -> han with weights)."""
    lines = [
        f"# Rime dictionary: {pkg}",
        "# Generated from merged.csv - do not edit manually",
        "---",
        f"name: {pkg}",
        f'version: "{BUILD_VERSION}"',
        "sort: by_weight",
        "...",
        "",
    ]
    for (latn_norm, han), count in sorted(entries.items()):
        code = _strip_brackets(latn_norm).replace("--", "   ").replace("-", "  ")
        han = _strip_brackets(han)
        if not han or not code:
            continue
        lines.append(f"{han}\t{code}\t{count}")
    path = output_dir / f"{pkg}.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {path}")


def _strip_brackets(s: str) -> str:
    import re

    s = re.sub(r"\[(?:替|音|訓|文|白)\]", "", s)
    s = re.sub(r"^\[([^\]]+)\]$", r"\1", s)
    return s


CASE_FOLD = [f"derive/{c.lower()}/{c}/" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

COMMENT_FORMAT = {
    "puj": [
        "xform/-/ /",
        "xform/chh/tsh/",
        "xform/ch/ts/",
        "xlit/12345678/¹²³⁴⁵⁶⁷⁸/",
    ],
    "poj": [
        "xform/-/ /",
        "xform/ou/oo/",
        "xform/ua/oa/",
        "xform/ue/oe/",
    ],
    "tl": [
        "xform/-/ /",
        "xform/chh/tsh/",
        "xform/ch/ts/",
    ],
    "bp": [
        "xform/-/ /",
        "xform/^g/gg/",
        "xform/^b/bb/",
        "xform/^j/zz/",
        "xform/^chh/c/",
        "xform/^ch/z/",
        "xform/^k(?=[^h])/g/",
        "xform/^kh/k/",
        "xform/^p(?=[^h])/b/",
        "xform/^ph/p/",
        "xform/^t(?=[^h])/d/",
        "xform/^th/t/",
        "xform/ou/oo/",
        "xform/^n(?=[^g])/ln/",
        "xform/([aeiou]+)nnh(\\d)$/n$1h$2/",
        "xform/([aeiou]+)nn(\\d)$/n$1$2/",
        "xform/^ng/ggn/",
        "xform/^m/bbn/",
        "xlit/12345678/¹²³⁴⁵⁶⁷⁸/",
    ],
    "dp": [
        "xform/-/ /",
        "xform/^g/gh/",
        "xform/^b/bh/",
        "xform/^j/r/",
        "xform/^chh/c/",
        "xform/^ch/z/",
        "xform/^k(?=[^h])/g/",
        "xform/^kh/k/",
        "xform/^p(?=[^h])/b/",
        "xform/^ph/p/",
        "xform/^t(?=[^h])/d/",
        "xform/^th/t/",
        "xform/e/ei/",
        "xform/ur/e/",
        "xlit/12345678/¹²³⁴⁵⁶⁷⁸/",
    ],
}

SYSTEM_ALGEBRA = {
    "puj": [
        "derive/ /-/",
        "derive/[1-8]//",
        "derive/ch/ts/",
        "derive/chh/tsh/",
        "derive/oinn/ainn/",
        "derive/nn//",
    ]
    + CASE_FOLD,
    "poj": [
        "derive/ /-/",
        "derive/[1-8]//",
        "xform/ou/oo/",
        "xform/ua/oa/",
        "xform/ue/oe/",
    ]
    + CASE_FOLD,
    "tl": [
        "xform/ch/ts/",
        "xform/chh/tsh/",
        "derive/ /-/",
        "derive/[1-8]//",
    ]
    + CASE_FOLD,
    "bp": [
        "xform/^g/gg/",
        "xform/^b/bb/",
        "xform/^j/zz/",
        "xform/^chh/c/",
        "xform/^ch/z/",
        "xform/^k(?=[^h])/g/",
        "xform/^kh/k/",
        "xform/^p(?=[^h])/b/",
        "xform/^ph/p/",
        "xform/^t(?=[^h])/d/",
        "xform/^th/t/",
        "xform/ou/oo/",
        "xform/^n(?=[^g])/ln/",
        "xform/([aeiou]+)nnh(\\d)$/n$1h$2/",
        "xform/([aeiou]+)nn(\\d)$/n$1$2/",
        "xform/^ng/ggn/",
        "xform/^m/bbn/",
        "derive/ /-/",
        "derive/[1-8]//",
    ]
    + CASE_FOLD,
    "dp": [
        "xform/^g/gh/",
        "xform/^b/bh/",
        "xform/^j/r/",
        "xform/^chh/c/",
        "xform/^ch/z/",
        "xform/^k(?=[^h])/g/",
        "xform/^kh/k/",
        "xform/^p(?=[^h])/b/",
        "xform/^ph/p/",
        "xform/^t(?=[^h])/d/",
        "xform/^th/t/",
        "xform/e/ei/",
        "xform/ur/e/",
        "derive/ /-/",
        "derive/[1-8]//",
        "derive/d/g/",
        "derive/([aeiu])n$/$1ng/",
        "derive/oinn/ainn/",
        "derive/nn//",
    ]
    + CASE_FOLD,
}

SCHEMA_TEMPLATE = """\
# Rime schema: {schema_id}
# Generated from merged.csv - do not edit manually

schema:
  schema_id: {schema_id}
  name: {name}
  version: "{version}"
  author:
    - Hokkien Writing Project
  dependencies:
    - {schema_id}_en

engine:
  processors:
    - ascii_composer
    - recognizer
    - lua_processor@{caps_tracker_name}
    - speller
    - punctuator
    - selector
    - navigator
    - key_binder
    - express_editor
  segmentors:
    - abc_segmentor
    - matcher
    - punct_segmentor
    - fallback_segmentor
  translators:
    - script_translator
    - reverse_lookup_translator
    - reverse_lookup_translator@en_lookup
  filters:
    - lua_filter@{filter_name}
    - uniquifier

speller:
  alphabet: zyxwvutsrqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA12345678-
  initials: zyxwvutsrqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA12345678
  delimiter: " -"
  algebra:
{algebra}

key_binder:
  bindings:
    - {{ when: paging, accept: Left, send: Page_Up }}
    - {{ when: has_menu, accept: Right, send: Page_Down }}
    - {{ when: paging, accept: bracketleft, send: Page_Up }}
    - {{ when: has_menu, accept: bracketright, send: Page_Down }}
    - {{ when: has_menu, accept: Tab, send: Page_Down }}
    - {{ when: paging, accept: Shift+Tab, send: Page_Up }}

style:
  horizontal: true
  candidate_list_layout: linear
  candidate_format: "%@"

translator:
  dictionary: {schema_id}
  enable_completion: true
  enable_sentence: true
  enable_user_dict: true
  spelling_hints: 99

reverse_lookup:
  dictionary: luna_pinyin
  prefix: "`"
  suffix: "'"
  tips: "〔普通話拼音〕"
  comment_format:
{pinyin_comment_format}

en_lookup:
  dictionary: {schema_id_en}
  prefix: "~"
  suffix: "'"
  tips: "〔English〕"
  comment_format:
{en_comment_format}

recognizer:
  import_preset: default
  patterns:
    en_lookup: "~[a-z]*'?$"
    reverse_lookup: "`[a-z]*'?$"

abc_segmentor:
  extra_tags:
    - reverse_lookup
"""

DEFAULT_CUSTOM_TEMPLATE = """\
# Rime default settings customization
# Generated from merged.csv - do not edit manually

patch:
  schema_list:
{schema_list}
  "menu/page_size": 6
"""

LUA_PROCESSOR_TEMPLATE = ""

LUA_FILTER_TEMPLATE = """\
-- Rime Lua module: {filter_name} (contains both processor and filter)
-- Generated from scripts/export_rime.py - do not edit manually

-- Comprehensive mapping of syllable codes to {system_name} handwriting
{syllable_map}

local LATIN_UPPER = {
    ["à"] = "À", ["á"] = "Á", ["â"] = "Â", ["ã"] = "Ã",
    ["è"] = "È", ["é"] = "É", ["ê"] = "Ê",
    ["ì"] = "Ì", ["í"] = "Í", ["î"] = "Î",
    ["ñ"] = "Ñ",
    ["ò"] = "Ò", ["ó"] = "Ó", ["ô"] = "Ô", ["õ"] = "Õ",
    ["ù"] = "Ù", ["ú"] = "Ú", ["û"] = "Û",
    ["ā"] = "Ā", ["ē"] = "Ē", ["ĩ"] = "Ĩ", ["ī"] = "Ī",
    ["ń"] = "Ń", ["ō"] = "Ō", ["ũ"] = "Ũ", ["ū"] = "Ū",
    ["ǹ"] = "Ǹ", ["ḿ"] = "Ḿ", ["ṳ"] = "Ṳ", ["ẽ"] = "Ẽ",
}

local function capitalize_first(text)
    if not text or text == "" then return text end
    local first = utf8.char(utf8.codepoint(text, 1))
    local upper = LATIN_UPPER[first] or first:upper()
    return upper .. text:sub(utf8.offset(text, 2) or (#text + 1))
end

local _caps_mask = ""

local function processor(key, env)
    if key:release() then return 2 end
    local ctx = env.engine.context
    local kc = key.keycode

    local n = #ctx.input
    if #_caps_mask > n then
        _caps_mask = _caps_mask:sub(1, n)
    end

    if kc == 8 then
        if #_caps_mask > 0 then
            _caps_mask = _caps_mask:sub(1, #_caps_mask - 1)
        end
        return 2
    end

    if kc >= 65 and kc <= 90 then
        _caps_mask = _caps_mask .. "U"
    elseif (kc >= 97 and kc <= 122) or (kc >= 48 and kc <= 57) or kc == 45 then
        _caps_mask = _caps_mask .. "_"
    end

    return 2
end

local function get_caps_mask(env)
    local ctx = env.engine.context
    local n = #ctx.input
    local caps = _caps_mask
    if #caps > n then caps = caps:sub(1, n) end
    while #caps < n do caps = caps .. "_" end
    return caps
end

local function codes_to_handwriting(comment)
    if not comment or comment == "" then return "" end
    local result = comment:gsub("[%w]+", function(code)
        local hw = SYLLABLE_MAP[code:lower()]
        return hw or code
    end)
    result = result:gsub("   ", "--")
    result = result:gsub("  ", "-")
    return result
end

local function apply_user_separators(cand, env)
    local ctx = env.engine.context
    local input = ctx.input or ""
    local comment = cand.comment or ""
    if input == "" then return cand.text end

    local caps = get_caps_mask(env)

    local codes = {}
    for code in comment:gmatch("[%w]+") do
        table.insert(codes, code)
    end

    local res = ""
    local i = 1
    local code_idx = 1
    while i <= #input do
        local token = input:match("^[%w]+", i)
        if token then
            local hw = token
            local full_code = codes[code_idx]
            if full_code then
                hw = SYLLABLE_MAP[full_code:lower()] or SYLLABLE_MAP[token:lower()] or token
                code_idx = code_idx + 1
            else
                hw = SYLLABLE_MAP[token:lower()] or token
            end

            if caps:sub(i, i) == "U" then
                hw = capitalize_first(hw)
            end

            res = res .. hw
            i = i + #token
        else
            local sep = input:match("^[^%w]+", i)
            if sep then
                res = res .. sep
                i = i + #sep
            else
                local char = input:sub(i, i)
                res = res .. char
                i = i + 1
            end
        end
    end
    return res
end

local function is_han_char(text)
    if not text or #text == 0 then return false end
    local b = string.byte(text, 1)
    if b >= 0xE4 and b <= 0xE9 then return true end
    if b >= 0xF0 then return true end
    return false
end

local function filter(translation, env)
    local caps = _caps_mask
    local has_caps = caps:sub(1, 1) == "U"
    local latin_cands = {}
    local han_cands = {}

    for cand in translation:iter() do
        local original_is_han = is_han_char(cand.text)
        local need_reconstruct = (cand.type == "sentence" or cand.type == "user_phrase"
            or cand.type == "dictionary")

        local display_text = cand.text
        if need_reconstruct then
            display_text = apply_user_separators(cand, env)
        end

        local display_comment = original_is_han
            and codes_to_handwriting(cand.comment)
            or ""

        if not has_caps then
            cand.comment = display_comment
            yield(cand)
        else
            if has_caps then
                display_text = capitalize_first(display_text)
            end
            local is_latin = display_text:match("^%a") ~= nil
            local new_cand = Candidate(cand.type, cand.start, cand._end, display_text, display_comment)
            if is_latin then
                table.insert(latin_cands, new_cand)
            else
                table.insert(han_cands, new_cand)
            end
        end
    end

    if has_caps then
        for _, c in ipairs(latin_cands) do yield(c) end
        for _, c in ipairs(han_cands) do yield(c) end
    end
end

return {{ processor = processor }, filter}
"""


def _extract_syllable_bases_from_entries(entries: dict) -> set[str]:
    """Extract all unique LATN_NORM syllable bases directly from entries."""
    bases = set()
    for (latn_norm, _han), _weight in entries.items():
        for syl in re.split(r"[\s\-]+", latn_norm):
            m = re.match(r"^([a-z]+?)(\d)$", syl.strip())
            if m:
                bases.add(m.group(1))
    return bases


def generate_latn_norm_syllables(entries: dict):
    """Generate all valid LATN_NORM syllables from actual data + tone expansion."""
    bases = _extract_syllable_bases_from_entries(entries)
    syllables = set()
    for base in bases:
        if base.endswith(("p", "t", "k", "h")):
            tones = [4, 8]
        else:
            tones = [1, 2, 3, 5, 6, 7]
        for tone in tones:
            syllables.add(f"{base}{tone}")
    return sorted(syllables)


def write_syllables_dict(entries: dict, system: str, pkg: str, output_dir: Path):
    """Write {pkg}_{system}_syllables.dict.yaml with all valid single-syllable romanizations."""
    translator = create_translator("LATN_NORM", system.upper())

    lines = [
        f"# Rime dictionary: {pkg}_{system}_syllables",
        "# Generated - all valid syllables - do not edit manually",
        "---",
        f"name: {pkg}_{system}_syllables",
        f'version: "{BUILD_VERSION}"',
        "sort: by_weight",
        "...",
        "",
    ]

    for syllable in generate_latn_norm_syllables(entries):
        try:
            handwriting = translator.translate(syllable)
        except Exception:
            continue
        if handwriting.strip():
            lines.append(f"{handwriting}\t{syllable}\t1")

    path = output_dir / f"{pkg}_{system}_syllables.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def write_system_dict(
    entries: dict, systems_data: dict, system: str, pkg: str, output_dir: Path
):
    """Write {pkg}_{system}.dict.yaml with romanization entries + han via import.

    Single translator design: romanization entries are first-class dictionary entries
    alongside han entries (imported from base dict via import_tables).
    """
    translator = create_translator("LATN_NORM", system.upper())
    system_converter = create_converter(system.upper())

    latn_weights = Counter()
    preferred_handwriting = {}  # latn_norm -> str

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
        f'version: "{BUILD_VERSION}"',
        "sort: by_weight",
        "import_tables:",
        f"  - {pkg}_chars",
        f"  - {pkg}",
        f"  - {pkg}_{system}_syllables",
        "...",
        "",
    ]

    for latn_norm, weight in sorted(latn_weights.items()):
        spaced_code = _strip_brackets(latn_norm).replace("-", " ")
        rom_weight = weight - 1
        csv_handwriting = preferred_handwriting.get(latn_norm)
        if not csv_handwriting or not csv_handwriting.strip():
            try:
                csv_handwriting = translator.translate(latn_norm)
            except Exception:
                continue
        if not csv_handwriting or not csv_handwriting.strip():
            continue
        csv_handwriting = _strip_brackets(csv_handwriting)
        standard_handwriting = _strip_brackets(
            system_converter.to_handwriting(
                system_converter.to_keyboard(csv_handwriting)
            )
        )
        if system == "dp":
            if standard_handwriting and standard_handwriting.strip():
                lines.append(
                    f"{standard_handwriting.replace('-', '')}\t{spaced_code}\t{rom_weight}"
                )
            if csv_handwriting and csv_handwriting != standard_handwriting:
                lines.append(
                    f"{csv_handwriting.replace('-', '')}\t{spaced_code}\t{rom_weight - 1}"
                )
        else:
            if standard_handwriting and standard_handwriting.strip():
                lines.append(f"{standard_handwriting}\t{spaced_code}\t{rom_weight}")
            if csv_handwriting and csv_handwriting != standard_handwriting:
                lines.append(f"{csv_handwriting}\t{spaced_code}\t{rom_weight - 1}")

    path = output_dir / f"{pkg}_{system}.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def format_algebra(rules: list) -> str:
    lines = []
    for r in rules:
        if r.startswith("#"):
            lines.append(f"    {r}")
        else:
            lines.append(f"    - {r}")
    return "\n".join(lines)


def format_comment_format(rules: list) -> str:
    lines = []
    for r in rules:
        lines.append(f"    - {r}")
    return "\n".join(lines)


def _clean_en(en_text: str) -> str:
    if en_text.startswith("#") or en_text.startswith("-") or en_text.startswith(":"):
        return ""
    text = en_text
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r'"[^"]*"', "", text)
    text = re.sub(r"means.*", "", text)
    text = re.sub(r"[^a-zA-Z ]", "", text)
    text = re.sub(r" +", " ", text).strip()
    return text if len(text.split()) <= 5 else ""


def write_en_dict(
    entries: dict, systems_data: dict, system: str, pkg: str, output_dir: Path
):
    translator = create_translator("LATN_NORM", system.upper())
    system_converter = create_converter(system.upper())
    dict_name = f"{pkg}_{system}_en"
    lines = [
        f"# Rime dictionary: {dict_name}",
        "# Generated from merged.csv - English reverse lookup",
        "---",
        f"name: {dict_name}",
        f'version: "{BUILD_VERSION}"',
        "sort: by_weight",
        "...",
        "",
    ]
    seen = set()
    count = 0
    with open(MERGED_CSV, encoding="utf-8") as f:
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
            en = (row.get("en") or "").strip()
            if not en or not latn_norm:
                continue
            if re.search(r'[".]', latn_norm):
                continue
            en_clean = _clean_en(en)
            if not en_clean:
                continue
            han = (row.get("han") or "").strip()
            han = re.sub(r"\[[^\]]*\]", "", han)
            if han:
                key = (han, en_clean)
                if key in seen:
                    continue
                if han.startswith("-") or han.startswith(":") or han.startswith("#"):
                    continue
                seen.add(key)
                lines.append(f"{han}\t{en_clean}\t100")
                count += 1
            else:
                csv_hw = (row.get(system) or "").strip()
                if not csv_hw:
                    try:
                        csv_hw = translator.translate(latn_norm)
                    except Exception:
                        continue
                if not csv_hw or not csv_hw.strip():
                    continue
                csv_hw = re.sub(r"[:\[\]#]+", "", csv_hw)
                csv_hw = csv_hw.strip()
                if not csv_hw:
                    continue
                    try:
                        csv_hw = translator.translate(latn_norm)
                    except Exception:
                        continue
                if not csv_hw or not csv_hw.strip():
                    continue
                try:
                    hw = system_converter.to_handwriting(
                        system_converter.to_keyboard(csv_hw)
                    )
                except Exception:
                    hw = csv_hw
                hw = _strip_brackets(hw)
                if system == "dp":
                    hw = hw.replace("-", "")
                if hw.startswith("-") or hw.startswith(":") or hw.startswith("#"):
                    continue
                key = (hw, en_clean)
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"{hw}\t{en_clean}\t50")
                count += 1
    path = output_dir / f"{dict_name}.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {count} entries to {path}")


def write_schema(system: str, pkg: str, output_dir: Path):
    schema_id = f"{pkg}_{system}"
    name = SYSTEM_NAMES[system]
    algebra = format_algebra(SYSTEM_ALGEBRA[system])
    filter_name = f"{system}_filter"
    caps_tracker_name = f"{system}_caps_tracker"
    comment_fmt = format_comment_format(COMMENT_FORMAT[system])

    content = SCHEMA_TEMPLATE.format(
        schema_id=schema_id,
        name=name,
        version=BUILD_VERSION,
        algebra=algebra,
        filter_name=filter_name,
        caps_tracker_name=caps_tracker_name,
        pinyin_comment_format=comment_fmt,
        en_comment_format=comment_fmt,
        schema_id_en=f"{schema_id}_en",
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


def generate_han_rom_map(entries: dict, systems_data: dict, system: str) -> str:
    translator = create_translator("LATN_NORM", system.upper())
    system_converter = create_converter(system.upper())
    mapping = {}
    for (latn_norm, han), weight in entries.items():
        csv_hw = systems_data.get((latn_norm, han), {}).get(system.lower())
        if not csv_hw or not csv_hw.strip():
            try:
                csv_hw = translator.translate(latn_norm)
            except Exception:
                continue
        if not csv_hw or not csv_hw.strip():
            continue
        try:
            hw = system_converter.to_handwriting(system_converter.to_keyboard(csv_hw))
        except Exception:
            hw = csv_hw
        if system == "dp":
            hw = hw.replace("-", "")
            if csv_hw and csv_hw != hw:
                if han not in mapping:
                    mapping[han] = csv_hw.replace("-", "")
        if han not in mapping and hw and hw.strip():
            mapping[han] = hw
    lines = ["local HAN_ROM_MAP = {"]
    for k, v in sorted(mapping.items()):
        safe_v = v.replace("\\", "\\\\").replace('"', '\\"')
        safe_k = k.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'    ["{safe_k}"] = "{safe_v}",')
    lines.append("}")
    return "\n".join(lines)


def generate_syllable_map(entries: dict, system: str) -> str:
    """Generate a Lua table mapping syllable codes to their handwriting."""
    translator = create_translator("LATN_NORM", system.upper())
    syllables = generate_latn_norm_syllables(entries)

    mapping = {}
    # First pass: all explicit tone syllables (e.g., menn1, ak4)
    for syl in syllables:
        try:
            hw = translator.translate(syl)
            if hw and hw.strip().lower() != syl.lower():
                mapping[syl.lower()] = hw
        except Exception:
            continue

    # Second pass: Implicit tone rules for digit-less input (e.g., menn -> meⁿ)
    # Rule: syllables ending in p, t, k, h are tone 4, others are tone 1
    bases = _extract_syllable_bases_from_entries(entries)
    for base in bases:
        base = base.lower()
        # Only add if not already present as a special single-letter syllable
        if base not in mapping:
            default_tone = "4" if base.endswith(("p", "t", "k", "h")) else "1"
            try:
                hw = translator.translate(base + default_tone)
                if hw:
                    mapping[base] = hw
            except Exception:
                continue

    lines = ["local SYLLABLE_MAP = {"]
    for k, v in sorted(mapping.items()):
        lines.append(f'    ["{k}"] = "{v}",')
    lines.append("}")
    return "\n".join(lines)


def write_lua_filter(entries: dict, system: str, output_dir: Path):
    """Write lua/{system}_filter.lua (single module with processor + filter)."""
    lua_dir = output_dir / "lua"
    lua_dir.mkdir(parents=True, exist_ok=True)

    filter_name = f"{system}_filter"
    system_name = SYSTEM_NAMES.get(system, system)
    syl_map_lua = generate_syllable_map(entries, system)
    content = (
        LUA_FILTER_TEMPLATE.replace("{syllable_map}", syl_map_lua)
        .replace("{filter_name}", filter_name)
        .replace("{system_name}", system_name)
    )
    path = lua_dir / f"{filter_name}.lua"
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")

    return filter_name


def main():
    # For character dict, use all entries (no system filtering) and punctuation stripped
    all_char_counts = load_all_entries_for_chars(MERGED_CSV)

    for pkg, cfg in PACKAGE_SYSTEMS.items():
        systems = cfg["systems"]
        entries, systems_data = load_entries(MERGED_CSV, require_systems=cfg["require"])
        if not entries:
            print(f"[{pkg}] No entries, skipping.")
            continue
        pkg_dir = OUTPUT_DIR / f"rime-{pkg}"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        write_base_dict(entries, pkg, pkg_dir)
        write_char_dict_from_counts(all_char_counts, pkg, pkg_dir)
        for system in systems:
            write_syllables_dict(entries, system, pkg, pkg_dir)
            write_system_dict(entries, systems_data, system, pkg, pkg_dir)
            write_en_dict(entries, systems_data, system, pkg, pkg_dir)
            write_schema(system, pkg, pkg_dir)
        write_default_custom(systems, pkg, pkg_dir)
        filter_names = []
        for system in systems:
            filter_names.append(write_lua_filter(entries, system, pkg_dir))
        rime_lua = pkg_dir / "rime.lua"
        lines = []
        for system in systems:
            fn = f"{system}_filter"
            ct = f"{system}_caps_tracker"
            lines.append(f"local {fn}_mod = require('{fn}')")
            lines.append(f"{fn} = {fn}_mod[2]")
            lines.append(f"{ct} = {fn}_mod[1].processor")
        rime_lua.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[{pkg}] Done.")

    print(f"\nDone. Rime files exported to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
