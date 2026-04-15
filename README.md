# 閩南語書寫 - 數據集

閩南語文字數位化專案，書籍、歌詞等等經原文經人工校注後，可透過腳本匯出原版與修改版。

## 專案結構

```
books/               校注後的書籍來源（含編輯標記）
lyrics/              校注後的歌詞來源（含編輯標記）
export/              匯出輸出
  books/             書籍匯出
  lyrics/            歌詞匯出
scripts/             工具腳本
  export.py          匯出原版 / 修改版 Markdown
  export_csv.py      匯出結構化 CSV
  processors/        各書籍的 CSV 解析處理器
    base.py          基礎類別與共用函數
  tests/             單元測試
build.sh             一鍵建置腳本
```

## 編輯標記規則

在 `books/`、`lyrics/` 等目錄中的 Markdown 檔案使用以下五種標記記錄校勘修改：

| 標記 | 含義 | 原版輸出 | 修改版輸出 |
|------|------|---------|-----------|
| `~~餮~~` | 刪除，不需改正 | 餮 | （移除） |
| `~~餮~~(餐)` | 刪除並改正為括號內文字 | 餮 | 餐 |
| `~~小暑~~()` | 刪除但不知如何改正，暫時留白 | 小暑 | `〔〕` |
| `++等++` | 新增文字 | （移除） | 等 |
| `++++` | 需要新增但暫時找不到合適文字 | （移除） | `〔〕` |

### 範例

**來源（校注版）：**
```
~~菓~~(果)子
~~污穢~~(垃圾)  ++污糟++
~~巧語~~()
++漉++
++++
```

**原版輸出：**
```
菓子
污穢
巧語


```

**修改版輸出：**
```
果子
垃圾  污糟
〔〕
漉
〔〕
```

## 使用方式

### 匯出

```bash
./build.sh
```

會在 `export/` 目錄下按來源目錄分別匯出，每個檔案產生兩個版本：
- `*_original.md` — 原版（移除標記，保留原始文字）
- `*_modified.md` — 修改版（套用所有校勘修改）

### CSV 匯出

每個檔案還會匯出結構化 CSV（需在 `scripts/processors/` 中有對應的處理器）：

| 欄位 | 說明 |
|------|------|
| `puj` | 白話字拼音（校注後） |
| `puj_orig` | 白話字拼音（原始，僅當與 puj 不同時填寫） |
| `han` | 漢字（校注後） |
| `han_orig` | 漢字（原始，僅當與 han 不同時填寫） |
| `en` | 英文翻譯（校注後） |
| `en_orig` | 英文翻譯（原始，僅當與 en 不同時填寫） |
| `source` | 來源（書名 > 章節） |

新增書籍時，只需在 `scripts/processors/` 新增同名的 `.py` 檔案，定義繼承 `BookProcessor` 的 `Processor` 類別即可。

## 測試

專案使用 Python 內置的 `unittest` 框架進行測試。執行以下指令即可運行所有單元測試：

```bash
PYTHONPATH=. python3 -m unittest discover scripts/tests
```

## 系統間轉換

專案支持在不同的 Latin 系統間進行相互轉換（如 POJ <-> PUJ），並支持自定義音韻規律映射。

```python
from scripts.latn.registry import LatnRegistry
from scripts.latn.config import PhoneticMapping

registry = LatnRegistry()
# 定義 POJ 到 PUJ 的映射規則
mapping = PhoneticMapping(
    vowel_map={"oo": "ou", "oa": "ua", "oe": "ue"},
    conversion_rules=[
        (r"^chh(?![ie])", "tsh"), # chh -> tsh (非 i/e 前)
        (r"^ch(?![hie])", "ts"),   # ch -> ts (非 h/i/e 前)
        (r"^j(?![ie])", "z"),      # j -> z (非 i/e 前)
    ]
)
registry.register_translator("POJ", "PUJ", mapping)

translator = registry.create_translator("POJ", "PUJ")
result = translator.translate("o͘-oá-oē") # 輸出 "ou-uá-uē"
```

## 收錄內容

- [Books 書籍](books/README.md)
- [Lyrics 歌詞](lyrics/README.md)

## 授權

MIT License
