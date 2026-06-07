---
name: resolve-hanzi-candidates
description: Resolve hanzi candidate lists (|/-separated) and ??? entries to single correct Chinese characters for Teochew/Hokkien vocabulary chunks. Use when processing books/004_chunk_*_done.csv files, resolving candidate annotations, or user says "process chunks" or "resolve candidates". Key rule: NEVER show reasoning — output final answers only.
---

# Resolve Hanzi Candidates

## Core Rule

**No reasoning, no analysis, no intermediate steps.** Read chunk → lookup ??? → pick correct hanzi → write done file. That's it.

## Chunk Processing Workflow

### Step 1: Read chunk CSV

Read `books/004_chunk_NNN.csv`. Columns: `en,puj,latn_norm,han`.

Three entry types in `han` column:
- **Resolved**: single hanzi string (e.g. `算盤`) → keep as-is
- **Candidates**: `|`/`/` separated (e.g. `退|褪/時|匙|辭`) → pick one per syllable
- **Unknown**: `???` → lookup then pick

### Step 2: Lookup ??? entries

Run per-syllable lookup against `export/teochew.csv` and `export/hokkien.csv`:

```python
import csv

targets = {"latn_norm_value": "en_value"}  # only ??? entries

syl_map = {}
for csv_path in ["export/teochew.csv", "export/hokkien.csv"]:
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            puj = row.get("puj","").strip()
            han = row.get("han","").strip()
            latn = row.get("latn_norm","").strip()
            if not puj or not han or not latn:
                continue
            if len(puj.split()) == 1:
                syl_map.setdefault(latn, set()).add(han)

for syl in targets:
    cands = sorted(syl_map.get(syl, set()))[:8]
    print(f"{syl}: {' '.join(cands) if cands else '???'}")
```

### Step 3: Resolve all entries

For each line, output the correct hanzi. Rules:

- **`|`/`/` candidates**: Pick the one hanzi per syllable that matches the English meaning. Example: `doubt,管然/定/着` → `管然` if "doubt" matches, or `無定着` if that matches better. Always pick based on `en` column semantics.
- **`???` after lookup**: Use lookup results + Teochew/Hokkien knowledge to assign hanzi. If genuinely unknown, keep `???`.
- **Already resolved**: Keep unchanged.
- **Not real PUJ** (e.g. `of fish`, `in a draught*`, English text in latn_norm): Mark `???`.
- **Common patterns**: `m̄` → 毋, `bô` → 無, `chiah8` → 食, `chui2` → 水, `im2` → 飲, `chiu2` → 酒, `sue1` → 衰, etc.

### Step 4: Write done file

Write `books/004_chunk_NNN_done.csv` with same columns: `en,puj,latn_norm,han`. Every `han` cell should be a single resolved string (or `???`).

## Processing Multiple Chunks

Process chunks sequentially. For each chunk:
1. Read chunk CSV
2. Lookup ??? entries (one batch bash call)
3. Write done file immediately
4. Move to next chunk

**Do not read the next chunk until the current done file is written.**

## Output Format

The done CSV must have identical rows to the chunk CSV. Same `en,puj,latn_norm` — only `han` column changes.

## Style Rules

1. **No reasoning displayed** — never show "let me think about this" or "considering X vs Y"
2. **No step-by-step analysis** — don't list syllable-by-syllable breakdowns
3. **Direct answers only** — read input, write output
4. **One tool call per step** — read, lookup, write. No extra exploration.
5. **Speed over perfection** — pick the most likely answer, don't discuss alternatives
6. **No subagents** — process inline only

## File Locations

| File | Purpose |
|------|---------|
| `books/004_chunk_NNN.csv` | Input chunks (001–124) |
| `books/004_chunk_NNN_done.csv` | Output done files |
| `export/teochew.csv` | Teochew hanzi lookup data |
| `export/hokkien.csv` | Hokkien hanzi lookup data |
| `books/004_hanzi_issues.csv` | Master issues file |

## Progress Tracking

After writing each done file, briefly note: "Chunk NNN done." Then immediately read and process the next chunk. No summary, no status report, no planning.
