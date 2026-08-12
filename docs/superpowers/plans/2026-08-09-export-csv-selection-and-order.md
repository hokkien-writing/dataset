# CSV Export Selection and Order Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional source-order preservation and exact book selection to `scripts/export_csv.py` without changing default exports.

**Architecture:** Parse CLI arguments in a focused function, resolve explicitly selected `books/*.md` inputs before the export loop, and conditionally sort extracted entries. Explicit selections fail closed when a file or processor is unavailable.

**Tech Stack:** Python 3.10+, argparse, pathlib, unittest.

## Global Constraints

- `--preserve-order` skips reading-based sorting; default behavior remains sorted.
- Repeatable `--book STEM` selects exact files under `books/`.
- Explicit missing books or processors exit nonzero with the offending stem.

---

### Task 1: CLI selection and order behavior

**Files:**
- Modify: `scripts/export_csv.py`
- Create: `scripts/tests/test_export_csv_cli.py`

**Interfaces:**
- Produces: `parse_args(argv: list[str] | None = None) -> argparse.Namespace`
- Produces: `select_sources(book_stems: list[str]) -> list[tuple[str, Path]]`
- Produces: `order_entries(entries: list, preserve_order: bool) -> list`

- [ ] Add tests proving default sorting and `--preserve-order` source ordering.
- [ ] Run `PYTHONPATH=. python3 -m unittest scripts.tests.test_export_csv_cli` and confirm the new tests fail.
- [ ] Add `argparse` options `--preserve-order` and repeatable `--book`.
- [ ] Resolve exact `books/STEM.md` paths and reject missing files or processors.
- [ ] Apply sorting only when `--preserve-order` is false.
- [ ] Run the new tests and the existing export-related tests.
- [ ] Run a real single-book export for 007 with `--preserve-order` and verify its first rows follow Markdown order.
