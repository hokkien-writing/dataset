# 007 Proofread Review Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local review web app for 131 unique unresolved 007 dictionary entries carrying 133 review issues, with source-page inspection, editable decisions, autosave, and reversible JSON export.

**Architecture:** A Python standard-library HTTP server serves a generated review dataset and a native HTML/CSS/JavaScript client. Poppler renders requested PDF pages into a cache, while browser decisions remain in localStorage and export as versioned JSON without mutating corpus sources.

**Tech Stack:** Python 3.10+, `unittest`, `http.server`, Poppler `pdftoppm`, HTML, CSS, JavaScript.

## Global Constraints

- Bind only to `127.0.0.1`.
- Dictionary page `n` maps to PDF page `n + 24`.
- Include exactly 131 unique entries carrying 133 issues: 93 cross-type, 27 empty-key, 1 existing-key conflict, and 12 truncated-gloss issues, with two entries carrying both cross-type and truncated-gloss issues.
- Do not modify source CSV, 007 correction tables, generated Markdown, or the source PDF.
- Store drafts in localStorage and export schema-versioned JSON.
- Use mouse wheel zoom centered on the pointer, drag to pan, and double-click to fit width.
- Do not add Node or third-party Python runtime dependencies.

---

### Task 1: Validated Review Data Model

**Files:**
- Create: `scripts/proofread_review/__init__.py`
- Create: `scripts/proofread_review/models.py`
- Test: `scripts/tests/test_proofread_review.py`

**Interfaces:**
- Produces: `ReviewRecord.from_dict(value)`, `ReviewDataset.from_records(records)`, `stable_record_id(value)`, and `validate_decision_export(dataset, payload)`.

- [ ] Write failing tests proving stable IDs are order-independent, duplicates fail closed, page numbers map with `+24`, and stale decision digests are rejected.
- [ ] Run `PYTHONPATH=. python3 -m unittest scripts.tests.test_proofread_review.TestReviewModels -v` and confirm the tests fail because the module is absent.
- [ ] Implement frozen dataclasses, canonical JSON hashing, required-field validation, unique-ID validation, and exact source-digest comparison.
- [ ] Re-run the model tests and confirm they pass.

### Task 2: Build the Exact 131-Entry / 133-Issue Dataset

**Files:**
- Create: `scripts/proofread_review/build_data.py`
- Create: `scripts/proofread_review/review_data.json`
- Modify: `scripts/tests/test_proofread_review.py`

**Interfaces:**
- Consumes: `scripts/proofread_review/review_actions_source.json`, the authoritative merged proofread CSV, and current 007 correction tables.
- Produces: `build_review_dataset(actions_path, proofread_path) -> ReviewDataset` and deterministic `review_data.json`.

- [ ] Write tests that assert exact issue counts `{cross_type: 93, empty_key: 27, existing_key_conflict: 1, truncated_gloss: 12}`, 131 unique records, 133 issues, two multi-issue records, unique IDs, required source/proposal fields, and page 32 to PDF page 56.
- [ ] Run the dataset tests and confirm they fail on the missing builder.
- [ ] Implement deterministic classification from action evidence, preserving full source context and overlap precedence so every action appears at most once.
- [ ] Generate `review_data.json`, run the dataset tests, and inspect representative records from all four categories.

### Task 3: Local Server and PDF Page Cache

**Files:**
- Create: `scripts/proofread_review/server.py`
- Create: `scripts/run_proofread_review.py`
- Modify: `scripts/tests/test_proofread_review.py`

**Interfaces:**
- Consumes: `ReviewDataset`, PDF path, and cache directory.
- Produces: `create_server(dataset_path, pdf_path, cache_dir, host="127.0.0.1", port=0)` and routes `/api/data`, `/api/health`, `/api/page/<number>.jpg`, `/`, `/app.js`, `/styles.css`.

- [ ] Write failing tests for loopback binding, health/data responses, page bounds, page 56 rendering, cache reuse, missing Poppler errors, and rejection of traversal-like paths.
- [ ] Run `PYTHONPATH=. python3 -m unittest scripts.tests.test_proofread_review.TestReviewServer -v` and confirm failure.
- [ ] Implement the HTTP handler, subprocess rendering to a temporary file followed by atomic rename, explicit MIME types, and JSON errors.
- [ ] Implement the CLI with `--pdf`, `--data`, `--cache-dir`, `--port`, and optional browser opening.
- [ ] Run server tests and manually verify page 56 renders from dictionary page 32.

### Task 4: Dense Review Interface

**Files:**
- Create: `scripts/proofread_review/static/index.html`
- Create: `scripts/proofread_review/static/styles.css`
- Create: `scripts/proofread_review/static/app.js`
- Modify: `scripts/tests/test_proofread_review.py`

**Interfaces:**
- Consumes: `/api/data` and `/api/page/<number>.jpg`.
- Produces: localStorage key `proofread-review:<data_version>` and exported schema `proofread-review-decisions/v1`.

- [ ] Add static-contract tests for required landmarks, accessible labels, no inline event handlers, decision schema constant, wheel listener with `preventDefault`, pointer pan, double-click fit, and input-focus shortcut guard.
- [ ] Run static-contract tests and confirm failure before assets exist.
- [ ] Implement the approved dense two-column UI, filters, progress, record navigation, source/proposal choices, editable final values, notes, accepted/deferred states, and persistent error banner.
- [ ] Implement pointer-centered wheel zoom, pointer-capture pan, double-click fit-width, adjacent PDF page navigation, and reset when changing records.
- [ ] Implement localStorage autosave, versioned export/import, source-digest checks, and safe JSON download.
- [ ] Run static-contract tests and browser-test the full review path.

### Task 5: End-to-End Verification and Adoption Entry

**Files:**
- Create: `scripts/proofread_review/README.md`
- Modify: `scripts/tests/test_proofread_review.py`

**Interfaces:**
- Produces: documented command `PYTHONPATH=. python3 scripts/run_proofread_review.py --pdf <path>` and an auditable decision export.

- [ ] Add an integration test that starts the server on an ephemeral port, loads the exact 131-record / 133-issue dataset, fetches page 56, and validates exported accepted/deferred records.
- [ ] Run `PYTHONPATH=. python3 -m unittest scripts.tests.test_proofread_review -v` and fix any failure.
- [ ] Start the real app with the supplied PDF, review representative records from all four categories, and verify refresh persistence plus JSON export/import.
- [ ] Verify desktop and narrow viewport layouts, keyboard focus, readable contrast, zoom/pan behavior, and no horizontal overflow outside the source viewer.
- [ ] Document start, review, backup, import/export, cache, and failure-recovery instructions.
- [ ] Run `git diff --check` and report all created files without staging or committing unrelated worktree changes.
