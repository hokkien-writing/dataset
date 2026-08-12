# 通用羅馬字與英文標點後處理實施計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 統一所有書籍匯出的英文與羅馬字標點、空格及句末符號。

**Architecture:** 在 `scripts.punctuation` 提供字段級英文與羅馬字函式；`export_csv.py` 在 processor 產出後統一處理 canonical 字段，保留 `*_orig`。007 Markdown 後處理沿用同一英文與羅馬字函式，避免兩套規則漂移。

**Tech Stack:** Python 3.10+、`re`、`unittest`、既有 CSV 匯出器。

## Global Constraints

- 英文缺少句末 `.?!` 時補 `.`。
- 英文與羅馬字不得含中文標點或彎引號。
- 標點前不得有空格；內部標點後恰有一個空格。
- 羅馬字句末 `?!` 跟隨英文；英文句點對應的羅馬字句點可省略。
- 不修改 `*_orig` 原始字段。
- 不新增第三方依賴。

---

### Task 1: 字段級標點函式

**Files:**
- Modify: `scripts/punctuation.py`
- Test: `scripts/tests/test_punctuation.py`

**Interfaces:**
- Produces: `normalize_english_gloss(text: str) -> str`
- Produces: `normalize_roman_reading(text: str, gloss: str = "") -> str`

- [ ] 寫真實錯誤案例與句末同步失敗測試。
- [ ] 確認測試先失敗。
- [ ] 實作最小字段級規則。
- [ ] 跑標點測試確認通過。

### Task 2: 通用匯出與 007 Markdown 接入

**Files:**
- Modify: `scripts/export_csv.py`
- Modify: `scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.py`
- Test: `scripts/tests/test_export_csv_cli.py`
- Test: `scripts/tests/test_wikisource_007.py`

**Interfaces:**
- Consumes: Task 1 字段級函式。
- Produces: 所有匯出 canonical 羅馬字／英文字段及 007 Markdown 統一標點。

- [ ] 寫匯出入口與 Markdown 入口失敗測試。
- [ ] 在匯出公共邊界正規化 `puj/poj/dp/bp/tl/en`。
- [ ] 在 007 條目後處理中正規化讀音與英文。
- [ ] 重建 007 Markdown/CSV並掃描殘留錯誤。
