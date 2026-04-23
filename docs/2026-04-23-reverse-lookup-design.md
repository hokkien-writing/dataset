# Rime 反查功能設計

## 概述

為閩南語和潮州話 Rime 輸入方案添加反查功能，用戶可透過普通話拼音、英文、注音或倉頡查詢對應的閩南/潮州詞彙。

**核心原則：** 不添加 Lua 腳本，全部使用 Rime 原生 `reverse_lookup_translator` + 字典配置。

### 反查結果

| 候選類型 | 說明 | 範例 |
|---------|------|------|
| 漢字候選 | comment 顯示系統羅馬字 | 房（comment: `pang⁵`） |
| 純羅馬字候選 | 無漢字對應的詞直接顯示羅馬字 | pâng |

### 前綴鍵一覽

| 前綴 | 反查類型 | 字典 | 範例 |
|------|---------|------|------|
| `` `1 `` | 普通話拼音 | `luna_pinyin`（Rime 內建） | `` `1fang `` → 房 |
| `` `2 `` | 英文 | `{pkg}_{system}_en.dict.yaml`（生成） | `` `2mother `` → 阿母 |
| `` `3 `` | 注音 | `bopomofo`（需用戶安裝） | `` `3ㄈㄤ `` → 房 |
| `` `4 `` | 倉頡 | `cangjie`（需用戶安裝） | `` `4戈田 `` → 房 |

**前綴無衝突：** `` `1 `` / `` `2 `` / `` `3 `` / `` `4 `` 不與任何拼音音節衝突，每種反查有明確的數字標識。

## 數據分析

從 `merged.csv`（336K 條目）：

| 欄位 | 有值條目數 | 說明 |
|------|-----------|------|
| `en` + `han` | 6,086 | 可直接用於英文反查字典 |
| `en`（無 han） | 99,020 | 多為長描述性短語，需篩選 |
| `zh_TW` + `han` | 126,679 | 已由普通話拼音反查覆蓋 |
| `zh_CN` | 0 | 目前全空 |

## 1. 普通話拼音反查

### 觸發

```
`1fang → 房、方、防、...
```

### 實現方式

`reverse_lookup_translator` + `luna_pinyin`（Rime 內建字典）。這是 dieghv 等方案的標準做法。

**流程：**
1. 用戶輸入 `` `1fang ``
2. `reverse_lookup_translator` 在 `luna_pinyin` 中查找 "fang"，返回漢字候選「房、方、防…」
3. 對每個候選，在主字典（如 `hokkien_poj`）中查找對應的 LATN_NORM code
4. `comment_format` 將 LATN_NORM 轉為可讀的系統羅馬字顯示

### Schema 改動

每個系統 schema 需要添加：

**engine：**
```yaml
engine:
  segmentors:
    - abc_segmentor
    - matcher          # 新增：支援 recognizer pattern
    - punct_segmentor
    - fallback_segmentor
  translators:
    - script_translator
    - reverse_lookup_translator   # 新增
```

**reverse_lookup 配置塊：**
```yaml
reverse_lookup:
  dictionary: luna_pinyin
  prefix: "`1"
  suffix: "'"
  tips: "〔普通話拼音〕"
  comment_format:
    - xform/ /-/           # 空格轉連字符
    # 系統特定的母音/聲母轉換（見下表）
    - xlit/12345678/¹²³⁴⁵⁶⁷⁸/  # 聲調數字→上標
```

**recognizer：**
```yaml
recognizer:
  patterns:
    reverse_lookup: "`1[a-z]*'?$"
