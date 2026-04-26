# dieghv 潮語字典匯入設計

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目標：** 從 [dieghv](https://github.com/kahaani/dieghv) 匯入潮州話單字讀音資料，篩選潮州音，映射至 DP 羅馬字，納入 `merged.csv`。

**資料來源：** dieghv — 潮語拼音輸入法，含 `dictionary.tsv`（8867 行）及 `dieziu.dict.yaml`（8683 筆）。

---

## 1. 原始資料結構

### 1-1. `dictionary.tsv`

7 欄，Tab 分隔，階層式（空值繼承上一行）：

| 欄位 | 說明 |
|---|---|
| 韻母 | 韻母中文名（如「亞」「窩」），空則繼承 |
| 聲母 | 聲母（b, p, d, t, l, g, k, h, z, c, s, null 等），空則繼承 |
| 聲調 | 調值 1-8，空則繼承 |
| 字頭 | 漢字 |
| 異體 | 異體字 |
| 安澄饒揭潮 | 5 位旗標，第 5 位 = 潮州。空 = 所有口音皆有 |
| 附加語音特徵 | 「鼻」（鼻化）、「脣」等，可忽略 |

### 1-2. `dieziu.dict.yaml`

Rime 字典格式，潮州音的字→DP code 對照：

```
亞	a1
鴨	ah4
踏	dah8
```

每行格式：`漢字\tDP code`。含少量多字詞（如「番梨 hueng1 lai5」）。

### 1-3. 授權

GPL-3.0。匯入資料存於 `export/external/`，不影響專案整體授權。

---

## 2. 匯入方案

### 核心問題

`dictionary.tsv` 只有中文字韻母名（如「亞」），沒有羅馬字代碼。需要從 `dieziu.dict.yaml` 交叉查表取得 DP code。

### 演算法

1. **解析 `dieziu.dict.yaml`** → `字 → [(code, parsed_initial, tone)]` 查表
   - 跳過 YAML 標頭（`...` 之前的行）
   - 跳過多字詞（含空格的 code 或多字字頭）
   - 解析 code 取出 initial 和 tone

2. **解析 `dictionary.tsv`**，逐行追蹤狀態：
   - 追蹤 current (rhyme, initial, tone)，空值繼承上一行
   - 每個字頭和異體：
     - 檢查口音旗標：空或第 5 位 = `1` → 納入
     - 從查表找 (char, initial, tone) 匹配的 code
     - `initial="null"` → code 無聲母（韻母起頭）

3. **輸出 `ExternalEntry`：**
   - `dp`：匹配的 DP code
   - `han`：漢字
   - `han_variants`：異體字（若有的話）
   - `source`：`dieghv > dictionary`

### 匹配邏輯

對 TSV 的一筆 (char, initial, tone)：
- `initial="null"` → 預期 code 無子音前綴
- `initial="b"` → 預期 code 以 "b" 開頭
- `tone=4` → 預期 code 尾碼為 "4"
- 從 dieziu.dict.yaml 該字的 code 列表中找匹配者

若無匹配，跳過並印 warning。

---

## 3. 實作計畫

### Task 1: 更新外部資料集文件

- [ ] `external/README.md` 加入 dieghv 條目（來源 URL、GPL-3.0 授權）
- [ ] `sync_external.sh` 加入 `sync_repo dieghv kahaani/dieghv master`

### Task 2: 修改 import_external.py 支援 TSV

- [ ] 將 `.csv` 搜尋改為 `*.csv` + `*.tsv`（或讓 DieghvImporter 自己處理檔案讀取）
- [ ] 在 `IMPORTERS` dict 註冊 `"dieghv": DieghvImporter()`

### Task 3: 建立 DieghvImporter

- [ ] 建立 `scripts/importers/dieghv.py`，繼承 `ExternalImporter`
- [ ] `import_file()` 讀取 dictionary.tsv + dieziu.dict.yaml，輸出潮州音條目
- [ ] 處理階層式狀態繼承（韻母/聲母/聲調空值往前找）
- [ ] 過濾潮州音（dialect flag 第 5 位）
- [ ] 異體字作為 `han_variants` 或獨立條目

### Task 4: 測試

- [ ] 建立 `scripts/tests/test_import_dieghv.py`
- [ ] 測試狀態繼承、口音過濾、code 匹配、異體字、missing match 跳過

### Task 5: 整合驗證

- [ ] 執行 `sync_external.sh` 拉取 dieghv
- [ ] 執行 `build.sh` 驗證 `merged.csv` 含 dieghv 資料

---

## 4. 邊界案例

| 情境 | 處理方式 |
|---|---|
| 多音字（一字多 code） | 用 initial+tone 匹配消歧 |
| 僅特定口音（如 "00001"） | 納入（潮州音 only） |
| 異體字 | 作為 `han_variants` |
| dieziu.dict.yaml 的多字詞 | 不匯入（只取單字） |
| 無匹配 code | 跳過，印 warning |
| 「鼻」標記 | 暫不處理（不影響 code 匹配） |
