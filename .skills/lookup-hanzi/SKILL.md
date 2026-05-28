---
name: lookup-hanzi
description: Look up Hanzi candidates from romanized input (PUJ/DP/POJ/TL/BP). Use when user provides romanized Teochew/Hokkien text and asks for Hanzi, or says "lookup", "find hanzi", "漢字", "找字", "糾正漢字". Converts to latn_norm via helper script, queries teochew.csv/hokkien.csv with primary/secondary priority based on system, then cross-validates with web search and linguistic expertise.
---

# Lookup Hanzi

Self-contained skill — all code and data are in this directory. Copy the entire `lookup-hanzi/` folder to any agent to use.

## Directory Structure

```
lookup-hanzi/
├── SKILL.md              (this file)
├── scripts/
│   ├── lookup.py         (main CLI entry point)
│   └── latn/             (self-contained romanization converter)
│       ├── __init__.py
│       ├── config.py
│       ├── converter.py
│       ├── registry.py
│       ├── translator.py
│       ├── mappings.py
│       └── systems/
│           ├── __init__.py
│           ├── poj.py
│           ├── puj.py
│           ├── tl.py
│           ├── bp.py
│           ├── dp.py
│           └── latn_norm.py
└── data/
    ├── teochew.csv        (Teochew hanzi lookup database)
    └── hokkien.csv        (Hokkien hanzi lookup database)
```

## Quick Start

```bash
python3 .skills/lookup-hanzi/scripts/lookup.py <SYSTEM> <word> [<word> ...]
```

No external dependencies — only Python stdlib is required. No need to set `PYTHONPATH` or install anything.

## System Detection

Check input for these markers to determine the romanization system:

| Marker | System |
|--------|--------|
| `ṳ`, `ⁿ`, `ts`/`tsh` initials | PUJ |
| `bh`/`gh`/`zz` initials, superscript digits | DP |
| `oa`/`oe` digraphs, `o͘` | POJ |
| `ts`/`tsh` without `oa`/`oe` | TL |
| `bb`/`gg`/`dd`, `ao` (not `au`) | BP |

If user prefixes input with system name (e.g. "PUJ: kiáⁿ"), use that.

## Workflow

1. **Detect system** from input or user hint
2. **Run lookup.py** with detected system and all space-separated words
3. **Evaluate and correct** — lookup results are **reference only** (see below)
4. **Present results**:
   - Single word: list candidates, pick best based on context
   - Full sentence: combine word-level matches (preferred) with syllable-level fallback, then compose full Hanzi sentence using semantics

## Primary vs Secondary Data

Lookup results are split by language variant based on the romanization system:

| System | Primary (潮州/福建) | Secondary reference |
|--------|---------------------|---------------------|
| PUJ, DP | `teochew.csv` | `hokkien.csv` |
| POJ, TL, BP | `hokkien.csv` | `teochew.csv` |

- **Primary** results come first — these are from the matching language variant
- **Secondary** results are supplementary — same pronunciation but from the other variant, shown only if not already in primary results
- When evaluating hanzi candidates, **prioritize primary results**. Secondary results may use different characters due to dialectal variation

## Data Is Reference Only

Data 中的漢字**僅供參考**，不可盲目採信。原因：

- 許多條目來自 19 世紀傳教士文獻，使用音借字（如「頗」代「泡/肨」）
- 外部資料集（ChhoeTaigi、dieghv）本身也有錯字或音借字
- 同一詞在不同 source 中可能用不同漢字，品質參差

### 驗證流程

收到 lookup.py 結果後，逐一判斷：

1. **語義檢查**：該漢字是否與英文釋義匹配？（例：「侶」= companion，不符合 plump）
2. **音韻檢查**：該漢字的潮州話讀音是否吻合？（例：肨讀 phong，非 pho）
3. **網路查證**：對於可疑或不確定的字詞，搜索閩南/潮州字典、學術文獻
4. **經驗判斷**：基於閩南/潮州語言知識提出正確或更合理的漢字
5. **標註信心**：明確告知哪些是確定的、哪些是推測的、哪些本字不明

### 常見問題模式

| 問題 | 例子 | 處理方式 |
|------|------|----------|
| 音借字 | 頗（quite）代泡/肨（plump） | 替換為語義匹配的字 |
| 本字不明 | lũ-lũ（侶侶）形容 plump | 標註「本字不明」，建議保留羅馬字 |
| 文白異讀 | phong↔pho, kang↔ka | 注意交替可能，不可因讀音差直接排除 |

## Reading Results

- **潮州/福建詞級匹配**: primary word matches — starting point, verify before accepting
- **福建/潮州參考匹配**: supplementary matches from the other variant — use with caution
- **音節級**: single-syllable candidates ranked by frequency — use when no word match or for ambiguous syllables
- **[異]**: han_variants (alternative orthography)

## Tips

- Word-level matches > syllable-level — but always verify
- Hyphenated input (`toa3-kiáⁿ`) is treated as one word for word-level lookup
- If lookup returns nothing, try splitting the word differently or check system detection
- For sentence translation, run all words in one call, then compose Hanzi based on semantics
- Search web for Teochew/Hokkien dictionaries when in doubt: 教育部臺灣台語常用詞辭典、ChhoeTaigi、潮州音字典

## Updating Data Files

To update the bundled data, re-run the project's build pipeline and copy:

```bash
bash build.sh
cp export/teochew.csv .skills/lookup-hanzi/data/teochew.csv
cp export/hokkien.csv .skills/lookup-hanzi/data/hokkien.csv
```