```

### comment_format 規則（各系統）

comment 來源是主字典的 LATN_NORM code。`comment_format` 將其轉為各系統可讀形式：

| 系統 | comment_format 規則 | 範例 |
|------|-------------------|------|
| POJ | `xform/ /-/`, `xform/ou/oo/`, `xform/ua/oa/`, `xform/ue/oe/`, `xlit/12345678/¹²³⁴⁵⁶⁷⁸/` | `pang5` → `pang⁵` |
| TL | `xform/ /-/`, `xform/chh/tsh/`, `xform/ch/ts/`, `xlit/12345678/¹²³⁴⁵⁶⁷⁸/` | `che2` → `tse²` |
| BP | `xform/ /-/`, 完整聲母轉換（同 SYSTEM_ALGEBRA 的 xform 規則）, `xform/ou/oo/`, `xlit/12345678/¹²³⁴⁵⁶⁷⁸/` | `pang5` → `pang⁵` |
| PUJ | `xform/ /-/`, `xform/chh/tsh/`, `xform/ch/ts/`, `xlit/12345678/¹²³⁴⁵⁶⁷⁸/` | `chek4` → `tsek⁴` |
| DP | `xform/ /-/`, 完整聲母/韻母轉換（同 SYSTEM_ALGEBRA）, `xform/e/ei/`, `xform/ur/e/`, `xlit/12345678/¹²³⁴⁵⁶⁷⁸/` | `chek4` → `zek⁴` |

**注意：** `xform` 規則應按「長模式優先」排列（如 `chh` 在 `ch` 之前）。comment_format 只包含 `xform`（破壞性轉換），不包含 `derive`（加法性轉換），因為注釋只需顯示標準形式。

## 2. 英文反查

### 觸發

```
`2mother → 阿母、母親、...
```

### 數據處理

從 `merged.csv` 生成英文反查字典：

1. 篩選有 `en` 和 `han` 的條目（約 6,086 條）
2. 清理英文：小寫化、移除標點 `[.,;:!?'"()\\[\\]{}]`、合併多餘空格
3. 過濾：跳過清理後為空或超過 5 個單詞的條目（排除長描述性短語）
4. **純羅馬字候選**：對 `han` 為空但有 `en` 的條目，用系統的 handwriting 作為候選文本

### 字典格式

生成 `{pkg}_{system}_en.dict.yaml`：

```yaml
# Rime dictionary: hokkien_poj_en
---
name: hokkien_poj_en
version: "20260423"
sort: by_weight
...

# 有漢字的條目
阿母	mother	100
阿姐	sister	100
阿叔	uncle	80

# 無漢字的條目（純羅馬字候選）
pâng	mother	50
```

**為何按系統分開：** 無漢字條目的候選文本是系統特定的羅馬字形式（POJ: `pâng`，TL: `pâng`，BP 不同）。有漢字的條目則各系統共用。

### Schema 改動

```yaml
engine:
  segmentors:
    - abc_segmentor
    - matcher
    - punct_segmentor
    - fallback_segmentor
  translators:
    - script_translator
    - reverse_lookup_translator
    - reverse_lookup_translator@en_lookup    # 新增

en_lookup:
  dictionary: {pkg}_{system}_en
  prefix: "`2"
  suffix: "'"
  tips: "〔English〕"
  comment_format:
    # 同普通話拼音反查的 comment_format

recognizer:
  patterns:
    en_lookup: "`2[a-z]*'?$"
    reverse_lookup: "`1[a-z]*'?$"
```

**無衝突：** `` `2 `` 前綴不與 `` `1 `` 普通話拼音衝突，recognizer pattern 明確區分。

### 純羅馬字候選處理

對無漢字的英文條目：
- 候選文本 = 系統 handwriting（如 POJ 的 `pâng`）
- 當 `reverse_lookup_translator@en_lookup` 返回此候選時，會在主字典中查找 `pâng` 作為 comment
- 若主字典有 `pâng` 條目，comment 顯示其 LATN_NORM code（經 comment_format 轉換後可能冗餘）
- 這是可接受的——重要的是候選本身可見

## 3. 注音 / 倉頡反查

### 前綴

- `` `3 `` → 注音反查
- `` `4 `` → 倉頡反查

### 前置依賴

用戶需安裝對應的 Rime 方案字典：
- 注音：`bopomofo` 方案（Rime 內建或從 `plum` 安裝）
- 倉頡：`cangjie` 或 `wubi` 方案

### Schema 改動

```yaml
engine:
  translators:
    - script_translator
    - reverse_lookup_translator
    - reverse_lookup_translator@en_lookup
    - reverse_lookup_translator@bopomofo_lookup
    - reverse_lookup_translator@cangjie_lookup

