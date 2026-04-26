---
name: rime-schema
description: Use when creating, modifying, or debugging Rime input schema files (.schema.yaml), dictionary files (.dict.yaml), customization patches (.custom.yaml), Lua scripts (lua_filter/lua_translator/lua_processor), or spelling algebra rules. Also use when Rime deployment fails or candidates don't appear as expected.
---

# Rime Schema Writing

## Overview

Rime is an input method framework where YAML text files define entire input schemes. A **schema** (`.schema.yaml`) declares the engine pipeline; a **dictionary** (`.dict.yaml`) provides the code table. Spelling algebra transforms between user keystrokes and dictionary codes.

## When to Use

- Creating/modifying `.schema.yaml`, `.dict.yaml`, `.custom.yaml`
- Writing Lua extensions (`lua_filter`, `lua_translator`, `lua_processor`)
- Designing `speller/algebra` rules
- Debugging deployment failures or missing candidates

## Official Reference (Read These First)

| Doc | URL | When to Read |
|-----|-----|-------------|
| Schema.yaml 詳解 | https://github.com/LEOYoon-Tsaw/Rime_collections/blob/master/Rime_description.md | **Any schema question** — exhaustive setting reference |
| Rime with Schemata | https://github.com/rime/home/wiki/RimeWithSchemata | Learning schema architecture, engine pipeline, dictionary format |
| Customization Guide | https://github.com/rime/home/wiki/CustomizationGuide | Writing `.custom.yaml` patches, fuzzy pinyin, key bindings |
| Spelling Algebra | https://github.com/rime/home/wiki/SpellingAlgebra | `xform`/`derive`/`abbrev`/`fuzz`/`xlit`/`erase` operators |
| User Guide | https://github.com/rime/home/wiki/UserGuide | End-user operations, dictionary management |

## File Types

| File | Naming | Purpose |
|------|--------|---------|
| Schema | `<id>.schema.yaml` | Engine pipeline + speller + translator config |
| Dictionary | `<name>.dict.yaml` | Tab-separated `text→code→weight` table |
| Custom patch | `<id>.custom.yaml` | Override schema without modifying original |
| Global patch | `default.custom.yaml` | Schema list, menu, hotkeys |
| Lua loader | `rime.lua` | `require()` + export Lua modules |
| Lua module | `lua/<name>.lua` | Custom filter/translator/processor |

## Schema Skeleton

```yaml
# Rime schema: my_schema

schema:
  schema_id: my_schema
  name: "My Schema"
  version: "1.0"
  author:
    - "Author"

engine:
  processors:
    - ascii_composer
    - speller
    - punctuator
    - selector
    - navigator
    - express_editor
  segmentors:
    - abc_segmentor
    - punct_segmentor
    - fallback_segmentor
  translators:
    - script_translator
  filters:
    - uniquifier

speller:
  alphabet: zyxwvutsrqponmlkjihgfedcba
  delimiter: " '"
  algebra:
    - derive/[0-9]//

translator:
  dictionary: my_dict
  enable_completion: true
  enable_sentence: true
```

### Multiple Translators

Use `@name` suffix for additional translators (e.g., romanization output alongside Han):

```yaml
engine:
  translators:
    - script_translator
    - script_translator@latn

translator:
  dictionary: base_dict

latn:
  dictionary: romanization_dict
  enable_completion: true
```

### Table Translator (Shape-based Input)

Replace `script_translator` with `table_translator` for cangjie/wubi-style input. Key extra options: `enable_encoder`, `encode_commit_history`, `max_phrase_length`.

## Dictionary Format

```yaml
# Rime dictionary: my_dict
---
name: my_dict
version: "1.0"
sort: by_weight
import_tables:
  - other_dict
...

文字	code1 code2	100
文字	code1 code2	50
```

**Rules:**
- YAML header between `---` and `...`; code table after `...`
- Tab-separated: `text[TAB]code[TAB]weight` (weight optional)
- Multi-syllable codes: space-delimited within code column
- `name` must match filename prefix
- UTF-8, LF line endings, first line a `#` comment (avoid BOM)
- `import_tables` merges other dictionaries
- `columns` defines custom column layout: `text`, `code`, `weight`, `stem`

## Spelling Algebra

### Operators

| Operator | Effect | Keeps Original |
|----------|--------|---------------|
| `xform/pat/repl/` | Rewrite (destructive) | No |
| `derive/pat/repl/` | Add variant | **Yes** |
| `abbrev/pat/repl/` | Low-priority abbreviation | Yes |
| `fuzz/pat/repl/` | Fuzzy (compose only) | Yes |
| `xlit/abc/XYZ/` | 1-to-1 char swap | No |
| `erase/pat/` | Remove | No |

