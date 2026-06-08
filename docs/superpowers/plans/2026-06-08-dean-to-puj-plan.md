# Dean-to-PUJ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse W. Dean's *First Lessons in the Tie-chiw Dialect* (1841) markdown tables, convert each romanization entry to PUJ using han-based lookup in `teochew.csv` (primary) with rule-based fallback, and output a CSV with page numbers.

**Architecture:** A standalone script `scripts/processors/dean_to_puj.py` following the `ssmp.py` pattern (markdown parsing + CSV output). It loads `teochew.csv` into a han→PUJ index, parses Dean's markdown tables into rows, and for each row either matches han characters against the index (with Levenshtein-based disambiguation for multiple readings) or falls back to rule-based Dean→LATN_NORM conversion.

**Tech Stack:** Python 3.10+, stdlib only (csv, re, pathlib, argparse), existing `scripts.latn` for PUJ conversion.

**Design doc:** `docs/2026-06-08-dean-to-puj-design.md`

---

### Task 1: Markdown table parser

**Files:**
- Create: `scripts/processors/dean_to_puj.py` (initial structure + parser)
- Test: `scripts/tests/test_dean_to_puj.py`

- [ ] **Step 1: Write the failing tests for markdown parsing**

```python
# scripts/tests/test_dean_to_puj.py
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.processors.dean_to_puj import parse_markdown


class TestParseMarkdown(unittest.TestCase):

    def test_extracts_table_rows_with_page(self):
        md = "<!-- page:14 -->\n| One | 一 | Chĕk |\n| Two | 二 | Naw |"
        rows = parse_markdown(md)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], ("14", "One", "一", "Chĕk"))
        self.assertEqual(rows[1], ("14", "Two", "二", "Naw"))

    def test_tracks_page_markers(self):
        md = "<!-- page:14 -->\n| A | 嬰 | Hia |\n<!-- page:17 -->\n| B | 靜 | Tiem |"
        rows = parse_markdown(md)
        self.assertEqual(rows[0][0], "14")
        self.assertEqual(rows[1][0], "17")

    def test_skips_non_table_lines(self):
        md = "<!-- page:14 -->\n# VOWEL SOUNDS\n| One | 一 | Chĕk |"
        rows = parse_markdown(md)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], "Chĕk")

    def test_skips_separator_rows(self):
        md = "<!-- page:14 -->\n|---|---|---|\n| One | 一 | Chĕk |"
        rows = parse_markdown(md)
        self.assertEqual(len(rows), 1)

    def test_cleans_ocr_artifacts(self):
        md = "<!-- page:44 -->\n| Six | 六~~丨~~(條)帶 | toa |"
        rows = parse_markdown(md)
        self.assertEqual(rows[0][2], "六條帶")

    def test_handles_empty_han_column(self):
        md = "<!-- page:54 -->\n| 28 | 二八領籐~~丨~~(蓆) | tin chiĕ |"
        rows = parse_markdown(md)
        self.assertEqual(len(rows), 1)

    def test_handles_phrase_rows(self):
        md = "<!-- page:17 -->\n| Be still | 靜靜 | Tiem tiem |"
        rows = parse_markdown(md)
        self.assertEqual(rows[0], ("17", "Be still", "靜靜", "Tiem tiem"))

    def test_handles_comma_in_dean_latn(self):
        md = "<!-- page:24 -->\n| He lives from hand to mouth | 左手挈、右手去 | Chaw chiw khiĕ,yiw chiw khur |"
        rows = parse_markdown(md)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][3], "Chaw chiw khiĕ")
        self.assertEqual(rows[1][3], "yiw chiw khur")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_dean_to_puj.TestParseMarkdown -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.processors.dean_to_puj'`

- [ ] **Step 3: Write the markdown parser implementation**

Create `scripts/processors/dean_to_puj.py`:

