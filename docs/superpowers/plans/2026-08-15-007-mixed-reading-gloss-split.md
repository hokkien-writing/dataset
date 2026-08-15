# 007 Mixed Reading/Gloss Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Execute this plan inline, task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `máng bé-khí; to make edging bé-khí pĭⁿ — edging.` into two correctly paired examples without changing ambiguous existing entries.

**Architecture:** Add a private, book-specific parser for the narrow `reading; ASCII English + reading` shape. Invoke it before the existing conservative chunk classifier; return `None` unless every boundary is independently recognizable.

**Tech Stack:** Python 3.10+, `re`, `unittest`

## Global Constraints

- Keep ambiguous input unchanged.
- Do not add cross-book behavior or hard-code the reported sentence.
- If output comparison finds false-positive splits, revert the parser change and encode one `example_split` correction instead.

---

### Task 1: Regression test and conservative parser

**Files:**
- Modify: `scripts/tests/test_wikisource_007.py`
- Modify: `scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.py`

**Interfaces:**
- Consumes: `_is_reading_seg(seg: str) -> bool`
- Produces: `_split_mixed_phrase_example(ph: str, gl: str) -> list[tuple[str, str]] | None`

- [ ] **Step 1: Write the failing test**

Add a test calling `_expand_example("máng bé-khí; to make edging bé-khí pĭⁿ", "edging.")` and expecting `[('máng bé-khí', 'to make edging.'), ('bé-khí pĭⁿ', 'edging.')]`.

- [ ] **Step 2: Run the focused test and verify failure**

Run `.venv/bin/python -m unittest scripts.tests.test_wikisource_007.TestExpandExampleInlineEnglish.test_semicolon_english_then_reading` and expect one combined tuple instead of two tuples.

- [ ] **Step 3: Implement the minimal parser**

Partition once at `; `. Require the left side to pass `_is_reading_seg`. Try every token boundary in the right side and accept only a boundary whose prefix is non-empty ASCII English and whose suffix passes `_is_reading_seg`. Require exactly one valid boundary; normalize the first gloss with terminal punctuation and pair the supplied gloss with the second reading. Call this helper at the start of `_expand_example`.

- [ ] **Step 4: Run focused and file-level tests**

Run the focused command, then `.venv/bin/python scripts/tests/test_wikisource_007.py`. Both must pass.

- [ ] **Step 5: Compare generated 007 behavior**

Exercise the parser against all formatted 007 example lines and list every input newly split by the helper. Inspect each change. If any is not clearly the same grammatical shape, remove the helper and use a single correction-catalog `example_split` entry.

- [ ] **Step 6: Verify cleanup**

Run `git diff --check` and inspect the scoped diff. Preserve all unrelated working-tree changes.
