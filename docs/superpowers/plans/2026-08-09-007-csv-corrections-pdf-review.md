# 007 CSV Corrections and PDF Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all 007 correction rules from Python constants into one authoritative CSV, review every rule against the source PDF, write accepted decisions back to the CSV, and regenerate Markdown without changing correction semantics.

**Architecture:** A typed `CorrectionCatalog` loads and validates the CSV, then exposes the five indexes currently embedded in the 007 module. A review adapter resolves each rule against pre-correction Markdown, builds stable PDF-backed records, and writes accepted replacement/status changes through an auditable plan; the postprocessor only consumes the catalog and never edits the CSV.

**Tech Stack:** Python 3.10+, standard-library `csv`, `dataclasses`, `hashlib`, `json`, `pathlib`, `unittest`; existing loopback review server, vanilla JavaScript client, Poppler PDF renderer, and offline Wikisource cache.

## Global Constraints

- The canonical source is `scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv`.
- Preserve the current 3,031 logical rules exactly during migration: 999 reading, 2 gloss, 11 example split, 2,016 review, and 3 headword review rules.
- Preserve lookup keys byte-for-byte after UTF-8 CSV round-trip; do not normalize PUJ, English, whitespace, punctuation, or Unicode while loading rules.
- Preserve the current precedence: headword review → review → example split → gloss → reading.
- Use one physical CSV row per ordinary rule and one row per split output for `example_split`; rows sharing `rule_id` must have consecutive `output_index` values starting at 1.
- Keep correction keys and PDF page read-only in the review web; reviewers may accept, reject, defer, edit replacement values, and add semantic notes.
- For 007 correction keys, `page` is already the PDF page and the offset is exactly `0`.
- A rejected correction remains in CSV for audit but has `enabled=false`; deferred rules remain unchanged.
- Only accepted, bundle-bound decisions may change CSV; exact old-value comparison is mandatory.
- Rebuilding the same inputs must reproduce the same catalog digest, review record IDs, bundle version, Markdown, and exported CSV.
- Do not add third-party dependencies, do not hand-edit generated export CSV, and do not add Python source comments.
- Preserve unrelated working-tree changes; every commit stages only the paths listed in its task.

## CSV Schema

The header is fixed and ordered:

```text
rule_id,rule_type,headword,key_reading,key_gloss,page,output_index,replacement_reading,replacement_gloss,enabled,review_status,note
```

Allowed values:

```text
rule_type: reading | gloss | example_split | review | headword_review
enabled: true | false
review_status: pending | accepted | rejected | deferred
```

Field rules:

- `reading`: `replacement_reading` required; `replacement_gloss` empty; `output_index=1`.
- `gloss`: `replacement_gloss` required; `replacement_reading` empty; `output_index=1`.
- `review` and `headword_review`: at least one replacement field non-empty; `output_index=1`.
- `headword_review`: `headword` required; all other types require it to be empty.
- `example_split`: at least two rows per `rule_id`; both replacement fields required; `output_index=1..N` without gaps.
- `page` is a positive decimal PDF page.
- `rule_id` is deterministic: `007-<rule_type>-<first 16 hex chars of SHA-256 over headword/key fields>`.

---

### Task 1: Typed Correction Catalog and CSV Validation

**Files:**
- Create: `scripts/wikisource/corrections.py`
- Create: `scripts/tests/test_wikisource_corrections.py`

**Interfaces:**
- Produces: `CorrectionRule`
- Produces: `CorrectionCatalog`
- Produces: `load_correction_catalog(path: Path) -> CorrectionCatalog`
- Produces: `catalog_digest(catalog: CorrectionCatalog) -> str`
- Produces: `rule_id_for(rule_type: str, headword: str, key: tuple[str, str, str]) -> str`

- [ ] **Step 1: Write failing tests for every rule type and index shape**

