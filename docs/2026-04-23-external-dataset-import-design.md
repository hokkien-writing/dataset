# 外部資料集導入設計

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將外部 GitHub 專案的台語詞庫轉換為 `merged.csv` 統一格式，合併後供 Rime 輸入法使用。

**First dataset:** [ChhoeTaigiDatabase](https://github.com/ChhoeTaigi/ChhoeTaigiDatabase) — 35 萬+ 筆台語字詞，含 POJ（白話字）和 KIP（教育部羅馬拼音）。

---

## 1. 架構

### 目錄結構

```
dataset/
├── external/                              ← 外部資料集原始檔
│   ├── README.md                          ← 資料來源、commit ID、授權記錄
│   └── ChhoeTaigiDatabase/                ← 每個專案一個資料夾
│       ├── README.md                      ← 原始專案的 README
│       ├── ChhoeTaigi_TaihoaSoanntengTuichiautian.csv
│       ├── ChhoeTaigi_TaijitToaSutian.csv
│       └── ...（原始 CSV）
├── scripts/
│   ├── import_external.py                 ← 轉換外部 CSV → export/external/*.csv
│   ├── merge_csv.py                       ← 合併所有 export/**/*.csv → merged.csv
│   └── importers/                         ← 各外部資料集的轉換邏輯
│       ├── __init__.py
│       ├── base.py                        ← ExternalImporter 基類
│       └── chhoetaigi.py                  ← ChhoeTaigi 轉換器
├── export/
│   ├── external/                          ← 外部資料集轉換後的標準化 CSV
│   │   ├── ChhoeTaigi_TaihoaSoanntengTuichiautian.csv
│   │   └── ...
│   ├── merged.csv
│   └── ...
├── sync_external.sh                       ← 同步外部資料集（clone + 清理 .git）
└── build.sh                               ← build 管線
```

### 管線

```
sync_external.sh           ← 手動執行，拉取原始檔到 external/
        │
        ▼
import_external.py         ← 讀 external/*.csv → 寫 export/external/*.csv
        │
        ▼
merge_csv.py               ← 讀 export/**/*.csv → 寫 export/merged.csv
        │
        ▼
export_rime.py             ← 讀 merged.csv → 寫 export/rime/
```

### 職責分離

| 腳本 | 職責 | 觸發時機 |
|---|---|---|
| `sync_external.sh` | clone/sparse-checkout 外部 repo，移除 .git，記錄 commit ID | 手動 |
| `import_external.py` | 讀取 `external/` 原始 CSV，轉換為 merged.csv 格式，寫入 `export/external/` | build |
| `merge_csv.py` | 合併所有 `export/**/*.csv` 為 `merged.csv` | build |

---

## 2. 各組件設計

### 2-1. `external/README.md`

記錄每個外部資料集的來源資訊，手動更新：

```markdown
# External Datasets

## ChhoeTaigiDatabase

- Source: https://github.com/ChhoeTaigi/ChhoeTaigiDatabase
- Commit: abc1234 (2026-04-23)
- License: mixed (see below)
  - TaihoaSoanntengTuichiautian: CC BY-SA 4.0
  - TaijitToaSutian: CC BY-NC-SA 3.0 TW
  - MaryknollTaiengSutian: CC BY-NC-SA 3.0 TW
  - EmbreeTaiengSutian: CC BY-NC-SA 3.0 TW
  - KauiokpooTaigiSutian: CC BY-ND 3.0 TW
  - KamJitian: CC BY-NC-SA 3.0 TW
  - iTaigiHoataiTuichiautian: CC0
  - TaioanPehoeKichhooGiku: CC BY-SA 4.0
  - TaioanSitbutMialui: CC BY-SA 4.0
```

### 2-2. `sync_external.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

EXTERNAL_DIR="external"

sync_repo() {
    local name="$1"
    local repo="$2"
    local branch="${3:-main}"
    local target="$EXTERNAL_DIR/$name"

    if [ -d "$target" ]; then
        echo "[$name] Already exists, skipping. Remove $target to re-sync."
        return
    fi

    echo "[$name] Cloning $repo ($branch)..."
    git clone --depth 1 --branch "$branch" "https://github.com/$repo.git" "$target"

    # Record commit ID
    cd "$target"
    local commit=$(git rev-parse HEAD)
    local date=$(git log -1 --format=%cs)
    echo "  Commit: $commit ($date)"
    cd - > /dev/null

    # Remove .git
    rm -rf "$target/.git"
    echo "[$name] Done."
}

sync_repo ChhoeTaigiDatabase ChhoeTaigi/ChhoeTaigiDatabase master
```

### 2-3. `ExternalImporter` 基類

```python
# scripts/importers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExternalEntry:
    latn_norm: str = ""
    puj: str = ""
    dp: str = ""
    poj: str = ""
    tl: str = ""
    bp: str = ""
    han: str = ""
    han_variants: str = ""
    en: str = ""
    zh_CN: str = ""
    zh_TW: str = ""
    source: str = ""


class ExternalImporter(ABC):
    @abstractmethod
    def import_file(self, csv_path: Path, source_id: str) -> list[ExternalEntry]:
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        pass
```

### 2-4. ChhoeTaigi 轉換器

```python
# scripts/importers/chhoetaigi.py

class ChhoeTaigiImporter(ExternalImporter):
    def get_source_name(self) -> str:
        return "ChhoeTaigi"

    def import_file(self, csv_path: Path, source_id: str) -> list[ExternalEntry]:
        # 欄位映射:
        #   PojUnicode      → poj
        #   KipUnicode       → tl
        #   HanLoTaibunPoj   → han (提取漢字)
        #   HoaBun           → zh_TW
        #   EngBun           → en
        ...
```

**ChhoeTaigi 欄位對應 merged.csv：**

| ChhoeTaigi 欄位 | merged.csv 欄位 | 備註 |
|---|---|---|
| `PojUnicode` | `poj` | 白話字帶調號 |
| `KipUnicode` | `tl` | 教育部羅馬拼音帶調號 |
| `HanLoTaibunPoj` | `han` | 漢羅混合，需 `extract_han_chars()` 提取純漢字 |
| `HoaBun` | `zh_TW` | 華文 |
| `EngBun` | `en` | 英文 |
| `PojInput` / `KipInput` | 忽略 | 用 latn 轉換器生成 latn_norm |

**關鍵技術點：**

1. **漢字提取** — `HanLoTaibunPoj` 是漢羅混合（如「出外 chhut-gōa」），用正則 `\u4e00-\u9fff` 過濾保留純漢字。
2. **latn_norm** — `import_external.py` 輸出時 `latn_norm` 留空，由 `merge_csv.py` 統一用 POJ → LATN_NORM 轉換器生成（若已有此路徑）。

### 2-5. `import_external.py`

```python
# scripts/import_external.py

def main():
    EXTERNAL_DIR = PROJECT_ROOT / "external"
    OUTPUT_DIR = PROJECT_ROOT / "export" / "external"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    importers = {
        "ChhoeTaigiDatabase": ChhoeTaigiImporter(),
    }

    for dir_name, importer in importers.items():
        src_dir = EXTERNAL_DIR / dir_name
        if not src_dir.exists():
            print(f"Skipping {dir_name} (not found)")
            continue
        for csv_file in sorted(src_dir.glob("*.csv")):
            entries = importer.import_file(csv_file, csv_file.stem)
            write_csv(entries, OUTPUT_DIR / csv_file.name, WIDE_FIELDS)
```

輸出的 CSV 格式與 `merged.csv` 一致（WIDE_FIELDS），`merge_csv.py` 直接掃描 `export/external/` 即可。

### 2-6. `merge_csv.py` 修改

新增掃描 `export/external/`，其餘邏輯不變：

```python
EXTERNAL_DIR = EXPORT_DIR / "external"

# main() 中新增:
for csv_file in sorted(EXTERNAL_DIR.glob("*.csv")):
    # 與 books/ 相同的讀取邏輯
    # 若 poj 非空且 latn_norm 為空，嘗試 POJ → LATN_NORM
```

### 2-7. `build.sh` 修改

```bash
python3 scripts/import_external.py   # 新增
python3 scripts/export.py
python3 scripts/export_csv.py
python3 scripts/merge_csv.py
python3 scripts/export_rime.py
```

---

## 3. 實作計畫

### Task 1: 基礎結構

- [ ] 建立 `external/` 目錄、`external/README.md`
- [ ] 建立 `scripts/importers/__init__.py`、`scripts/importers/base.py`（`ExternalEntry` + `ExternalImporter`）
- [ ] 建立 `sync_external.sh`

### Task 2: ChhoeTaigi 轉換器

- [ ] 實作 `scripts/importers/chhoetaigi.py`：`extract_han_chars()` + 欄位映射 + 9 份資料集的欄位差異回退
- [ ] 編寫測試 `scripts/tests/test_import_chhoetaigi.py`

### Task 3: import_external.py

- [ ] 實作 `scripts/import_external.py`：掃描 `external/` 目錄、呼叫對應 importer、輸出標準化 CSV 到 `export/external/`

### Task 4: merge_csv.py 修改

- [ ] 新增 `EXTERNAL_DIR` 掃描
- [ ] 對外部 CSV，若 `poj` 非空且 `latn_norm` 為空，嘗試 POJ → LATN_NORM 轉換

### Task 5: 整合

- [ ] 修改 `build.sh` 加入 `import_external.py`
- [ ] 執行 `./sync_external.sh` → `./build.sh` 驗證 merged.csv 含 ChhoeTaigi 資料
- [ ] 驗證 Rime 字典正確包含新增條目
- [ ] 更新專案 `README.md` 授權段落，標注外部資料集的開源協議（引用 `external/README.md` 詳細列表）

---

## 4. 未來擴展

新增外部資料集只需：
1. 在 `sync_external.sh` 加一行 `sync_repo`
2. 在 `scripts/importers/` 新增對應的 importer
3. 在 `import_external.py` 的 `importers` dict 中註冊
4. 更新 `external/README.md`
5. 執行 `./sync_external.sh && ./build.sh`