```python
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_PAGE_RE = re.compile(r'<!-- page:(\d+) -->')
_OCR_RE = re.compile(r'~~丨~~\(([^)]*)\)')
_TABLE_ROW_RE = re.compile(r'^\s*\|')
_SEPARATOR_RE = re.compile(r'^\s*\|[-:\s|]+\|\s*$')

_HAN_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf000-\uf8ff\U00020000-\U0002a6df]')


def _clean_han(text: str) -> str:
    text = _OCR_RE.sub(r'\1', text)
    return text


def _extract_han_chars(text: str) -> list[str]:
    return _HAN_RE.findall(text)


def parse_markdown(md_text: str) -> list[tuple[str, str, str, str]]:
    rows = []
    current_page = ""

    for line in md_text.split('\n'):
        page_match = _PAGE_RE.search(line)
        if page_match:
            current_page = page_match.group(1)
            continue

        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        if _SEPARATOR_RE.match(stripped):
            continue

        cells = [c.strip() for c in stripped.split('|')]
        cells = [c for c in cells if c]

        if len(cells) < 3:
            continue

        english = cells[0]
        han_raw = _clean_han(cells[1])
        dean_latn_raw = cells[2]

        han_chars = _extract_han_chars(han_raw)
        if not han_chars:
            continue

        for segment in dean_latn_raw.split(','):
            segment = segment.strip()
            if segment.startswith('、') or not segment:
                continue
            rows.append((current_page, english, han_raw, segment))

    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_dean_to_puj.TestParseMarkdown -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/processors/dean_to_puj.py scripts/tests/test_dean_to_puj.py
git commit -m "feat: add markdown table parser for Dean's Tie-chiw dialect"
```

---

### Task 2: Dean syllable splitter and normalizer

**Files:**
- Modify: `scripts/processors/dean_to_puj.py`
- Modify: `scripts/tests/test_dean_to_puj.py`

- [ ] **Step 1: Write the failing tests**

Add to `scripts/tests/test_dean_to_puj.py`:

```python
from scripts.processors.dean_to_puj import split_dean_syllables, normalize_dean_syllable


class TestSplitDeanSyllables(unittest.TestCase):

    def test_single_syllable(self):
        self.assertEqual(split_dean_syllables("Chĕk"), ["chĕk"])

    def test_hyphenated(self):
        self.assertEqual(split_dean_syllables("a-nou-kia"), ["a", "nou", "kia"])

    def test_space_separated(self):
        self.assertEqual(split_dean_syllables("Tiem tiem"), ["tiem", "tiem"])

    def test_hyphen_and_space(self):
        self.assertEqual(split_dean_syllables("a-pey,keng chai"), ["a", "pey"])

    def test_complex_phrase(self):
        result = split_dean_syllables("Lur a-pey si liou")
        self.assertEqual(result, ["lur", "a", "pey", "si", "liou"])

    def test_special_chars(self):
        self.assertEqual(split_dean_syllables("mʼkheng"), ["mʼkheng"])

    def test_gn_initial(self):
        self.assertEqual(split_dean_syllables("Gñou chap gñou"), ["gñou", "chap", "gñou"])

    def test_c_apostrophe(self):
        self.assertEqual(split_dean_syllables("Cʼhin"), ["cʼhin"])


class TestNormalizeDeanSyllable(unittest.TestCase):

    def test_strip_breve(self):
        self.assertEqual(normalize_dean_syllable("chĕk"), "chek")

    def test_gn_to_ng(self):
        self.assertEqual(normalize_dean_syllable("gñou"), "ngou")

    def test_aou_to_au(self):
        self.assertEqual(normalize_dean_syllable("kaou"), "kau")

    def test_aw_to_o(self):
        self.assertEqual(normalize_dean_syllable("naw"), "no")

    def test_ey_to_e(self):
        self.assertEqual(normalize_dean_syllable("pey"), "pe")

    def test_ow_to_ou(self):
        self.assertEqual(normalize_dean_syllable("kaw"), "ko")

    def test_lowercase(self):
        self.assertEqual(normalize_dean_syllable("Chap"), "chap")

    def test_complex(self):
        self.assertEqual(normalize_dean_syllable("Pŏng"), "pong")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_dean_to_puj.TestSplitDeanSyllables scripts.tests.test_dean_to_puj.TestNormalizeDeanSyllable -v`
Expected: FAIL with `ImportError: cannot import name 'split_dean_syllables'`

- [ ] **Step 3: Implement syllable splitter and normalizer**

Add to `scripts/processors/dean_to_puj.py`:

```python
_BREVE_MAP = str.maketrans({
    'ă': 'a', 'ĕ': 'e', 'ĭ': 'i', 'ŏ': 'o', 'ŭ': 'u',
    'Ă': 'a', 'Ĕ': 'e', 'Ĭ': 'i', 'Ŏ': 'o', 'Ŭ': 'u',
})

_WORD_RE = re.compile(r"[A-Za-z\u0300-\u036f\u0128\u0129\u0131\u00f1\u02bc\u0142\u2019]+")


def split_dean_syllables(text: str) -> list[str]:
    return [m.group().lower() for m in _WORD_RE.finditer(text)]


def normalize_dean_syllable(syllable: str) -> str:
    s = syllable.lower().translate(_BREVE_MAP)
    s = re.sub(r'^gn', 'ng', s)
    s = s.replace('gñ', 'ng')
    s = s.replace('aou', 'au')
    s = s.replace('aw', 'o')
    s = s.replace('ow', 'ou')
    s = s.replace('ey', 'e')
    s = s.replace('iw', 'iu')
    s = s.replace('yiw', 'iu')
    s = s.replace('ñ', 'n')
    s = s.replace('ʼ', '')
    return s
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_dean_to_puj.TestSplitDeanSyllables scripts.tests.test_dean_to_puj.TestNormalizeDeanSyllable -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/processors/dean_to_puj.py scripts/tests/test_dean_to_puj.py
git commit -m "feat: add Dean syllable splitter and normalizer"
```

---

### Task 3: Han-based PUJ lookup with Levenshtein disambiguation

**Files:**
- Modify: `scripts/processors/dean_to_puj.py`
- Modify: `scripts/tests/test_dean_to_puj.py`

- [ ] **Step 1: Write the failing tests**

Add to `scripts/tests/test_dean_to_puj.py`:

```python
from scripts.processors.dean_to_puj import (
    build_han_index,
    levenshtein,
    lookup_puj_for_row,
)


class TestLevenshtein(unittest.TestCase):

    def test_identical(self):
        self.assertEqual(levenshtein("chap", "chap"), 0)

    def test_one_substitution(self):
        self.assertEqual(levenshtein("chap", "tsap"), 1)

    def test_different_lengths(self):
        self.assertEqual(levenshtein("chhit", "chit"), 1)

    def test_empty_strings(self):
        self.assertEqual(levenshtein("", ""), 0)
        self.assertEqual(levenshtein("a", ""), 1)


class TestBuildHanIndex(unittest.TestCase):

    def setUp(self):
        import csv
        import io
        csv_text = "latn_norm,puj,dp,han,han_variants,en,zh_CN,zh_TW,source\n"
        csv_text += "a1,a,,阿,,,,,\n"
        csv_text += "a1,a,,亞,,,,,\n"
        csv_text += "nng6,,nñg6,二,,,,,\n"
        csv_text += "no6,,no6,二,,,,,\n"
        csv_text += "chek8,,chek8,一,,,,,\n"
        csv_text += "it8,,it8,一,,,,,\n"
        csv_text += "kau2,,kau2,九,,,,,\n"
        csv_text += "ou5,,ou5,黑,,,,,\n"
        self.reader = csv.DictReader(io.StringIO(csv_text))
        self.index = build_han_index(self.reader)

    def test_index_has_entries(self):
        self.assertIn("一", self.index)
        self.assertIn("二", self.index)
        self.assertIn("九", self.index)

    def test_index_returns_list_of_puj(self):
        entries = self.index["一"]
        self.assertIsInstance(entries, list)
        self.assertIn(("chek8", "chek"), entries)

    def test_multiple_readings(self):
        entries = self.index["二"]
        pujs = [p for p, _ in entries]
        self.assertIn("nng6", pujs)
        self.assertIn("no6", pujs)


class TestLookupPujForRow(unittest.TestCase):

    def setUp(self):
        import csv
        import io
        csv_text = "latn_norm,puj,dp,han,han_variants,en,zh_CN,zh_TW,source\n"
        csv_text += "nng6,,nñg6,二,,,,,\n"
        csv_text += "no6,,no6,二,,,,,\n"
        csv_text += "chek8,,chek8,一,,,,,\n"
        csv_text += "it8,,it8,一,,,,,\n"
        csv_text += "kau2,,kau2,九,,,,,\n"
        csv_text += "ou5,,ou5,黑,,,,,\n"
        csv_text += "nang5,,nang5,人,,,,,\n"
        csv_text += "hueh4,,hueh4,血,,,,,\n"
        self.reader = csv.DictReader(io.StringIO(csv_text))
        self.index = build_han_index(self.reader)

    def test_single_char_exact_match(self):
        han_chars = ["一"]
        dean_syllables = ["chĕk"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertEqual(result, ["chek8"])

    def test_ambiguous_selects_closest(self):
        han_chars = ["二"]
        dean_syllables = ["naw"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertEqual(result, ["no6"])

    def test_multiple_chars(self):
        han_chars = ["人"]
        dean_syllables = ["nang"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertEqual(result, ["nang5"])

    def test_char_not_in_index_returns_none(self):
        han_chars = ["X"]
        dean_syllables = ["foo"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertIsNone(result)

    def test_mismatched_counts_returns_none(self):
        han_chars = ["一", "二"]
        dean_syllables = ["chĕk"]
        result = lookup_puj_for_row(han_chars, dean_syllables, self.index)
        self.assertIsNone(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_dean_to_puj.TestLevenshtein scripts.tests.test_dean_to_puj.TestBuildHanIndex scripts.tests.test_dean_to_puj.TestLookupPujForRow -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement han index, Levenshtein, and lookup**

Add to `scripts/processors/dean_to_puj.py`:

```python
def levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr.append(min(
                curr[j] + 1,
                prev[j + 1] + 1,
                prev[j] + cost,
            ))
        prev = curr
    return prev[-1]