bopomofo_lookup:
  dictionary: bopomofo
  prefix: "`3"
  suffix: "'"
  tips: "〔注音〕"
  comment_format:
    # 同系統 comment_format

cangjie_lookup:
  dictionary: cangjie
  prefix: "`4"
  suffix: "'"
  tips: "〔倉頡〕"
  comment_format:
    # 同系統 comment_format

recognizer:
  patterns:
    en_lookup: "`2[a-z]*'?$"
    bopomofo_lookup: "`3[a-z]*'?$"
    cangjie_lookup: "`4[a-z]*'?$"
    reverse_lookup: "`1[a-z]*'?$"
```

**無衝突：** 數字前綴 `` `1 `` ~ `` `4 `` 不與任何拼音音節衝突，無需依賴 recognizer 排序。若用戶未安裝注音/倉頡字典，對應前綴會靜默失效。

### 降級方案

若 `reverse_lookup_translator` 不支援 named instance（需測試），改用 `table_translator@en_lookup` + `affix_segmentor@en_lookup`：

```yaml
engine:
  segmentors:
    - abc_segmentor
    - affix_segmentor@en_lookup
    - matcher
    - punct_segmentor
    - fallback_segmentor
  translators:
    - script_translator
    - reverse_lookup_translator
    - table_translator@en_lookup

en_lookup:
  tag: en_lookup
  dictionary: {pkg}_{system}_en
  prefix: "`2"
  tips: "〔English〕"
  enable_completion: true
  enable_sentence: false
```

此方案缺點：`table_translator` 不會自動從主字典查找 comment，無法顯示羅馬字注釋。

## 新增字典清單

需在 `export_rime.py` 中生成以下字典：

| 文件 | 用途 | 條目數（約） |
|------|------|-------------|
| `rime-hokkien/hokkien_poj_en.dict.yaml` | POJ 英文反查 | ~6K（han）+ 篩選後的 no-han |
| `rime-hokkien/hokkien_tl_en.dict.yaml` | TL 英文反查 | 同上 |
| `rime-hokkien/hokkien_bp_en.dict.yaml` | BP 英文反查 | 同上 |
| `rime-teochew/teochew_puj_en.dict.yaml` | PUJ 英文反查 | ~6K |
| `rime-teochew/teochew_dp_en.dict.yaml` | DP 英文反查 | ~6K |

**不需要額外字典的：** 普通話拼音（用 `luna_pinyin`）、注音（用 `bopomofo`）、倉頡（用 `cangjie`）。

## export_rime.py 改動

### 新增函式

#### `write_en_dict(entries, systems_data, system, pkg, output_dir)`

為每個系統生成英文反查字典：

```python
def write_en_dict(entries, systems_data, system, pkg, output_dir):
    translator = create_translator("LATN_NORM", system.upper())
    system_converter = create_converter(system.upper())

    # 有漢字的條目：en → han
    # 無漢字的條目：en → 系統 handwriting
    # 清理英文：lowercase, strip punctuation, collapse spaces
    # 過濾：≤ 5 words
```

**英文清理邏輯：**
```python
def _clean_en(en_text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z ]", "", en_text).lower()
    cleaned = re.sub(r" +", " ", cleaned).strip()
    return cleaned if len(cleaned.split()) <= 5 else ""
```

#### `get_comment_format(system: str) -> list[str]`

從 `SYSTEM_ALGEBRA[system]` 提取 `xform` 規則，附加聲調上標轉換：

```python
def get_comment_format(system: str) -> list[str]:
    rules = ["xform/ /-/"]
    for rule in SYSTEM_ALGEBRA[system]:
        if rule.startswith("xform/"):
            rules.append(rule)
    rules.append("xlit/12345678/¹²³⁴⁵⁶⁷⁸/")
    return rules
