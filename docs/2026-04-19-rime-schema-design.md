# Rime 閩南語輸入方案設計

## 概述

從 `export/merged.csv` 生成 Rime 輸入方案，支持 5 種閩南語拼音系統（POJ、TL、PUJ、BP、DP）的獨立輸入方案。每個方案同時輸出漢字候選和對應系統的羅馬字候選。

## 方案選擇：單一字典 + 拼寫運算

- 1 個基礎字典 `hokkien.dict.yaml`（latn_norm 編碼 → 漢字）
- Python 腳本為每個系統預生成羅馬字字典（latn_norm → 各系統羅馬字文本）
- 5 個 `.schema.yaml`，各用拼寫運算將用戶輸入轉為 latn_norm
- 每個 schema 內掛兩個 translator：漢字 + 羅馬字
- 漢字候選旁顯示羅馬字注釋（`comment_format`）

優點：單一數據源、利用 Rime 原生拼寫運算、維護成本最低。

## 文件結構

分為 `rime-hokkien` 和 `rime-teochew` 兩個獨立方案包：

```
export/rime/
├── rime-hokkien/
│   ├── hokkien.dict.yaml               # 基礎字典：latn_norm → 漢字
│   ├── hokkien_bp_latn.dict.yaml       # BP 羅馬字字典
│   ├── hokkien_tl_latn.dict.yaml       # TL 羅馬字字典
│   ├── hokkien_poj_latn.dict.yaml      # POJ 羅馬字字典
│   ├── hokkien_bp.schema.yaml          # BP 輸入方案
│   ├── hokkien_tl.schema.yaml          # TL 輸入方案
│   ├── hokkien_poj.schema.yaml         # POJ 輸入方案
│   └── default.custom.yaml             # 註冊方案到選單
└── rime-teochew/
    ├── teochew.dict.yaml               # 基礎字典：latn_norm → 漢字
    ├── teochew_puj_latn.dict.yaml      # PUJ 羅馬字字典
    ├── teochew_dp_latn.dict.yaml       # DP 羅馬字字典
    ├── teochew_puj.schema.yaml         # PUJ 輸入方案
    ├── teochew_dp.schema.yaml          # DP 輸入方案
    └── default.custom.yaml             # 註冊方案到選單
```

**方案包劃分：**
- **rime-hokkien**：BP（閩南話拼音）、TL（台羅）、POJ（白話字）
- **rime-teochew**：PUJ（潮州白話字）、DP（潮州話拼音）

兩個包的基礎字典內容相同（同一數據源），但命名和配套的輸入方案不同。

## 基礎字典格式

`hokkien.dict.yaml` / `teochew.dict.yaml` 從 `merged.csv` 的 `latn_norm` 和 `han` 列生成：

```yaml
# Rime dictionary: hokkien
---
name: hokkien
version: "0.1"
sort: by_weight
...

阿母	a1 bo2	100
亞無	a1 bo5	100
阿叔	a1 chek4	300
```

規則：
- 編碼用 latn_norm 鍵盤形式（數字標調，如 `a1 bo2`），音節間以空格分隔
- 以 `(latn_norm, han)` 為 key 去重，每次出現加權重 100
- 漢字中的 `[訓]`、`[音]` 等方括號標記在生成時清除
- `han` 為空或 `latn_norm` 為空的列跳過
- `latn_norm` 中含 `,.?!"'` 等標點符號的列跳過
- 超過 10 個音節的詞條跳過
- 多音節詞中的 `-` 轉為空格（`a1-che2` → `a1 che2`）
- 用戶可通過 `-` 或空格分隔音節（schema 中 `derive/-/ /`）
- **異體字**：`han_variants` 欄位（`|` 分隔）中的異體字也作為獨立詞條收錄，權重逐次減半：第一變體 50，第二 25，第三 12，以此類推。僅影響漢字詞表，不影響羅馬字詞表

示例（`眾人` 有 2 次出現 + 2 個異體字）：
```yaml
眾人	cheng3 nang5	200
眾儂	cheng3 nang5	100
衆人	cheng3 nang5	50
衆儂	cheng3 nang5	24
```

## 羅馬字字典

每個系統 X 各一本 `hokkien_X_latn.dict.yaml`。用 Python 現有的 `create_translator("LATN_NORM", "X")` 從 latn_norm 批量轉換生成。

以 POJ 為例：

```yaml
# Rime dictionary: hokkien_poj_latn
---
name: hokkien_poj_latn
version: "0.1"
sort: by_weight
...

a-bó	a1 bo2	100
a-bô	a1 bo5	100
a-ché	a1 che2	100
a-chek	a1 chek4	300
```