def build_han_index(reader: csv.DictReader) -> dict[str, list[tuple[str, str]]]:
    index: dict[str, list[tuple[str, str]]] = {}
    for row in reader:
        han = row.get("han", "").strip()
        if not han:
            continue
        puj = row.get("puj", "").strip()
        latn_norm = row.get("latn_norm", "").strip()
        if puj and latn_norm:
            index.setdefault(han, []).append((puj, latn_norm))
    return index


def lookup_puj_for_row(
    han_chars: list[str],
    dean_syllables: list[str],
    han_index: dict[str, list[tuple[str, str]]],
) -> list[str] | None:
    if len(han_chars) != len(dean_syllables):
        return None

    result: list[str] = []
    for han, dean_syl in zip(han_chars, dean_syllables):
        entries = han_index.get(han)
        if not entries:
            return None

        if len(entries) == 1:
            result.append(entries[0][0])
            continue

        normalized = normalize_dean_syllable(dean_syl)
        best = min(entries, key=lambda e: levenshtein(normalized, e[1]))
        result.append(best[0])

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_dean_to_puj.TestLevenshtein scripts.tests.test_dean_to_puj.TestBuildHanIndex scripts.tests.test_dean_to_puj.TestLookupPujForRow -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/processors/dean_to_puj.py scripts/tests/test_dean_to_puj.py
git commit -m "feat: add han-based PUJ lookup with Levenshtein disambiguation"
```

---

### Task 4: Rule-based fallback converter

**Files:**
- Modify: `scripts/processors/dean_to_puj.py`
- Modify: `scripts/tests/test_dean_to_puj.py`

- [ ] **Step 1: Write the failing tests**

Add to `scripts/tests/test_dean_to_puj.py`:

```python
from scripts.processors.dean_to_puj import dean_to_latn_norm


class TestDeanToLatnNorm(unittest.TestCase):

    def test_gn_initial(self):
        self.assertEqual(dean_to_latn_norm("gñou"), "ngou")

    def test_breve_stripped(self):
        self.assertEqual(dean_to_latn_norm("chĕk"), "chek")

    def test_aou(self):
        self.assertEqual(dean_to_latn_norm("kaou"), "kau")

    def test_aw(self):
        self.assertEqual(dean_to_latn_norm("naw"), "no")

    def test_ey(self):
        self.assertEqual(dean_to_latn_norm("pey"), "pe")

    def test_ow(self):
        self.assertEqual(dean_to_latn_norm("low"), "lou")

    def test_iw(self):
        self.assertEqual(dean_to_latn_norm("yiw"), "iu")

    def test_m_apostrophe(self):
        self.assertEqual(dean_to_latn_norm("mʼkheng"), "mkheng")

    def test_c_apostrophe(self):
        self.assertEqual(dean_to_latn_norm("cʼhin"), "chin")

    def test_pñi(self):
        self.assertEqual(dean_to_latn_norm("pñi"), "phinn")

    def test_hñg(self):
        self.assertEqual(dean_to_latn_norm("hñg"), "hngnn")

    def test_kñui(self):
        self.assertEqual(dean_to_latn_norm("kñui"), "kuinn")

    def test_gña(self):
        self.assertEqual(dean_to_latn_norm("gña"), "ngann")

    def test_complex_phrase(self):
        result = dean_to_latn_norm("mʼkheng lai")
        self.assertEqual(result, "mkheng lai")

    def test_chap(self):
        self.assertEqual(dean_to_latn_norm("chap"), "chap")

    def test_boe(self):
        self.assertEqual(dean_to_latn_norm("boe"), "boe")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_dean_to_puj.TestDeanToLatnNorm -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement dean_to_latn_norm**