### Key Rules

1. **Longer patterns first**: `tsh` before `ts`, `chh` before `ch`
2. **`xform` is destructive**: chain transforms the current state
3. **`derive` is additive**: keeps original + adds alternative
4. **Rules transform dictionary codes** into user-typable forms, not the reverse

```yaml
algebra:
  - derive/ /-/          # hyphen as syllable separator
  - derive/[1-8]//       # toneless input
  - xform/tsh/chh/       # consonant mapping (long first!)
  - xform/ts/ch/
  - derive/a/A/          # case folding (one per letter)
```

## Engine Components Quick Reference

### Processors

`ascii_composer` · `speller` · `punctuator` · `selector` · `navigator` · `express_editor` · `key_binder` · `recognizer` · `fluid_editor` · `chord_composer` · `lua_processor@name`

### Segmentors

`ascii_segmentor` · `abc_segmentor` · `punct_segmentor` · `matcher` · `fallback_segmentor` · `affix_segmentor@name` · `lua_segmentor@name`

### Translators

| Component | Use For |
|-----------|---------|
| `script_translator` | Phonetic input (pinyin, jyutping, etc.) |
| `table_translator` | Shape-based input (cangjie, wubi) |
| `echo_translator` | Echo input as fallback candidate |
| `punct_translator` | Punctuation conversion |
| `reverse_lookup_translator` | Cross-schema lookup |
| `history_translator` | Commit history as candidates |
| `lua_translator@name` | Custom Lua translator |

### Filters

`uniquifier` · `simplifier` (OpenCC 繁→簡) · `cjk_minifier` · `single_char_filter` · `reverse_lookup_filter@name` · `lua_filter@name`

## Translator Options

```yaml
translator:
  dictionary: my_dict
  prism: custom_prism
  user_dict: custom_user_dict
  enable_completion: true
  enable_sentence: true
  enable_correction: true     # script_translator only
  enable_user_dict: true
  enable_encoder: true        # table_translator only
  max_phrase_length: 5
  preedit_format:
    - xform/([nl])v/$1ü/
  comment_format:
    - xlit|abc|XYZ|
  initial_quality: 1.0
  spelling_hints: 4
  always_show_comments: true
  tag: abc
  prefix: "`"
  tips: "【反查】"
```

## Lua Integration

`rime.lua` loads modules; schema references them via `lua_filter@name` / `lua_translator@name` / `lua_processor@name`:

```lua
-- rime.lua
local my_mod = require('my_module')
my_filter = my_mod[2]           -- filter function for lua_filter@my_filter
my_processor = my_mod[1]        -- processor table for lua_processor@my_filter
```

```lua
-- lua/my_module.lua
local function processor(key, env)
  return 2  -- kAccepted
end

local function filter(translation, env)
  for cand in translation:iter() do
    yield(cand)
  end
end

return {{ processor = processor }, filter}
```

## Customization (`.custom.yaml`)

```yaml
patch:
  "menu/page_size": 9
  "key_binder/bindings":
    - { when: paging, accept: bracketleft, send: Page_Up }
  "switcher/hotkeys":
    - "Control+s"
    - F4
```

Common targets: `menu/page_size`, `schema_list`, `switcher/hotkeys`, `punctuator/half_shape`, `switches/@N/reset`, `style/font_face`, `style/horizontal`

## Data Paths

| Platform | Shared | User |
|----------|--------|------|
| Linux (ibus) | `/usr/share/rime-data/` | `~/.config/ibus/rime/` |
| Linux (fcitx5) | `/usr/share/rime-data/` | `~/.local/share/fcitx5/rime/` |
| Windows | `<install>\data` | `%APPDATA%\Rime` |
| macOS | `/Library/Input Methods/Squirrel.app/Contents/SharedSupport/` | `~/Library/Rime/` |

## Debugging Checklist

1. **YAML syntax**: Spaces for indentation (never tabs in structure); tabs only in dict code table
2. **Encoding**: UTF-8 without BOM
3. **`schema_id`** matches filename prefix (lowercase, no spaces)
4. **`name`** in dict matches filename prefix
5. **Algebra order**: longer patterns before shorter
6. **`import_tables`**: all referenced dicts exist
7. **`alphabet`**: includes every char in codes (digits, hyphens, uppercase)
8. **Lua**: `rime.lua` must `require()` and export the function names used in schema
9. **Re-deploy** after any change
10. **Check logs**: `build/` folder in user data dir for deployment errors
11. **`speller/algebra` direction**: rules map *dictionary codes → user-typable forms*
12. **Missing candidates**: verify `enable_completion`, `enable_sentence`, dictionary actually contains matching entries
