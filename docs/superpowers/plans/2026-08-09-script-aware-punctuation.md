# Script-Aware Punctuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bidirectional Chinese/Roman punctuation normalization, apply it to semantic spans in the 007 Markdown pipeline, and normalize the designated proofreading CSV without changing row order.

**Architecture:** Keep punctuation conversion in a pure `scripts/punctuation.py` module. Add a thin CLI in `scripts/normalize_punctuation.py`, while the 007 postprocessor calls a Markdown-structure adapter that converts only headword, PUJ, and English spans.

**Tech Stack:** Python 3.10+, standard-library `argparse`, `csv`, `pathlib`, `re`, and `unittest`.

## Global Constraints

- Map `，。；：！？（）“”‘’` bidirectionally with `,.;:!?()""''`.
- Preserve ASCII apostrophes inside English and PUJ words; normalize `don‘t` and `don’t` to `don't`.
- Preserve CSV headers, row order, row count, non-target fields, and UTF-8 encoding.
- Do not modify page markers or Markdown syntax.
- Repeated normalization in the same direction must be idempotent.
- Do not add third-party dependencies or Python source comments.

---

### Task 1: Pure Punctuation Normalizer

**Files:**
- Create: `scripts/punctuation.py`
- Create: `scripts/tests/test_punctuation.py`

**Interfaces:**
- Produces: `to_roman_punctuation(text: str) -> str`
- Produces: `to_chinese_punctuation(text: str) -> str`

- [ ] **Step 1: Write failing unit tests for mappings, paired quotes, apostrophes, spacing, and idempotency**

```python
self.assertEqual(to_roman_punctuation("伊講：‘don‘t！’"), "伊講: 'don't!'")
self.assertEqual(to_chinese_punctuation('伊講: "好!"'), '伊講：“好！”')
self.assertEqual(to_roman_punctuation(to_roman_punctuation("話，話。")), "話, 話.")
```

- [ ] **Step 2: Run the focused test and confirm it fails because the module is absent**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_punctuation`

- [ ] **Step 3: Implement token-aware quote and punctuation conversion**

Implement pure functions using compiled regular expressions. Detect a curly single quote between word characters as an apostrophe before converting paired quotation marks; apply direction-specific spacing after character mapping.

- [ ] **Step 4: Run the focused test and confirm it passes**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_punctuation`

### Task 2: CLI and CSV Field Policy

**Files:**
- Create: `scripts/normalize_punctuation.py`
- Modify: `scripts/tests/test_punctuation.py`

**Interfaces:**
- Consumes: `to_roman_punctuation`, `to_chinese_punctuation`
- Produces: `normalize_csv(path: Path, chinese_fields: tuple[str, ...], roman_fields: tuple[str, ...]) -> dict[str, int]`
- Produces: CLI `--mode roman|chinese|proofread-csv INPUT [--output OUTPUT]`

- [ ] **Step 1: Write failing tests for CSV field direction, row/header preservation, summary counts, and missing fields**

```python
summary = normalize_csv(path, ("字目", "词条"), ("读音", "释义"))
self.assertEqual(rows[0]["词条"], "話，好！")
self.assertEqual(rows[0]["读音"], "u, ho!")
self.assertEqual(summary["rows"], 1)
```

- [ ] **Step 2: Run tests and confirm the CSV tests fail**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_punctuation`

- [ ] **Step 3: Implement text and atomic CSV CLI paths**

Use `csv.DictReader`/`csv.DictWriter`, create a same-directory temporary file with `tempfile.NamedTemporaryFile`, validate required fields before writing, re-read the temporary output, then replace the requested output path. Emit JSON-compatible summary data from `main()`.

- [ ] **Step 4: Run focused tests and confirm they pass**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_punctuation`

### Task 3: 007 Markdown Pipeline Integration

**Files:**
- Modify: `scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.py`
- Modify: `scripts/tests/test_wikisource_007.py`

**Interfaces:**
- Consumes: both pure punctuation functions
- Produces: `normalize_entry_punctuation(text: str) -> str`

- [ ] **Step 1: Write failing tests for headword, PUJ, English, Markdown, and page-marker preservation**

```python
raw = '<!-- page:1 -->\n- **話,好!** ua，ho！ — say，"good！"\n  - *ua，ho！* — say，good！\n'
self.assertEqual(
    normalize_entry_punctuation(raw),
    '<!-- page:1 -->\n- **話，好！** ua, ho! — say, "good!"\n  - *ua, ho!* — say, good!\n',
)
```

- [ ] **Step 2: Run the focused 007 test and confirm it fails**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_wikisource_007`

- [ ] **Step 3: Implement line-structure normalization and call it at the end of `postprocess`**

Match existing headword and example Markdown shapes, reconstruct lines from unchanged Markdown delimiters plus normalized semantic captures, and leave unmatched lines untouched.

- [ ] **Step 4: Run punctuation and 007 tests and confirm they pass**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_punctuation scripts.tests.test_wikisource_007`

### Task 4: Normalize Real Artifacts and Verify

**Files:**
- Modify: `books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md`
- Modify: `books/（合併校對&修正讀音）斐姑娘詞典.csv`

**Interfaces:**
- Consumes: offline wikitext cache and `proofread-csv` CLI mode
- Produces: normalized Markdown and CSV source artifacts

- [ ] **Step 1: Snapshot CSV structural invariants and current 007 processor count**

Capture the CSV header, row count, ordered tuple of `字目/词条/页码`, and the processor entry count before mutation.

- [ ] **Step 2: Regenerate 007 Markdown from the offline cache**

Run: `PYTHONPATH=. .venv/bin/python -m scripts.wikisource --title "Dictionary of the Swatow dialect.djvu" --start 1 --end 648 --output books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md --cache-dir tmp/dictionary_of_the_swatow_dialect --offline`

- [ ] **Step 3: Normalize the proofreading CSV in place**

Run: `PYTHONPATH=. .venv/bin/python scripts/normalize_punctuation.py --mode proofread-csv 'books/（合併校對&修正讀音）斐姑娘詞典.csv'`

- [ ] **Step 4: Verify structural invariants and residual punctuation**

Assert page markers are exactly 1 through 648, processor entry count is unchanged, no target Chinese punctuation remains in parsed PUJ/English spans, CSV header/row count/key order match the snapshot, and no target Roman punctuation remains in `字目/词条` where it acts as punctuation.

- [ ] **Step 5: Re-run both normalizers and confirm no file changes**

Hash both artifacts, repeat regeneration/CSV normalization, and assert the hashes remain identical.

- [ ] **Step 6: Run regression tests and diff checks**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_punctuation scripts.tests.test_wikisource_007 scripts.tests.test_processor_007`

Run: `git diff --check -- scripts/punctuation.py scripts/normalize_punctuation.py scripts/tests/test_punctuation.py scripts/tests/test_wikisource_007.py scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.py books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md 'books/（合併校對&修正讀音）斐姑娘詞典.csv'`