Add to `scripts/processors/dean_to_puj.py`:

```python
def dean_to_latn_norm(text: str) -> str:
    syllables = split_dean_syllables(text)
    result = []
    for syl in syllables:
        norm = syl.translate(_BREVE_MAP).lower()
        norm = re.sub(r'^gn(?=[aeiou])', 'ng', norm)
        norm = norm.replace('aou', 'au')
        norm = norm.replace('aw', 'o')
        norm = norm.replace('ow', 'ou')
        norm = norm.replace('ey', 'e')
        norm = norm.replace('yiw', 'iu')
        norm = norm.replace('iw', 'iu')
        norm = norm.replace('ʼ', '')

        if re.search(r'ñ', norm):
            norm = re.sub(r'ñ$', 'nn', norm)
            norm = norm.replace('ñ', 'n')

        result.append(norm)
    return ' '.join(result)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests/test_dean_to_puj.TestDeanToLatnNorm -v`
Expected: All PASS. Fix any failures — the `ñ` handling needs to correctly produce `nn` at end for nasalization and `n` elsewhere. Adjust regex order if needed.

- [ ] **Step 5: Commit**

```bash
git add scripts/processors/dean_to_puj.py scripts/tests/test_dean_to_puj.py
git commit -m "feat: add Dean to LATN_NORM rule-based fallback converter"
```

---

### Task 5: Main pipeline — integrate parser, lookup, and fallback

**Files:**
- Modify: `scripts/processors/dean_to_puj.py`
- Modify: `scripts/tests/test_dean_to_puj.py`

- [ ] **Step 1: Write the failing integration tests**

Add to `scripts/tests/test_dean_to_puj.py`:

```python
from scripts.processors.dean_to_puj import process_rows


class TestProcessRows(unittest.TestCase):

    def setUp(self):
        import csv
        import io
        csv_text = "latn_norm,puj,dp,han,han_variants,en,zh_CN,zh_TW,source\n"
        csv_text += "chek8,,chek8,一,,,,,\n"
        csv_text += "it8,,it8,一,,,,,\n"
        csv_text += "no6,,no6,二,,,,,\n"
        csv_text += "nng6,,nng6,二,,,,,\n"
        csv_text += "ngou6,,ngou6,五,,,,,\n"
        csv_text += "nang5,,nang5,人,,,,,\n"
        csv_text += "ou5,,ou5,黑,,,,,\n"
        self.reader = csv.DictReader(io.StringIO(csv_text))

    def test_han_matched_row(self):
        rows = [("14", "One", "一", "Chĕk")]
        results = process_rows(rows, self.reader)
        self.assertEqual(results[0]["puj"], "chek8")
        self.assertEqual(results[0]["source"], "teochew.csv")

    def test_fallback_row(self):
        rows = [("14", "Ghost", "鬼", "Kui")]
        results = process_rows(rows, self.reader)
        self.assertTrue(results[0]["puj"].startswith("*"))
        self.assertEqual(results[0]["source"], "rule")

    def test_preserves_page(self):
        rows = [("14", "One", "一", "Chĕk")]
        results = process_rows(rows, self.reader)
        self.assertEqual(results[0]["page"], "14")

    def test_preserves_dean_latn(self):
        rows = [("14", "One", "一", "Chĕk")]
        results = process_rows(rows, self.reader)
        self.assertEqual(results[0]["dean_latn"], "Chĕk")

    def test_ambiguous_selects_closest(self):
        rows = [("14", "Two", "二", "Naw")]
        results = process_rows(rows, self.reader)
        self.assertEqual(results[0]["puj"], "no6")

    def test_empty_han_skipped(self):
        rows = [("14", "Header", "", "Foo")]
        results = process_rows(rows, self.reader)
        self.assertEqual(len(results), 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_dean_to_puj.TestProcessRows -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement process_rows**

Add to `scripts/processors/dean_to_puj.py`:

```python
def process_rows(
    rows: list[tuple[str, str, str, str]],
    teochew_reader: csv.DictReader,
) -> list[dict[str, str]]:
    han_index = build_han_index(teochew_reader)
    results = []

    for page, english, han_raw, dean_latn in rows:
        han_chars = _extract_han_chars(han_raw)
        if not han_chars:
            continue

        dean_syllables = split_dean_syllables(dean_latn)
        puj_list = lookup_puj_for_row(han_chars, dean_syllables, han_index)

        if puj_list is not None:
            puj = '-'.join(puj_list)
            source = "teochew.csv"
        else:
            latn_norm = dean_to_latn_norm(dean_latn)
            puj = f"*{latn_norm}"
            source = "rule"

        results.append({
            "page": page,
            "english": english,
            "han": han_raw,
            "dean_latn": dean_latn,
            "puj": puj,
            "source": source,
        })

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_dean_to_puj.TestProcessRows -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/processors/dean_to_puj.py scripts/tests/test_dean_to_puj.py
git commit -m "feat: add process_rows integrating lookup and fallback"
```

---

### Task 6: Main entry point with CLI and CSV output

**Files:**
- Modify: `scripts/processors/dean_to_puj.py`
- Test: manual end-to-end run

- [ ] **Step 1: Add the `main()` function and CLI**

Add to `scripts/processors/dean_to_puj.py`:

```python
import argparse