```python
catalog = load_correction_catalog(fixture)
self.assertEqual("fixed", catalog.reading[("raw", "gloss", "25")])
self.assertEqual("fixed gloss", catalog.gloss[("raw", "gloss", "25")])
self.assertEqual(
    [("one", "first."), ("two", "second.")],
    catalog.example_splits[("raw", "gloss", "25")],
)
self.assertEqual(
    ("fixed", None),
    catalog.review[("raw", "gloss", "25")],
)
self.assertEqual(
    ("fixed", "fixed gloss"),
    catalog.headword_review[("字", "raw", "gloss", "25")],
)
```

- [ ] **Step 2: Write failing validation tests**

Cover duplicate `rule_id/output_index`, duplicate logical keys within a type, unknown enums, invalid booleans, missing headword, forbidden headword, missing replacements, non-positive pages, split groups with one row, split index gaps, and conflicting enabled rows.

- [ ] **Step 3: Run the focused tests and confirm import failure**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_wikisource_corrections -v`

Expected: `ModuleNotFoundError: No module named 'scripts.wikisource.corrections'`.

- [ ] **Step 4: Implement immutable records and fail-closed CSV loading**

```python
@dataclass(frozen=True)
class CorrectionRule:
    rule_id: str
    rule_type: str
    headword: str
    key: tuple[str, str, str]
    output_index: int
    replacement_reading: str
    replacement_gloss: str
    enabled: bool
    review_status: str
    note: str

@dataclass(frozen=True)
class CorrectionCatalog:
    rules: tuple[CorrectionRule, ...]
    reading: dict[tuple[str, str, str], str]
    gloss: dict[tuple[str, str, str], str]
    example_splits: dict[tuple[str, str, str], list[tuple[str, str]]]
    review: dict[tuple[str, str, str], tuple[str | None, str | None]]
    headword_review: dict[tuple[str, str, str, str], tuple[str | None, str | None]]
```

Disabled rules remain in `rules` but are excluded from all runtime indexes.

- [ ] **Step 5: Run focused tests and verify they pass**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_wikisource_corrections -v`

- [ ] **Step 6: Commit the catalog boundary**

```bash
git add scripts/wikisource/corrections.py scripts/tests/test_wikisource_corrections.py
git commit -m "feat(007): add typed CSV correction catalog"
```

### Task 2: Lossless Migration from Python Constants

**Files:**
- Create temporarily: `scripts/migrations/export_007_corrections.py`
- Create: `scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv`
- Modify: `scripts/tests/test_wikisource_corrections.py`

**Interfaces:**
- Consumes: the five current `_BOOK_*` constants and `rule_id_for()`
- Produces: the authoritative CSV and a parity report

- [ ] **Step 1: Write a failing real-data parity test**

The test imports the current 007 module, loads the migrated CSV, and compares all five catalog indexes directly to the five Python constants.

```python
self.assertEqual(mod._BOOK_READING_CORRECTIONS, catalog.reading)
self.assertEqual(mod._BOOK_GLOSS_CORRECTIONS, catalog.gloss)
self.assertEqual(mod._BOOK_EXAMPLE_SPLITS, catalog.example_splits)
self.assertEqual(mod._BOOK_REVIEW_CORRECTIONS, catalog.review)
self.assertEqual(mod._BOOK_HEADWORD_REVIEW_CORRECTIONS, catalog.headword_review)
```

- [ ] **Step 2: Run the parity test and confirm the missing CSV failure**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_wikisource_corrections.CorrectionMigrationTests -v`

- [ ] **Step 3: Implement the one-time exporter**

Export rows in deterministic order `(page as int, rule_type, headword, key_reading, key_gloss, output_index)`. Use `csv.DictWriter`, UTF-8, `newline=""`, and `lineterminator="\n"`; write `enabled=true`, `review_status=pending`, and an empty note. Convert `None` replacements to empty strings and expand each example split into numbered rows.

- [ ] **Step 4: Generate the CSV and print audited counts**

Run: `PYTHONPATH=. .venv/bin/python scripts/migrations/export_007_corrections.py`

Expected logical counts:

```text
reading=999 gloss=2 example_split=11 review=2016 headword_review=3 total=3031
```

- [ ] **Step 5: Run parity, stable-ID, and duplicate-key tests**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_wikisource_corrections -v`

