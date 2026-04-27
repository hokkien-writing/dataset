# Candidate Display Refactor Design

Date: 2026-04-27

## Problem

The current Lua filter in `LUA_FILTER_TEMPLATE` (`scripts/export_rime.py`) is overly complex. It contains `apply_user_separators`, `codes_to_handwriting`, coverage-based dedup grouping, and tone-mismatch filtering — all tangled together. The `exact_translator` and filter dedup logic interact in fragile ways. Candidate display needs to be simplified to three clean input modes.

## Goals

1. **Toneless input** (e.g. `thien khi`): Show candidates ordered by weight from `script_translator` (Han) and `latn_translator` (handwritten Latin), mixed together by weight.
2. **Tone-bearing input** (e.g. `thien1-khi2`): Exact-match handwritten Latin via `SYLLABLE_MAP` takes top priority. Other candidates still appear below, ordered by weight.
3. **Abbreviated input** (e.g. `tk` → 天氣): Support first-letter-per-syllable abbreviation via Rime `abbrev` algebra rules. No Lua code needed.
4. **User dictionary learning**: All user selections must update `user_dict` weights, regardless of input mode.

## Input Modes

| Mode | Example | Candidate Sources |
|------|---------|-------------------|
| Toneless | `thien khi` | `script_translator` + `latn_translator`, ordered by weight |
| Tone-bearing | `thien1-khi2` | `exact_translator` (SYLLABLE_MAP, highest priority) + `script_translator`/`latn_translator` |
| Abbreviated | `tk` | Rime `abbrev` algebra expands to full syllables, then `script_translator` + `latn_translator` |

Abbreviated input is toneless-only. Mixed tone+abbrev (e.g. `tk2`) is not supported.

## Candidate Display

- **Han candidates**: text = 漢字, comment = handwritten Latin (converted via `SYLLABLE_MAP`)
- **Latin candidates**: text = handwritten Latin, comment = empty
- Both types are mixed and ordered by weight. No grouping by script type.

## Architecture

### Delete from `LUA_FILTER_TEMPLATE`

- `codes_to_handwriting` — only needed for Han comment, will be replaced by simpler inline conversion
- `apply_user_separators` — handwritten Latin candidates now come directly from `latn_translator`, no reconstruction needed
- Coverage-based dedup grouping (`yield_item`, coverage tracking) — replaced by weight-based mixed ordering
- Tone-mismatch filtering (`is_perfect` check) — simplified: exact candidates are only produced by `exact_translator` which already guarantees valid mapping

### Keep

- `SYLLABLE_MAP` — used by `exact_translator` and Han comment conversion
- `processor` (`_caps_mask`) — uppercase tracking, preserved as-is
- `is_han_char` — filter needs to distinguish Han vs Latin candidates
- `exact_translator` — unchanged, only activates when input contains digits or hyphens

### Rewrite: `filter`

Simplified logic:

1. Iterate all candidates from translators
2. Classify as Han or Latin via `is_han_char`
3. Han candidates: convert comment (space-separated LATN_NORM syllable codes from `spelling_hints`) to handwritten Latin using `SYLLABLE_MAP` — look up each code, join with `-`
4. Latin candidates: keep text as-is, clear comment
5. Apply first-letter capitalization based on `_caps_mask`
6. Tone-bearing input: `exact`-type candidates get high quality; when a `latn_translator` candidate has the same text, prefer it (preserves user_dict link)
7. Yield all candidates, ordered by weight

### Module Return

Unchanged:

```lua
return { processor = processor, filter = filter, translator = exact_translator }
```

### Speller Algebra: Abbreviated Input

Add `abbrev` rule to each system's speller algebra in `SCHEMA_TEMPLATE`:

```yaml
algebra:
    # ... existing rules ...
    - abbrev/^([a-z]).+$/$1/
```

`abbrev` is additive — it creates alternative spellings without removing the originals. This lets Rime's built-in `script_translator` and `latn_translator` handle abbreviation matching natively. No Lua code required.

### User Dictionary Learning

- Toneless and abbreviated inputs: candidates from `script_translator` and `latn_translator` are `Phrase` objects with user_dict links. Selections update weights automatically.
- Tone-bearing inputs: `exact_translator` creates plain `Candidate` objects without user_dict links. The filter ensures that when a `latn_translator` candidate produces the same text, the exact candidate is suppressed so the user_dict-capable version is selected.

## Files Changed

| File | Change |
|------|--------|
| `scripts/export_rime.py` | Rewrite `LUA_FILTER_TEMPLATE` filter function; add `abbrev` rule to `SCHEMA_TEMPLATE` |
| `export/rime/rime-{hokkien,teochew}/*.lua` | Regenerated |
| `export/rime/rime-{hokkien,teochew}/*.schema.yaml` | Regenerated with updated algebra |

## Out of Scope

- `_caps_mask` global state sharing across schemas (known issue, separate fix)
- `COMMENT_FORMAT` dict (existing dead code)
- Changes to `SYLLABLE_MAP` generation
- Changes to `rime.lua` generator