規則：
- 羅馬字用該系統的 handwriting 形式（帶變音符號，如 `a-bó`），多音節用 `-` 連接
- 編碼用 latn_norm，與基礎字典一致
- 按 `latn_norm` 聚合權重（同一 latn_norm 只出現一次，權重為所有漢字變體的加總），不受異體字影響
- 與基礎字典條目一一對應（同來源、同 key）

## Schema 定義

每個系統的 schema 核心差異在 `speller/algebra`（用戶輸入 → latn_norm）。

以 PUJ 為例 `hokkien_puj.schema.yaml`：

```yaml
# Rime schema: hokkien_puj
schema:
  schema_id: hokkien_puj
  name: 閩南語・白話字
  version: "0.1"
  author:
    - Hokkien Writing Project

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
    - script_translator@latn
  filters:
    - uniquifier

speller:
  alphabet: zyxwvutsrqponmlkjihgfedcba12345678-
  algebra:
    - derive/-/ /
    - derive/[1-8]//
    - xform/tsh/chh/
    - xform/ts/ch/
    - xform/^z/j/

translator:
  dictionary: hokkien
  enable_correction: true

latn:
  dictionary: hokkien_puj_latn
  enable_completion: true
```

### 各系統 algebra 映射

| 系統 | 聲母映射（用戶輸入 → latn_norm） | 韻母映射 |
|------|------|------|
| PUJ | `ts→ch`, `tsh→chh`, `z→j` | `ⁿ` 已是 `nn`，基本一致 |
| POJ | 基本一致（POJ 本身有 `ch/chh`） | `oo→ou`, `oa→ua`, `oe→ue` |
| TL | `ts→ch`, `tsh→chh` | 基本一致 |
| BP | `b→p`, `p→ph`, `bb→bb`→... 大量映射 | `oo→ou` |
| DP | `b→p`, `p→ph`, `z→ch`, `c→chh`, `r→j` | `ê→e`, `e→ur`（需注意順序） |

注：較長的映射規則必須排在前面（如 `tsh` 在 `ts` 之前）。

### 無調輸入

`derive/[1-8]//` 讓 `abo` 也能匹配 `a1bo2`。

### 連字符支持

`derive/-/ /` 讓用戶輸入 `a1-bo2` 等同 `a1 bo2`，方便用戶自定義詞典。

## 構建管線

在 `scripts/` 下新增 `export_rime.py`，集成到 `build.sh` 末尾。

### 流程

```
merged.csv
    │
    ▼
scripts/export_rime.py
    │
    ├── 讀 CSV，(latn_norm, han) 去重計數
    │
    ├── hokkien.dict.yaml           # latn_norm → han，附權重
    │
    ├── 對每個系統 X (POJ/TL/PUJ/BP/DP):
    │   ├── create_translator("LATN_NORM", X)
    │   ├── 批量轉換 latn_norm → X handwriting 形式
    │   └── hokkien_X_latn.dict.yaml
    │
    ├── hokkien_X.schema.yaml × 5   # 從模板 + 各系統 algebra 規則
    │
    └── default.custom.yaml          # 註冊 5 個方案
```

### Schema 模板

```python
SCHEMA_TEMPLATE = """..."""  # 含 {schema_id}, {name}, {algebra}, {latn_dict} 佔位符

SYSTEM_CONFIGS = {
    "poj": {
        "schema_id": "hokkien_poj",
        "name": "閩南語・白話字",
        "latn_dict": "hokkien_poj_latn",
        "algebra": [...],
    },
    # ...
}
```

### 權重邏輯

```python
from collections import Counter

counts = Counter()
for row in csv:
    if row.latn_norm and row.han:
        # 過濾：標點、超過 10 音節
        # 清除 [訓][音] 等標記
        counts[(row.latn_norm, clean_han)] += 100  # 基礎權重
        # 異體字：逐次減半
        for variant in row.han_variants.split("|"):
            w = w // 2
            counts[(row.latn_norm, clean_variant)] += w

# 基礎字典：han \t latn_norm \t weight（含異體字）
# 羅馬字字典：按 latn_norm 聚合權重，每個 latn_norm 只一條
```

## 用戶使用方式

1. 將 `export/rime/` 下所有文件複製到 Rime 用戶資料夾
2. 重新佈署 Rime
3. 在方案選單中選擇對應的閩南語方案
4. 用對應系統的拼音輸入，候選列表同時顯示漢字（附羅馬字注釋）和獨立羅馬字候選項
5. 可帶調或無調輸入，可用 `-` 分隔音節