- [ ] **Step 6: Commit the authoritative data before changing runtime reads**

```bash
git add scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv scripts/migrations/export_007_corrections.py scripts/tests/test_wikisource_corrections.py
git commit -m "data(007): migrate correction rules to CSV"
```

### Task 3: Switch the 007 Postprocessor to the Catalog

**Files:**
- Modify: `scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.py`
- Modify: `scripts/tests/test_wikisource_007.py`
- Modify: `scripts/tests/test_wikisource_corrections.py`

**Interfaces:**
- Consumes: `load_correction_catalog()`
- Produces: module-level `CORRECTION_CATALOG`
- Preserves: `_lookup_correction()`, `_lookup_headword_correction()`, and `fix_reading_corrections()` behavior

- [ ] **Step 1: Add a regression test that loads the module with a fixture catalog**

Patch the catalog path before module execution and assert the same precedence collision resolves as follows:

```python
self.assertEqual(
    "headword result",
    apply_fixture(headword="字", reading="raw", gloss="gloss", page="25"),
)
```

Also assert precedence in separate fixtures: headword review beats review; review beats split; split beats gloss; gloss beats reading.

- [ ] **Step 2: Capture the current full offline output hash and parser accounting**

Regenerate to `tmp/007-before-csv-corrections.md`, then record SHA-256, page markers 1–648, and processor entry count 48,597.

- [ ] **Step 3: Replace constant references with catalog indexes**

```python
CORRECTION_CATALOG = load_correction_catalog(
    PROJECT_ROOT / "scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv"
)
```

Route all lookups and `_BOOK_CORRECTION_PRE_KEYS` construction through the catalog without adding a Python-constant fallback.

- [ ] **Step 4: Remove the five embedded constant bodies**

Delete `_BOOK_READING_CORRECTIONS`, `_BOOK_GLOSS_CORRECTIONS`, `_BOOK_EXAMPLE_SPLITS`, `_BOOK_REVIEW_CORRECTIONS`, and `_BOOK_HEADWORD_REVIEW_CORRECTIONS` only after all runtime references use the catalog.

- [ ] **Step 5: Regenerate and compare exact output**

Regenerate to `tmp/007-after-csv-corrections.md` and require byte equality with `tmp/007-before-csv-corrections.md`, plus identical 48,597-entry processor output.

