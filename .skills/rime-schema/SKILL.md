---
name: rime-schema
description: Creating, modifying, or debugging Rime schemas (.schema.yaml), dictionaries (.dict.yaml), and Lua scripts.
---

# Rime Schema Writing

## Overview
Rime uses YAML files for configuration. A **schema** (`.schema.yaml`) defines the engine pipeline; a **dictionary** (`.dict.yaml`) provides the code table.

## Dictionary Format
```yaml
# Rime dictionary: my_dict
---
name: my_dict
...
文字	code1 code2	100
```
- **Tab-separated**: `text[TAB]code[TAB]weight`.
- **Multi-syllable**: Space-delimited codes.
- **Import**: `import_tables` merges other dicts.

## Spelling Algebra
Transforms dictionary codes into user-typable forms (not the reverse).
- `xform/pat/repl/`: Destructive rewrite.
- `derive/pat/repl/`: Add variant (keeps original).
- `abbrev/pat/repl/`: Low-priority shorthand.
- **Rule**: Longer patterns (e.g., `tsh`) must come before shorter ones (`ts`).

## Lua Integration
Exported in `rime.lua`, referenced via `lua_filter@name` or `lua_translator@name`.

### Preserving User Dictionary Learning
When modifying candidate text in a Lua filter:
1. **`cand.text` is Read-Only**: To change text, you **must** use `ShadowCandidate` to wrap the original candidate.
2. **Use `ShadowCandidate`**: Using `Candidate(...)` creates a brand new candidate and severs the internal pointer to Rime's `Phrase` engine, preventing the user dictionary from learning it. Instead, use `ShadowCandidate(cand, cand.type, new_text, cand.comment)`.
3. **Boost Priority**: If promoting a reconstructed phrase, manually increase `quality` (e.g., `+100`) on the new shadow candidate.

```lua
local function yield_item(item)
    if item.text_changed then
        -- ShadowCandidate preserves the internal Phrase reference for user_dict learning
        local c = ShadowCandidate(item.cand, item.type, item.text, item.comment)
        c.quality = item.cand.quality + 100
        yield(c)
    else
        yield(item.cand)
    end
end
```

### Tone-Aware Filtering
Rime's user dictionary fuzzy matching is aggressive. When the user types explicit tones/separators, use the Lua filter to discard mismatches:
- Compare the input syllables (e.g., `tai5`) with the candidate's codes (e.g., `tai6`).
- If tones are present in input but don't match the candidate, discard the candidate to prevent noise.

## Debugging Checklist
1. **YAML Indentation**: Never use tabs in the structure (only in the dict code table).
2. **Alphabet**: Must include every character used in dictionary codes (digits, hyphens, caps).
3. **Deployment**: Always click "Deploy" after modifying any file.
4. **Logs**: Check `build/` folder for syntax errors; check `/tmp/rime.*` for engine logs.

### Log Locations (macOS / Squirrel)

Logs are in `/private/var/folders/.../T/rime.squirrel/`.

| File | Content |
|------|---------|
| `rime.squirrel.INFO` | Deployment info, schema loading |
| `rime.squirrel.WARNING` | Duplicate dict entries, non-fatal issues |
| `rime.squirrel.ERROR` | YAML parse errors, missing files, Lua failures |

Symlinks point to timestamped files.

### Lua Module Return Shape

`rime.lua` does `local mod = require('name')` then assigns `name = mod.filter` etc. The Lua module **must** return a flat table:

```lua
-- ✓ Correct: flat table
return { processor = proc, filter = filt, translator = trans }

-- ✗ Wrong: double-nested — mod.filter will be nil
return {{ processor = proc, filter = filt, translator = trans }}
```

If `mod.filter` is nil, Rime silently skips the filter/translator — no candidates appear and no error is logged.

### Auto-Composed Sentence Hyphens

When `script_translator` composes a sentence from individual syllable dict entries, it concatenates their texts without separators (e.g., `tiân` + `sí` → `tiânsí`). To restore hyphens, walk the **user's input** for separator positions and use **comment codes** (from `spelling_hints`) for SYLLABLE_MAP lookup:

```lua
-- Comment codes = LATN_NORM format (matches SYLLABLE_MAP keys)
-- User input = schema romanization (may differ, e.g. PUJ "hoan5" vs LATN_NORM "huan5")
local codes = {}
for code in (cand.comment or ""):gmatch("[%w]+") do
    table.insert(codes, code:lower())
end
local new_text = ""
local i, code_idx, valid = 1, 1, true
while i <= #input do
    local token = input:match("^[%w]+", i)
    if token then
        local hw = nil
        local ci = code_idx
        while ci <= #codes do
            hw = SYLLABLE_MAP[codes[ci]]
            if hw then code_idx = ci + 1; break end
            ci = ci + 1
        end
        if not hw then hw = SYLLABLE_MAP[token:lower()] end
        if not hw then valid = false; break end
        new_text = new_text .. hw
        i = i + #token
    else
        local sep = input:match("^[^%w]+", i)  -- preserves -, --, etc.
        if sep then new_text = new_text .. sep; i = i + #sep
        else new_text = new_text .. input:sub(i, i); i = i + 1 end
    end
end
if not valid then new_text = cand.text end
```

Why not just use comment codes with `table.concat(parts, "-")`?
- That only handles single `-` and can't distinguish `-` from `--`
- User input may use different romanization than SYLLABLE_MAP keys (e.g. `hoan5` in PUJ vs `huan5` in LATN_NORM)

### Tone-Number-Aware Candidate Ordering

When the user types explicit tone numbers, Latin candidates should be prioritized over Han candidates. Sort by input coverage (`_end - start`) so full-input matches come before partial ones:

```lua
local has_digits = (ctx.input or ""):match("%d") ~= nil
local latin_first = has_caps or has_digits
-- ... collect latin_items / han_items when latin_first ...
if latin_first then
    table.sort(latin_items, function(a, b)
        return (a._end - a.start) > (b._end - b.start)
    end)
    for _, c in ipairs(latin_items) do yield(c) end
    -- then yield han_items
end
```

### Pitfalls
- **Sandbox**: `io` and `os` libraries are restricted in many Rime builds.
- **Memory**: Avoid creating too many tables inside the filter loop.
- **Comment vs Input**: User input determines separators (`-`/`--`); comment codes (LATN_NORM) determine handwriting lookup. Never mix the two purposes.
- **Silent Lua failures**: If a `lua_filter`/`lua_translator`/`lua_processor` name doesn't resolve to a callable, Rime logs nothing and shows no candidates. Always verify `rime.lua` exports match schema references.
- **Silent `cand.text` write**: Assigning `cand.text = x` in a Lua filter does **not** produce an error but silently fails — the displayed text remains unchanged. Always use `ShadowCandidate` to change candidate text.

## Official Reference

| Doc | URL | When to Read |
|-----|-----|-------------|
| Schema.yaml 詳解 | https://github.com/LEOYoon-Tsaw/Rime_collections/blob/master/Rime_description.md | **Any schema question** — exhaustive setting reference |
| Rime with Schemata | https://github.com/rime/home/wiki/RimeWithSchemata | Learning schema architecture, engine pipeline, dictionary format |
| Customization Guide | https://github.com/rime/home/wiki/CustomizationGuide | Writing `.custom.yaml` patches, fuzzy pinyin, key bindings |
| Spelling Algebra | https://github.com/rime/home/wiki/SpellingAlgebra | `xform`/`derive`/`abbrev`/`fuzz`/`xlit`/`erase` operators |
| User Guide | https://github.com/rime/home/wiki/UserGuide | End-user operations, dictionary management |
