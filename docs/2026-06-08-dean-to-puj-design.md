# Dean's Tie-chiw Romanization → PUJ Conversion Design

## Background

W. Dean's *First Lessons in the Tie-chiw Dialect* (Bangkok, 1841) uses an early missionary romanization for Teochew. The goal is to convert all romanization entries in the book's tables to standard PUJ (Pe̍h-ūe-jī), using the existing `export/teochew.csv` as the primary reference.

## Dean's Romanization System

### Key Characteristics

- **No tones marked.** Dean explicitly states he does not attempt to mark tones.
- **Breve diacritics** (ă, ĕ, ĭ, ŏ, ŭ) mark **checked/entering tone syllables** (syllables ending in -p, -t, -k, or glottal stop -h), NOT tone height.
- `gn` = velar nasal initial (ng), e.g. `Gñou` = 五 (ngou)
- `mʼ` = syllabic nasal m used as negation prefix (不), e.g. `mʼkheng` = 不肯
- `Cʼ` = variant aspiration notation, e.g. `Cʼhin` = 寒
- `aou` = `au` diphthong, e.g. `Kaou` = 九
- `ch` = both ch and ts (no distinction)
- `ey` = `e`, `ow` = `ou`, `iw/yiw` = `iu`
- Hyphens separate syllables: `a-nou-kia` (亞孥子)
- `pñi`, `hñg` = nasalized forms

### Sample Mappings

| Dean | Character | PUJ | Note |
|------|-----------|-----|------|
| Chĕk | 一 | chek8 | breve = checked |
| Naw | 二 | no6 | aw->o |
| Gñou | 五 | ngou6 | gn→ng |
| Chĭt | 七 | chhit4 | breve = checked |
| Kaou | 九 | kau2 | aou→au |
| Nang | 人 | nang5 | same |
| Koi | 雞 | koi1 | same |
| Ou | 黑 | ou | same |
| Pey | 父 | pe6 | ey→e |
| Baw | 母 | bo2 | aw->o |

## Data Flow

```
books/003_First_Lessons_in_the_Tie-chiw_Dialect.md
                    ↓ parse markdown tables
        (page, english, han, dean_latn)
                    ↓
        ┌───────────┴───────────┐
        ↓ han-based lookup        ↓ rule-based fallback
  teochew.csv match han     dean→LATN_NORM→PUJ
        ↓                       ↓
  best PUJ (with tones)     PUJ (no tones, * prefix)
        └───────────┬───────────┘
                    ↓ merge
        export/dean_to_puj.csv
```

## Module: `scripts/processors/dean_to_puj.py`

### Step 1: Markdown Table Parsing

- Track `<!-- page:N -->` markers for page numbers
- Extract table rows with regex: `| english | han | dean_latn |`
- Clean OCR artifacts: `~~丨~~(X)` → `X`
- Handle italic classifiers: `*tiou*`, `*chiă*` etc. (these are numeral classifier readings, not phrase pronunciation)
- Split comma-separated multi-syllable entries: `Chaw chiw khiĕ,yiw chiw khur` → `Chaw chiw khiĕ` + `yiw chiw khur`

### Step 2: Han-based PUJ Lookup (primary)

For each row:
1. Count han characters vs dean syllables
2. If counts match: per-character lookup in `teochew.csv` by `han` column
3. When a character has multiple PUJ readings, select the best match using **phonetic similarity scoring**:
   - Normalize Dean syllable (strip breves, `gn→ng`, `aou→au`, lowercase)
   - Compare normalized Dean with PUJ `latn_norm` using Levenshtein distance
   - Pick the PUJ entry with smallest distance
4. Assemble multi-character PUJ by joining per-character results

### Step 3: Rule-based Fallback (no tones)

When han-based lookup fails (character not in teochew.csv, or mismatched counts):

Dean → LATN_NORM mapping:

| Dean | LATN_NORM | Notes |
|------|-----------|-------|
| `gn` (initial) | `ng` | velar nasal |
| `ă` | `a` | checked syllable |
| `ĕ` | `e` | checked syllable |
| `ĭ` | `i` | checked syllable |
| `ŏ` | `o` | checked syllable |
| `ŭ` | `u` | checked syllable |
| `aou` | `au` | diphthong |
| `aw` | `o` | |
| `ow` | `ou` | |
| `ey` | `e` | |
| `iw` / `yiw` | `iu` | |
| `mʼ` | `m` | negation nasal |
| `Cʼ` | `Ch` + aspiration | context-dependent |
| `pñi` | `phinn` | nasalized |
| `hñg` | `hngnn` | nasalized |
| `gñ` | `ng` | |
| `kñui` | `kuinn` | |
| `mʼkheng` | `m6-kheng2` |   |

Output is prefixed with `*` to indicate no tone information.

### Step 4: CSV Output

File: `export/dean_to_puj.csv`

```csv
page,english,han,dean_latn,puj,source
14,One,一,Chĕk,chek8,teochew.csv
14,Two,二,Naw,no6,teochew.csv
14,Blood,血,Huĕ,hueh4,teochew.csv
14,Black,黑,Ou,*ou,rule
```

- `page`: page number from `<!-- page:N -->` markers
- `english`: first column (English gloss)
- `han`: second column (Chinese characters, cleaned)
- `dean_latn`: third column (Dean's romanization, preserved as-is)
- `puj`: converted PUJ; `*` prefix = no tone (rule-based)
- `source`: `teochew.csv` (han matched) or `rule` (fallback)


## Dependencies

- `export/teochew.csv` for han→PUJ lookup
- Python `csv`, `re`, `pathlib` (stdlib only)
- Levenshtein distance: simple inline implementation (no external lib needed)

## Execution

```bash
PYTHONPATH=. python3 scripts/processors/dean_to_puj.py \
  --input books/003_First_Lessons_in_the_Tie-chiw_Dialect.md \
  --teochew export/teochew.csv \
  --output export/dean_to_puj.csv
```

## Integration (Future)

Could be integrated into `build.sh` pipeline if desired, or used to generate clippings for Rime import.