- [ ] **Step 6: Run correction and 007 regressions**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_wikisource_corrections scripts.tests.test_wikisource_007 scripts.tests.test_processor_007 -v`

- [ ] **Step 7: Commit the runtime switch**

```bash
git add scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.py scripts/tests/test_wikisource_007.py scripts/tests/test_wikisource_corrections.py
git commit -m "refactor(007): load correction rules from CSV"
```

### Task 4: Build a Full Correction Review Dataset

**Files:**
- Create: `scripts/proofread_review/correction_review.py`
- Modify: `scripts/proofread_review/models.py`
- Modify: `scripts/proofread_review/build_data.py`
- Modify: `scripts/tests/test_proofread_review.py`

**Interfaces:**
- Consumes: `CorrectionCatalog` and pre-correction 007 Markdown entries
- Produces: `build_correction_review_dataset(catalog, source_entries) -> ReviewDataset`
- Produces: issue type `rule_review`
- Produces context keys: `rule_id`, `rule_type`, `headword`, `key_reading`, `key_gloss`, `key_page`, `resolved_page`, `output_count`

- [ ] **Step 1: Write failing tests for all five rule types**

For each rule, assert `current` contains the uncorrected source entry, `proposal` contains the CSV replacement, `page == resolved_page`, `pdf_page == resolved_page`, and the stable record ID is unchanged by CSV row reordering. Keep the CSV key page separately as `context.key_page`.

- [ ] **Step 2: Write failing tests for unresolved and ambiguous source keys**

Require fail-closed diagnostics for a rule that matches no source entry or multiple entries without a headword discriminator. Do not silently omit either case.

- [ ] **Step 3: Add `rule_review` and rule metadata to the versioned model**

Keep the existing decision schema compatible. Stable IDs bind the rule ID, raw CSV row values, resolved source values, and catalog digest.

- [ ] **Step 4: Resolve rules before applying corrections**

Build source entries from `build_markdown()` plus structural formatting, but before `fix_reading_corrections()`. Resolve exact `(key_reading, key_gloss, page)` first, then use the production-compatible unique-nearby rule within two pages; use `headword` for contextual rules. Record both key page and resolved source page, and fail closed when nearby resolution has more than one candidate. Keep source resolution separate from the runtime correction lookup.

- [ ] **Step 5: Represent split proposals as aligned ordered lines**

Use newline-separated `proposal.reading` and `proposal.gloss` with equal line counts. Preserve the grouped `rule_id` and `output_index`; reject ingestion if the two fields have different non-empty line counts.

- [ ] **Step 6: Add CLI selection for the full correction queue**

```bash
PYTHONPATH=. .venv/bin/python -m scripts.proofread_review.build_data \
  --mode corrections \
  --corrections scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv \
  --output tmp/007-correction-review-data.json
```

- [ ] **Step 7: Assert complete queue accounting**

The generated dataset must contain exactly one review record per logical rule: 3,031 total, grouped by the five expected counts. Every record must resolve or appear in an explicit error report that blocks launch.

- [ ] **Step 8: Run model and dataset tests**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_proofread_review scripts.tests.test_wikisource_corrections -v`

- [ ] **Step 9: Commit the review adapter**

```bash
git add scripts/proofread_review/correction_review.py scripts/proofread_review/models.py scripts/proofread_review/build_data.py scripts/tests/test_proofread_review.py
git commit -m "feat(007): build full correction review queue"
```

### Task 5: Add Rule-Aware Review UI and PDF Configuration

**Files:**
- Modify: `scripts/proofread_review/static/index.html`
- Modify: `scripts/proofread_review/static/app.js`
- Modify: `scripts/proofread_review/static/styles.css`
- Modify: `scripts/proofread_review/server.py`
- Modify: `scripts/run_proofread_review.py`
- Modify: `scripts/tests/test_proofread_review.py`
- Create: `scripts/tests/test_proofread_review_static.py`

**Interfaces:**
- Consumes: correction review dataset records
- Produces: `--page-field page --page-offset 0`
- Produces: a paired-row editor for `example_split`

- [ ] **Step 1: Write static contract tests before changing the UI**

Assert the client exposes rule type/status, read-only key fields, current/proposed/final values, semantic note, accepted/rejected/deferred actions, split-row add/remove/reorder controls, direct PDF page input, previous/next page, and pointer-centered wheel zoom.

- [ ] **Step 2: Write server tests for configurable page mapping**

Launch with `page_field="page"`, `page_offset=0`; assert record page 25 requests PDF page 25. Add a second fixture with offset 24 to preserve left-CSV reuse.

- [ ] **Step 3: Add document configuration to dataset/server health**

```python
DocumentConfig(pdf_path=args.pdf, page_field=args.page_field, page_offset=args.page_offset)
```

Reject a non-integer offset and an unavailable page field before launching. Keep loopback-only binding and current Poppler failure behavior.

- [ ] **Step 4: Render ordinary and split rules with type-specific editors**

Ordinary rules retain reading/gloss final fields. Split rules render ordered paired rows; serialization produces aligned newline fields and validates pair count before acceptance.

- [ ] **Step 5: Preserve flexible semantic handling**

