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

When `script_translator` composes a sentence from individual syllable dict entries, it concatenates their texts without separators (e.g., `tiân` + `sí` → `tiânsí`). To add hyphens, reconstruct the text from `spelling_hints` comment codes via a SYLLABLE_MAP:

```lua
local hw_parts = {}
for code in (cand.comment or ""):gmatch("[%w]+") do
    local hw = SYLLABLE_MAP[code:lower()]
    if hw then table.insert(hw_parts, hw) else hw_parts = {}; break end
end
if #hw_parts > 0 then
    new_text = table.concat(hw_parts, "-")
end
```

Key insight: `cand.comment` (from `spelling_hints`) contains the segmented codes even for auto-composed sentences. Use `ShadowCandidate` to apply the new text.

### Pitfalls
- **Sandbox**: `io` and `os` libraries are restricted in many Rime builds.
- **Memory**: Avoid creating too many tables inside the filter loop.
- **Comment Mapping**: `cand.comment` is the only source of syllable segmentation for synthesized sentences in many schemas. Use it to reconstruct Latin handwriting with hyphens.
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
