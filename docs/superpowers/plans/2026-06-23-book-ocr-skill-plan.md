# Book OCR Skill Implementation Plan

> **For agentic workers:** Use subagent-driven-development or executing-plans to implement task-by-task.

**Goal:** Build a CLI (`book-ocr`) that ingests a PDF URL or page images, samples pages to auto-detect layout, runs marker-pdf OCR with resume, and merges to `merged.md` with page markers.

**Architecture:** Skill at `wiki/skills/book-ocr/` (symlinked to `~/.agents/skills/`). Python package `book_ocr/` with strategy pattern (`skip` / `simple` / `grid`). CLI: `plan | run | merge | status`. Workspace files drive resumability.

**Tech Stack:** Python 3.10+, marker-pdf, surya-ocr, scipy, PyMuPDF, Pillow, requests. unittest.

**Design doc:** `code/dataset/docs/2026-06-23-book-ocr-skill-design.md`

**Cross-repo note:** Skill code in `wiki/` repo. This plan in `code/dataset/`. Wiki commits: update `notes/journal.md` → `git add` → `git commit` → `git pull --rebase` → `git push`.

---

### Task 1: Scaffold skill directory + SKILL.md + symlink

**Files to create:**
- `wiki/skills/book-ocr/SKILL.md` — frontmatter + 4-phase mermaid + CLI block + agent trigger table + references list
- `wiki/skills/book-ocr/scripts/requirements.txt` — marker-pdf, scipy, PyMuPDF, Pillow, requests
- `wiki/skills/book-ocr/scripts/tests/fixtures/.gitkeep`
- `wiki/skills/book-ocr/references/{strategies,plan-schema,failure-modes}.md` — each = "Filled in Task 14."
- Symlink: `~/.agents/skills/book-ocr` → `/home/ubuntu/floating-cloud/wiki/skills/book-ocr`

**Commit:** `feat(skills): scaffold book-ocr skill`

---

### Task 2: Plan I/O (`book_ocr/plan.py`)

**Files to create:**
- `book_ocr/__init__.py` (empty)
- `book_ocr/plan.py`
- `tests/__init__.py` (empty)
- `tests/test_plan.py`

**Interfaces:**
- `PageGroup(range, kind, columns=None, has_rule_lines=False, has_row_lines=False, reason=None)` — dataclass
- `Plan(slug, meta, sampled_pages, page_groups, postprocessing, confidence, note)` — dataclass with `.write(path)`, `Plan.read(path)`
- `expand_range(spec: str) -> list[int]` — `"23"` or `"1-3"`
- `expand_pages_spec(spec: str) -> list[int]` — `"23,187,300-302"`
- `expand_groups(groups: list[PageGroup]) -> dict[int, PageGroup]`

**Test points:** single page, range, mixed spec, invalid range raises, PageGroup round-trip, Plan JSON round-trip.

**Commit:** `feat(book-ocr): plan.py — Plan/PageGroup dataclasses and JSON I/O`

---

### Task 3: Strategy ABC + `skip` strategy

**Files:**
- `book_ocr/strategies/__init__.py`
- `book_ocr/strategies/base.py` — `class Strategy(ABC): name; detect(image_path) -> float; ocr(...) -> str`
- `book_ocr/strategies/skip.py` — detect: dark pixel ratio < 1% → 1.0; ocr: returns ""
- `tests/test_strategies.py`

**Test points:** SkipStrategy.detect on purely white page ≥ 0.9; on fully dark page ≤ 0.5; .ocr returns "".

**Commit:** `feat(book-ocr): Strategy ABC + SkipStrategy`

---

### Task 4: `simple` strategy

**Files:**
- `book_ocr/strategies/simple.py`
- Extend `tests/test_strategies.py`

**Interfaces:** `SimpleStrategy`. detect: surya text-detection → count wide boxes (width > page_width * 0.7) / total boxes → ratio. ocr: module-level lazy `PdfConverter` (default config, `extract_images=False`). Image → temporary single-page PDF → converter → `text_from_rendered`.

**Test points:** skipped if no fixture.

**Commit:** `feat(book-ocr): SimpleStrategy`

---

### Task 5: `grid` strategy — detection

**Files:**
- `book_ocr/strategies/grid.py` (detection only)
- Extend `tests/test_strategies.py`

**Interface:** `detect_grid(image_path) -> GridParams(columns, has_rule_lines, column_x, confidence)`

**Algorithm:** dark-pixel column projection → scipy `maximum_filter1d` → search best equally-spaced N-line grid (N=1..5, spacing 60-200px). If peak-score ≥ 0.35 → rules detected. Fallback: surya text-detection → cluster x-centers with equal-boundary heuristic for k=2..6 → pick best k by within-cluster variance.