Keep one disposition selector plus one supplemental note. Rejecting a rule does not require a note; structural actions and key/page objections require a non-empty note.

- [ ] **Step 6: Verify PDF interaction contracts**

Test record change auto-jump, manual arbitrary-page navigation, previous/next, manual browsing not changing the record page, mouse-wheel pointer-centered zoom, drag-to-pan, and double-click fit-width.

- [ ] **Step 7: Run server and static tests**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_proofread_review scripts.tests.test_proofread_review_static -v`

- [ ] **Step 8: Commit the rule-aware review UI**

```bash
git add scripts/proofread_review/static/index.html scripts/proofread_review/static/app.js scripts/proofread_review/static/styles.css scripts/proofread_review/server.py scripts/run_proofread_review.py scripts/tests/test_proofread_review.py scripts/tests/test_proofread_review_static.py
git commit -m "feat(007): review CSV corrections against PDF"
```

### Task 6: Compile Decisions into a Stale-Safe CSV Write-Back Plan

**Files:**
- Create: `scripts/proofread_review/correction_writeback.py`
- Modify: `scripts/proofread_review/models.py`
- Create: `scripts/tests/test_correction_writeback.py`

**Interfaces:**
- Produces: `compile_correction_plan(catalog_path: Path, data_path: Path, decisions_path: Path) -> dict[str, object]`
- Produces: `apply_correction_plan(catalog_path: Path, plan: dict[str, object]) -> None`
- Produces schema: `007-correction-csv-writeback-plan/v1`

- [ ] **Step 1: Write failing decision-semantic tests**

```python
accepted_proposal -> enabled=true, review_status=accepted, replacement updated
accepted_current -> enabled=false, review_status=rejected, replacement preserved
rejected -> enabled=false, review_status=rejected, replacement preserved
deferred -> no CSV mutation
```

Also test custom ordinary values, custom split rows, notes, stale source digests, stale catalog digests, missing rule IDs, duplicate decisions, and exact-old-value conflicts.

- [ ] **Step 2: Run the focused test and confirm import failure**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_correction_writeback -v`

- [ ] **Step 3: Implement a dry-run plan containing raw old and new rows**

```json
{
  "schema": "007-correction-csv-writeback-plan/v1",
  "catalog_digest": "...",
  "changes": [
    {
      "rule_id": "...",
      "old_rows": [],
      "new_rows": [],
      "decision_id": "..."
    }
  ],
  "unchanged": [],
  "deferred": []
}
```

- [ ] **Step 4: Implement atomic application**

Re-read the CSV, verify its digest and each exact `old_rows` group, apply changes in current CSV order, revalidate with `load_correction_catalog()`, write a same-directory temporary file, then atomically replace the target.

- [ ] **Step 5: Add CLI preview and explicit apply gate**

```bash
PYTHONPATH=. .venv/bin/python -m scripts.proofread_review.correction_writeback \
  --data tmp/007-correction-review-data.json \
  --decisions tmp/007-correction-review-decisions.json \
  --corrections scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv \
  --plan tmp/007-correction-writeback-plan.json
```

Require `--apply` for mutation; without it, write only the plan.