def main():
    parser = argparse.ArgumentParser(description="Convert Dean's Tie-chiw romanization to PUJ")
    parser.add_argument("--input", required=True, help="Path to Dean markdown file")
    parser.add_argument("--teochew", required=True, help="Path to teochew.csv")
    parser.add_argument("--output", required=True, help="Path to output CSV")
    args = parser.parse_args()

    md_text = Path(args.input).read_text(encoding='utf-8')
    rows = parse_markdown(md_text)

    with open(args.teochew, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        results = process_rows(rows, reader)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["page", "english", "han", "dean_latn", "puj", "source"])
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"Wrote {len(results)} entries to {output_path}")
    matched = sum(1 for r in results if r["source"] == "teochew.csv")
    fallback = sum(1 for r in results if r["source"] == "rule")
    print(f"  matched: {matched}, fallback: {fallback}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run end-to-end on the actual book**

Run:
```bash
PYTHONPATH=. python3 scripts/processors/dean_to_puj.py \
  --input books/003_First_Lessons_in_the_Tie-chiw_Dialect.md \
  --teochew export/teochew.csv \
  --output export/dean_to_puj.csv
```

Expected: Prints entry count with matched/fallback breakdown. Check a few rows in the output:

```bash
head -20 export/dean_to_puj.csv
```

Verify:
- `一` → `chek8` (teochew.csv)
- `二` → `no6` (teochew.csv, closest to Naw)
- `黑` → `ou5` or fallback `*ou` (depends on teochew.csv having 黑 with ou reading)

- [ ] **Step 3: Commit**

```bash
git add scripts/processors/dean_to_puj.py
git commit -m "feat: add CLI entry point for Dean-to-PUJ converter"
```

---

### Task 7: Run all tests and review output quality

- [ ] **Step 1: Run all tests**

```bash
PYTHONPATH=. python3 -m unittest scripts.tests.test_dean_to_puj -v
```

Expected: All PASS

- [ ] **Step 2: Inspect output CSV for quality**

```bash
wc -l export/dean_to_puj.csv
# Check matched vs fallback ratio
awk -F, '$6=="rule"' export/dean_to_puj.csv | wc -l
awk -F, '$6=="teochew.csv"' export/dean_to_puj.csv | wc -l
```

- [ ] **Step 3: Spot-check a sampling of entries**

Look at rows from different sections (Numerals, Words, Body, Animals) to verify:
- Han-matched entries have correct PUJ with tones
- Fallback entries have reasonable LATN_NORM forms
- Page numbers are correct

- [ ] **Step 4: If issues found, fix and re-run**

Common issues to watch for:
- OCR-cleaned han characters that don't exist in teochew.csv (will fallback)
- Multi-character phrases where han/syllable counts don't match
- `~~丨~~()` patterns that weren't cleaned correctly
- Dean syllables with unusual characters not handled by normalizer

- [ ] **Step 5: Final commit if fixes were needed**

```bash
git add -A
git commit -m "fix: address Dean-to-PUJ conversion edge cases"
```