**Test points:** skipped if no fixture. No ImportError.

`GridStrategy.ocr` raises `NotImplementedError` (implemented in Task 6).

**Commit:** `feat(book-ocr): GridStrategy detection`

---

### Task 6: `grid` strategy — OCR

**Files:**
- Modify `book_ocr/strategies/grid.py` — replace NotImplementedError in `GridStrategy.ocr`
- Extend `tests/test_strategies.py`

**Algorithm:** detect grid (or use passed params). Crop to each column slice (or column×row cell if has_row_lines). For each cell: save temp webp → marker `PdfConverter` with `{force_ocr=True, force_layout_block="Text"}`, filtering TableProcessors. Period cell output. Concat: no row lines → column-major; has row lines → markdown table. Module-level lazy converter.

**Test points:** skipped if no fixture. No ImportError.

**Commit:** `feat(book-ocr): GridStrategy OCR`

---

### Task 7: Postprocess simple rules

**Files:**
- `book_ocr/postprocess.py`
- `tests/test_postprocess.py`

**Interfaces (all `(text: str) -> str`):**
- `sup_tags` — `<sup>N</sup>` → Unicode superscript
- `ocr_error_letters` — `<sup>[liî]</sup>` → `¹`
- `apply_page_marker(text, page_num)` — prepend `<!-- page:N -->\n\n`
- `RULES` dict registry mapping rule-id → callable

**Test points:** sup single digit, sup multi-digit, OCR error letters, page marker. Registry contains expected keys.

**Commit:** `feat(book-ocr): postprocess simple rules`

---

### Task 8: Postprocess `latex-math` rule

**Files:**
- Modify `book_ocr/postprocess.py`
- Extend `tests/test_postprocess.py`

**Algorithm on `$...$` blocks (in order):**
1. `\textbf{X}`, `\text{X}` → X
2. `{\rm X}`, `{\bf X}`, `{\it X}`, `{\sf X}`, `{\tt X}` → X
3. `\overline{X}`, `\underline{X}`, `\dot{X}`, `\hat{X}`, `\bar{X}`, `\tilde{X}`, `\vec{X}` → X
4. `\mathbf{X}`, `\mathsf{X}`, `\mathit{X}`, `\mathrm{X}`, `\mathcal{X}` → X
5. Symbol map (`\Box`→`☐`, etc.)
6. `^N` / `^{N}` → sup; `^{...}` → unwrap
7. `_N` / `_{N}` → sub; `_{...}` → unwrap
8. Residual `\command` → command

Implementation mirrors `wiki/tech/ocr-superscript-postprocessing.md` exactly.

**Test points:** `\mathbf{a}^1`, nested `\dot{\textbf{m}}`, `\Box^2`, `\overline{\rm NN}^2`, subscript, idempotency.

**Commit:** `feat(book-ocr): postprocess latex-math rule`

---

### Task 9: Phase 1 ingest

**Files:**
- `book_ocr/ingest.py`
- `tests/test_ingest.py`

**Interfaces:**
- `download_pdf(url, dest: Path) -> Path` — stream `requests.get` → `.partial` suffix → atomic rename. Existing complete = no-op.
- `render_pages(pdf_path, out_dir, dpi=300, quality=85) -> int` — PyMuPDF per-page render to `NNNN.webp`. Existing non-empty = skip. Returns total pages.
- `write_meta(workspace, total_pages, source_url, dpi)` — writes `meta.json`

**Test points:** download skips existing, atomic rename, write_meta JSON structure. `render_pages` exercised in smoke test only.

**Commit:** `feat(book-ocr): Phase 1 ingest`

---

### Task 10: Phase 2 sample + plan generation

**Files:**
- `book_ocr/sample.py`
- `tests/test_sample.py`

**Interfaces:**
- `sample_pages(total, n=8, skip_pct=0.05)` — returns sorted page numbers avoiding first/last skip_pct
- `classify_page(image_path, strategies) -> (kind, params)` — run all strategies, pick highest confidence
- `aggregate_ranges(per_page_kinds: dict, total) -> list[PageGroup]` — collapse consecutive same-kind
- `make_plan(workspace, slug, total, source_url, dpi) -> Plan` — orchestrates: sample → classify sample pages → aggregate ranges → write plan.json + sample webps/mds

**Test points:** sample_pages avoids edges, returns right count, sorted. aggregate_ranges collapses correctly.

**Commit:** `feat(book-ocr): Phase 2 sampling and plan generation`

---

### Task 11: Phase 3 batch_ocr

**Files:**
- `book_ocr/batch_ocr.py`
- `tests/test_batch_ocr.py`