- [ ] **Step 6: Run write-back and catalog tests**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_correction_writeback scripts.tests.test_wikisource_corrections -v`

- [ ] **Step 7: Commit the CSV write-back gate**

```bash
git add scripts/proofread_review/correction_writeback.py scripts/proofread_review/models.py scripts/tests/test_correction_writeback.py
git commit -m "feat(007): write reviewed corrections back to CSV"
```

### Task 7: End-to-End Migration, Review Launch, and Regeneration Verification

**Files:**
- Modify: `scripts/proofread_review/README.md`
- Modify: `scripts/tests/test_wikisource_007.py`
- Delete: `scripts/migrations/export_007_corrections.py`
- Regenerate: `books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md`
- Regenerate: `export/books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv`

**Interfaces:**
- Consumes: catalog, review data, decisions, and write-back plan
- Produces: documented operator workflow and final verified artifacts

- [ ] **Step 1: Add an end-to-end fixture test**

Create a miniature catalog containing all five types, build review data, ingest accepted/rejected/deferred decisions, apply a CSV plan, regenerate Markdown, and assert only accepted changes land.

- [ ] **Step 2: Generate and validate the real 3,031-rule review bundle**

Run the correction review builder and require:

```text
records=3031 unresolved=0 ambiguous=0 page_offset=0
```

If unresolved or ambiguous is nonzero, stop and export the diagnostics; do not launch an incomplete queue.

- [ ] **Step 3: Launch the PDF review server for a smoke test**

```bash
PYTHONPATH=. .venv/bin/python scripts/run_proofread_review.py \
  --data tmp/007-correction-review-data.json \
  --decisions tmp/007-correction-review-decisions.json \
  --pdf /Users/lim/Desktop/A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.pdf \
  --page-field page \
  --page-offset 0 \
  --port 8765
```

Verify health, first-record PDF rendering, record auto-jump, arbitrary-page jump, wheel zoom, decision autosave, export, and re-import. Stop the smoke-test server afterward.

- [ ] **Step 4: Document the operator workflow**

Document migration invariants, CSV columns, build-review command, server command, export/restore, dry-run write-back, explicit apply, regeneration, audit checks, and rollback through the prior CSV commit.

- [ ] **Step 5: Remove the one-time exporter**

Delete `scripts/migrations/export_007_corrections.py` after parity has passed and the authoritative CSV is committed. Future edits and reviews operate on CSV only.

- [ ] **Step 6: Regenerate official Markdown and selected-book CSV**

```bash
PYTHONPATH=. .venv/bin/python -m scripts.wikisource \
  --title "Dictionary of the Swatow dialect.djvu" \
  --start 1 --end 648 \
  --output books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md \
  --cache-dir tmp/dictionary_of_the_swatow_dialect \
  --offline

PYTHONPATH=. .venv/bin/python scripts/export_csv.py \
  --book 007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect \
  --preserve-order
```

- [ ] **Step 7: Run final accounting and determinism checks**

Require page markers 1–648, 48,597 parsed/exported entries, zero catalog validation errors, stable catalog digest, stable review IDs under CSV row reordering, and identical artifact hashes on a second regeneration.

- [ ] **Step 8: Run all relevant tests and diff checks**

```bash
PYTHONPATH=. .venv/bin/python -m unittest \
  scripts.tests.test_wikisource_corrections \
  scripts.tests.test_wikisource_007 \
  scripts.tests.test_processor_007 \
  scripts.tests.test_proofread_review \
  scripts.tests.test_proofread_review_static \
  scripts.tests.test_correction_writeback \
  scripts.tests.test_export_csv_cli
```

Run `git diff --check` on Python, JavaScript, CSS, HTML, Markdown, and the canonical corrections CSV. Exclude generated CRLF export CSV from whitespace checking and validate it through `csv.DictReader` instead.

- [ ] **Step 9: Commit documentation, cleanup, and regenerated artifacts**

```bash
git add scripts/proofread_review/README.md scripts/tests/test_wikisource_007.py books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md export/books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv
git add -u scripts/migrations/export_007_corrections.py
git commit -m "docs(007): finalize CSV correction review workflow"
```

## Execution Order and Gates

```text
Task 1 → Task 2 parity gate → Task 3 byte-equivalence gate
       → Task 4 complete-accounting gate → Task 5 PDF/UI gate
       → Task 6 dry-run/write-back gate → Task 7 end-to-end gate
```

Do not start PDF review until Task 4 reports all 3,031 logical rules accounted for. Do not delete Python constants until Task 2 parity passes. Do not mutate the canonical CSV from decisions until Task 6 produces a stale-free dry-run plan. Do not regenerate official artifacts until the reviewed CSV passes catalog validation.
