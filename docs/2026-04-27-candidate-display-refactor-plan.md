# Candidate Display Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the Lua filter and add abbrev algebra rules to simplify candidate display into three clean input modes (toneless, tone-bearing, abbreviated).

**Architecture:** Delete `codes_to_handwriting`, `apply_user_separators`, and coverage-grouping logic from `LUA_FILTER_TEMPLATE`. Rewrite `filter` to a simple pass-through that formats Han comments and clears Latin comments. Add `abbrev` rule to `SYSTEM_ALGEBRA` for each system. Keep `exact_translator`, `processor`, and `is_han_char` unchanged.

**Tech Stack:** Python (export_rime.py), Lua (generated filter modules), YAML (generated schemas)

---

### Task 1: Rewrite `filter` function in `LUA_FILTER_TEMPLATE`

**Files:**
- Modify: `scripts/export_rime.py:928-1061` (the `filter` function body)

- [ ] **Step 1: Replace the entire filter function (lines 928-1061) with the simplified version**

Replace from `local function filter(translation, env)` through the closing `end` (before `local function exact_translator`) with:

```lua
local function filter(translation, env)
    local ctx = env.engine.context
    local input = ctx.input or ""
    local caps = _caps_mask
    local has_caps = caps:sub(1, 1) == "U"
    local has_tones = input:match("[%d%-]") ~= nil

    if has_tones then
        local latn_texts = {}
        local items = {}

        for cand in translation:iter() do
            local is_han = is_han_char(cand.text)

            if is_han then
                local comment = cand.comment or ""
                local hw = comment:gsub("[%w]+", function(code)
                    return SYLLABLE_MAP[code:lower()] or code
                end)
                hw = hw:gsub("   ", "--")
                hw = hw:gsub("  ", "-")
                cand.comment = hw
                table.insert(items, { cand = cand, is_exact = false })
            else
                if cand.type ~= "exact" then
                    latn_texts[cand.text] = true
                end
                if has_caps then
                    cand.text = capitalize_first(cand.text)
                end
                cand.comment = ""
                table.insert(items, { cand = cand, is_exact = cand.type == "exact" })
            end
        end

        for _, item in ipairs(items) do
            if item.is_exact and latn_texts[item.cand.text] then
                -- skip: user_dict-capable candidate with same text exists
            else
                yield(item.cand)
            end
        end
    else
        for cand in translation:iter() do
            if is_han_char(cand.text) then
                local comment = cand.comment or ""
                local hw = comment:gsub("[%w]+", function(code)
                    return SYLLABLE_MAP[code:lower()] or code
                end)
                hw = hw:gsub("   ", "--")
                hw = hw:gsub("  ", "-")
                cand.comment = hw
            else
                if has_caps then
                    cand.text = capitalize_first(cand.text)
                end
                cand.comment = ""
            end
            yield(cand)
        end
    end
end
```

- [ ] **Step 2: Delete `codes_to_handwriting` function (lines 839-848)**

Delete the entire function. It is no longer called — Han comment conversion is now inline in the filter.

- [ ] **Step 3: Delete `apply_user_separators` function (lines 850-918)**

Delete the entire function. It is no longer called.

- [ ] **Step 4: Run existing tests to verify nothing breaks**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_export_rime -v`
Expected: All tests PASS. Tests don't exercise Lua output directly, so they should pass unchanged.

- [ ] **Step 5: Commit**

```bash
git add scripts/export_rime.py
git commit -m "refactor: rewrite Lua filter, delete codes_to_handwriting and apply_user_separators"
```

---

### Task 2: Add `abbrev` rule to `SYSTEM_ALGEBRA` for all systems

**Files:**
- Modify: `scripts/export_rime.py:474-545` (`SYSTEM_ALGEBRA` dict)

- [ ] **Step 1: Add `abbrev` rule to each system's algebra list**

Rime's `abbrev` operator creates an alias: `abbrev/pattern/replacement/` means "also accept `replacement` as input for entries whose code matches `pattern`". To support first-letter-per-syllable abbreviation (e.g. `tk` → 天氣), add `abbrev/^([a-z]).+$/$1/` which creates single-letter aliases for every syllable. Input `tk` is then segmented as `t` + `k` (via delimiter), matching all syllables starting with `t` and `k`.

For each system in `SYSTEM_ALGEBRA` (`puj`, `poj`, `tl`, `bp`, `dp`), change the trailing `+ CASE_FOLD,` to `+ CASE_FOLD + ["abbrev/^([a-z]).+$/$1/"],`.

Example — `puj` becomes:
```python
"puj": [
    "derive/ /-/",
    "derive/[1-8]//",
    "derive/ch/ts/",
    "derive/chh/tsh/",
    "derive/oinn/ainn/",
    "derive/nn//",
]
+ CASE_FOLD
+ [
    "abbrev/^([a-z]).+$/$1/",
],
```

Apply this same pattern to all five systems (`puj`, `poj`, `tl`, `bp`, `dp`).

- [ ] **Step 2: Run tests**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_export_rime -v`
Expected: All tests PASS.

- [ ] **Step 3: Build and verify schema output contains abbrev rule**

Run: `PYTHONPATH=. python3 scripts/export_rime.py`
Then check a generated schema:
```bash
grep abbrev export/rime/rime-teochew/teochew_puj.schema.yaml
```
Expected: Output contains `abbrev/^([a-z]).+$/$1/`

- [ ] **Step 4: Commit**

```bash
git add scripts/export_rime.py
git commit -m "feat: add abbrev algebra rule for first-letter-per-syllable input"
```

---

### Task 3: Build, deploy, and manual test

**Files:** None (verification only)

- [ ] **Step 1: Full build**

Run: `bash build.sh`
Expected: Completes without errors.

- [ ] **Step 2: Deploy to Rime**

Run: `bash rime_deploy.sh`
Expected: Files copied to `~/Library/Rime/`.

- [ ] **Step 3: Manual verification — three input modes**

Test in any text editor with the Rime input active (PUJ or DP schema):

1. **Toneless input**: Type `thien khi` → Expect Han candidates (天氣 etc.) with handwritten Latin comments, and Latin candidates without comments, all mixed by weight.

2. **Tone-bearing input**: Type `thien1-khi2` → Expect exact handwritten match at top (e.g. `thien-khí`), other candidates below. No duplicate exact+latn entries for same text.

3. **Abbreviated input**: Type `tk` → Expect candidates like 天氣 appearing via abbreviation expansion.

4. **User dict learning**: Select a candidate from abbreviated input, then type `tk` again → Expect the previously selected candidate to have higher rank.

- [ ] **Step 4: Commit any fixes if needed**
