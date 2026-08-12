# Proofread Matching Human Review Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable local human-review web workflow to `proofread-matching` for real, ambiguous, deferred, and structural dictionary records while preserving the existing stale-safe accepted-only write-back gate.

**Architecture:** A `review_bundle` adapter serializes existing review records and structural issues into a versioned bundle and re-ingests versioned decisions. A Python standard-library loopback server serves a native web client and optional Poppler-rendered PDF pages; project callers provide PDF path, page field, and page offset as configuration.

**Tech Stack:** Python 3.10+, dataclasses, `unittest`, `http.server`, Poppler `pdfinfo`/`pdftoppm`, HTML, CSS, JavaScript.

## Global Constraints

- Include only real, ambiguous, explicitly deferred, and structural records in the human queue.
- Merge multiple issues sharing one stable review identity into one web record.
- Preserve decision key, rules version, run audit, source digest, evidence, and proposed patches.
- Keep the web app decision-only; apply changes only through `apply_accepted_records`.
- Bind the server only to `127.0.0.1` and allowlist every served route.
- Make PDF support optional and configure it with exact `page_field` and integer `page_offset` values.
- On record change, auto-jump to the mapped page; also support arbitrary valid PDF-page jumps, adjacent-page navigation, and “return to record page”.
- Use Python standard library and existing Poppler commands; add no Node or Python runtime dependency.
- Keep detailed web instructions in `references/human-review-web.md`, not in the already-long `SKILL.md`.
- Do not create or modify Git commits.

---

### Task 1: Versioned Review Bundle and Decision Adapter

**Files:**
- Create: `scripts/proof/review_bundle.py`
- Modify: `scripts/proof/__init__.py`
- Create: `scripts/tests/test_review_bundle.py`

**Interfaces:**
- Consumes: existing `ReviewRecord`, `Decision`, `Patch`, and caller-supplied structural issue mappings.
- Produces: `build_review_bundle(records, *, structural_issues=(), document=None) -> ReviewBundle`, `export_review_bundle(bundle) -> dict[str, object]`, and `ingest_web_decisions(records, bundle, payload) -> DecisionImportResult`.

- [ ] Write failing public-interface tests with literal expected schemas for scope filtering, stable-ID issue merging, document config, decision round-trip, and stale rejection on each binding.
- [ ] Run `python3.12 -m unittest scripts.tests.test_review_bundle -v`; confirm import failure.
- [ ] Implement frozen bundle/document/web-record dataclasses, canonical JSON hashing, deterministic merge order, exact schema validation, and stale-safe decision ingestion.
- [ ] Re-run the bundle tests; require all tests to pass.

### Task 2: Loopback Server and Optional PDF Adapter

**Files:**
- Create: `scripts/review_web/__init__.py`
- Create: `scripts/review_web/server.py`
- Create: `scripts/review_web/cli.py`
- Create: `scripts/tests/test_review_web_server.py`

**Interfaces:**
- Consumes: bundle JSON, optional `DocumentConfig`, decision output path, and cache directory.
- Produces: `create_review_server(bundle_path, *, decisions_path=None, cache_dir, host="127.0.0.1", port=0)` and CLI options `--bundle`, `--decisions`, `--cache-dir`, `--port`, `--no-open`.

- [ ] Write failing tests for loopback binding, health/bundle routes, route allowlisting, decision-file validation, optional-PDF degradation, page bounds, render cache reuse, and atomic cache creation.
- [ ] Run the server tests and confirm import failure.
- [ ] Implement the route handler, JSON errors, optional `PageRenderer`, atomic page cache, and a CLI that prints the final local URL.
- [ ] Run the server tests with a generated small fixture PDF or supplied PDF; require all tests to pass.

### Task 3: Dense Human Review Client

**Files:**
- Create: `scripts/review_web/static/index.html`
- Create: `scripts/review_web/static/styles.css`
- Create: `scripts/review_web/static/app.js`
- Create: `scripts/tests/test_review_web_static.py`

**Interfaces:**
- Consumes: `/api/bundle`, optional `/api/page/<page>.jpg`, and `/api/decisions`.
- Produces: `proofread-review-decisions/v1`, bundle-hash-scoped localStorage drafts, and accepted/rejected/deferred decisions.

- [ ] Write failing static-contract tests for accessible landmarks, field-source choices, custom final values, status controls, bundle hash, stale bindings, wheel listener with `preventDefault`, pointer pan, double-click fit, arbitrary page input, “return to record page”, and record-change auto-jump.
- [ ] Run static tests and confirm missing assets.
- [ ] Implement the approved dense layout with record filters, evidence, per-field source/reference/proposal choices, custom edits, notes, statuses, autosave, import/export, and visible errors.
- [ ] Implement optional PDF mode, pointer-centered wheel zoom, pointer pan, fit-width, arbitrary-page validation, adjacent pages, record-page return, and automatic re定位 on each record change.
- [ ] Run static tests and JavaScript syntax check; require both to pass.

### Task 4: Skill Instructions and Progressive Disclosure

**Files:**
- Modify: `SKILL.md`
- Create: `references/human-review-web.md`
- Modify if present: `agents/openai.yaml`

**Interfaces:**
- Consumes: bundle/server/client commands implemented by Tasks 1–3.
- Produces: a concise human-review branch in the core workflow and a directly linked detailed reference.

- [ ] Update the frontmatter description so human adjudication and review-web requests trigger the skill; preserve user-invocation settings when present.
- [ ] Add a short “Human review web” step after triage with checkable completion criteria and a direct pointer to `references/human-review-web.md`.
- [ ] Write the reference with exact scope rules, bundle/decision schemas, PDF mapping semantics, commands, stale handling, accepted-only write-back, and recovery behavior.
- [ ] Review every new instruction for duplication, weak pointers, hidden must-read rules, and stale command copies; keep each meaning in one place.

### Task 5: Integrated Validation

**Files:**
- Modify: relevant test fixtures only when a failing integrated test requires them.

**Interfaces:**
- Produces: a validated, reusable skill folder with no project-specific 007 paths or field names.

- [ ] Run all `proofread-matching/scripts/tests/test_*.py` tests under Python 3.10+.
- [ ] Start the review server with a fixture bundle and PDF; browser-test record auto-jump, arbitrary page jump, return-to-record, wheel zoom, custom decision, refresh persistence, export/import, and no-PDF degradation.
- [ ] Check desktop and narrow viewport screenshots, console errors, horizontal overflow, focus behavior, and readable evidence density.
- [ ] Run `node --check` on `app.js`, `git diff --check` where applicable, `skill-creator/scripts/quick_validate.py`, and `agent-kit-validator` against the skill folder.
- [ ] Report modified files, verification evidence, adoption command, and any remaining limitations without staging or committing.