```

### 修改 `write_schema()`

更新 `SCHEMA_TEMPLATE` 加入：
- `matcher` segmentor
- `reverse_lookup_translator` 及 named instances
- `reverse_lookup` 配置塊
- `en_lookup` 配置塊
- `bopomofo_lookup` / `cangjie_lookup` 配置塊
- `recognizer` patterns

### 修改主流程

在 `main()` 中為每個系統呼叫 `write_en_dict()`。

## Schema 模板改動

完整的新 `SCHEMA_TEMPLATE`：

```yaml
# Rime schema: {schema_id}
# Generated from merged.csv - do not edit manually

schema:
  schema_id: {schema_id}
  name: {name}
  version: "{version}"
  author:
    - Hokkien Writing Project

engine:
  processors:
    - ascii_composer
    - lua_processor@{caps_tracker_name}
    - speller
    - punctuator
    - selector
    - navigator
    - key_binder
    - express_editor
  segmentors:
    - abc_segmentor
    - matcher
    - punct_segmentor
    - fallback_segmentor
  translators:
    - script_translator
    - reverse_lookup_translator
    - reverse_lookup_translator@en_lookup
    - reverse_lookup_translator@bopomofo_lookup
    - reverse_lookup_translator@cangjie_lookup
  filters:
    - lua_filter@{filter_name}
    - uniquifier

speller:
  alphabet: zyxwvutsrqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA12345678-
  initials: zyxwvutsrqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA12345678
  delimiter: " -"
  algebra:
{algebra}

key_binder:
  bindings:
    - {{ when: paging, accept: Left, send: Page_Up }}
    - {{ when: has_menu, accept: Right, send: Page_Down }}
    - {{ when: paging, accept: bracketleft, send: Page_Up }}
    - {{ when: has_menu, accept: bracketright, send: Page_Down }}
    - {{ when: has_menu, accept: Tab, send: Page_Down }}
    - {{ when: paging, accept: Shift+Tab, send: Page_Up }}

style:
  horizontal: true
  candidate_list_layout: linear
  candidate_format: "%@"

translator:
  dictionary: {schema_id}
  enable_completion: true
  enable_sentence: true
  enable_user_dict: true
  spelling_hints: 99

reverse_lookup:
  dictionary: luna_pinyin
  prefix: "`1"
  suffix: "'"
  tips: "〔普通話拼音〕"
  comment_format:
{pinyin_comment_format}

en_lookup:
  dictionary: {schema_id}_en
  prefix: "`2"
  suffix: "'"
  tips: "〔English〕"
  comment_format:
{en_comment_format}

bopomofo_lookup:
  dictionary: bopomofo
  prefix: "`3"
  suffix: "'"
  tips: "〔注音〕"
  comment_format:
{bopomofo_comment_format}

cangjie_lookup:
  dictionary: cangjie
  prefix: "`4"
  suffix: "'"
  tips: "〔倉頡〕"
  comment_format:
{cangjie_comment_format}

recognizer:
  patterns:
    en_lookup: "`2[a-z]*'?$"
    bopomofo_lookup: "`3[a-z]*'?$"
    cangjie_lookup: "`4[a-z]*'?$"
    reverse_lookup: "`1[a-z]*'?$"
```

其中 `{xxx_comment_format}` 由 `get_comment_format(system)` 生成並格式化。

## 已知限制

1. **comment_format 不產生聲調符號**：代之以聲調上標（如 `pang⁵` 而非 `pâng`）。完整的聲調符號定位需要 Lua 處理，與「不用 Lua」原則衝突。
2. **英文反查精度有限**：英文定義多為描述性短語（如 "grand-uncle's child, younger, paternal"），清理後可能不直覺。建議限制 ≤ 5 詞。
3. **注音/倉頡需額外安裝**：`bopomofo` 和 `cangjie` 字典非 Rime 必裝組件，未安裝時對應前綴靜默失效。
4. **zh_TW 反查未實現**：233K 條 zh_TW 定義目前無法直接反查，需額外的拼音分詞和字典生成。

## 實現優先級

1. **Phase 1**：普通話拼音反查（標準做法，風險最低）
2. **Phase 2**：英文反查（需生成字典 + 測試 named instance）
3. **Phase 3**：注音/倉頡（需驗證 `reverse_lookup_translator` named instance 支援）
4. **Phase 4**（未來）：zh_TW 中文定義反查