**Interfaces:**
- `load_state(workspace) -> (completed: set[int], failed: dict[int, str])` — reads state.json if exists
- `save_state(workspace, completed, failed)` — writes state.json
- `run_plan(plan, workspace, strategies, timeout=300)` — for each page in plan: skip if `md/NNNN.md` exists; classify using plan's page_groups; call strategy.ocr; write md/NNNN.md; update state. Timeout per page via `signal.alarm(timeout)`.

**Test points:** state read/write round-trip, run_plan skips completed pages (mocked strategies).

**Commit:** `feat(book-ocr): Phase 3 batch OCR with checkpoint resume`

---

### Task 12: Phase 4 merge

**Files:**
- Modify `book_ocr/postprocess.py` (add `merge_pages`)
- `tests/test_postprocess.py`

**Interface:** `merge_pages(workspace, plan) -> Path` — for each page_num in plan: read `md/NNNN.md` (empty if `skip` kind) → apply `apply_page_marker(text, page_num)` → apply each rule in `plan.postprocessing` via `RULES` dict → concat into `merged.md`. Returns `merged.md` path.

**Rule application order:** `sup-tags → ocr-error-letters → latex-math`. `page-marker` applied per-page before concatenation, not globally.

**Test points:** merge on minimal workspace produces correct page markers and rule output.

**Commit:** `feat(book-ocr): Phase 4 merge with postprocess pipeline`

---

### Task 13: CLI dispatch + `--images` mode

**Files:**
- `book_ocr/__main__.py`
- `book_ocr/cli.py`
- `tests/test_cli.py`

**Subcommands:**
- `plan --pdf-url URL --slug SLUG [--workspace DIR] [--samples N]` → ingest + sample + make_plan
- `plan --images GLOB --slug SLUG [--workspace DIR]` → skip ingest, use images as pages/ → sample + make_plan
- `run --slug SLUG [--workspace DIR] [--pages SPEC]` → load plan, batch_ocr.run; if `--pages` specified, only those (via `expand_pages_spec`)
- `merge --slug SLUG [--workspace DIR]` → merge_pages
- `status --slug SLUG [--workspace DIR]` → print state stats

**Workspace resolution:** `workspace = (args.workspace or Path.cwd() / "tmp" / "ocr" / args.slug)`.
`PYTHONPATH` setup in `__main__.py` so `python3 -m book_ocr` works.

**Test points:** argparse parses subcommands correctly; workspace path logic.

**Commit:** `feat(book-ocr): CLI dispatch with 5 subcommands`

---

### Task 14: Fill reference docs

**Files to update:**
- `references/strategies.md` — condensed from design doc §「頁面形態（kind）分類」 + §「技術棧」。One paragraph per kind: what it detects, how, what config it uses. Include the grid detection algorithm summary and note about marker TableProcessor filtering.
- `references/plan-schema.md` — show `plan.json` example (from design doc) with field-by-field explanation. Include `expand_range` behavior rules (start ≤ end, comma-separated).
- `references/failure-modes.md` — table from design doc §「失敗模式」, copied verbatim.

**Commit:** `docs(book-ocr): fill reference documents`

---

### Task 15: Smoke test end-to-end

Pick a short public-domain PDF (< 50 pages), e.g. `Primary_Lessons_in_Swatow_Grammar` (source_id=8) or `要理問答` (source_id=17). Run:

```bash
cd /home/ubuntu/floating-cloud/wiki/skills/book-ocr/scripts
python3 -m book_ocr plan --pdf-url "https://archive.org/download/..." --slug smoke-test
# review plan.json
python3 -m book_ocr run --slug smoke-test
# check md/NNNN.md exist
python3 -m book_ocr merge --slug smoke-test
# check merged.md exists with page markers
```

List any issues discovered as comments in `merged.md` or a companion `smoke-test-notes.md`.

**Commit:** `test(book-ocr): smoke test on [book-name]`

---

### Task 16: Update dataset AGENTS.md + merge branch

**Files:**
- Modify `code/dataset/AGENTS.md` — add entry in 「Project Skills」 section referencing the wiki skill path and the design doc
- Commit and push `feature/20260623/book-ocr-skill`
- Create PR or merge into `main` unilaterally (per dataset workflow)

**Commit:** `docs: reference book-ocr skill in AGENTS.md`

---

### Self-Review Checklist

1. **Spec coverage:** Every section of the design doc maps to ≥ 1 task: 4 phases (T9-12), 3 kind matrix (T3-6), postprocess rules (T7-8), CLI (T13), plan.json (T2), failure modes (T14). ✓
2. **Placeholder scan:** No "TODO" / "TBD" / "implement later". Each task has interface signatures, files, and test points. ✓
3. **Type consistency:** `PageGroup` / `Plan` / `GridParams` names and fields match between T2, T5, T10, T11. ✓
4. **Task independence:** Each task produces testable output; no task depends on uncommitted code from later tasks. ✓