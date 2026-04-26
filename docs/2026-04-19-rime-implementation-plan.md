# Rime 閩南語輸入方案實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 從 `export/merged.csv` 生成完整的 Rime 輸入方案，支持 POJ/TL/PUJ/BP/DP 五種拼音系統輸入，輸出漢字和羅馬字。

**Architecture:** 單一基礎字典（latn_norm 編碼）+ 拼寫運算映射用戶輸入 + 預生成羅馬字字典。Python 腳本 `export_rime.py` 讀取 merged.csv，利用現有 `scripts/latn` 模組做轉換，生成所有 Rime 文件到 `export/rime/`。

**Tech Stack:** Python 3（現有 latn 模組），Rime schema/dict YAML 格式

---

### Task 1: 創建 export_rime.py 骨架與基礎字典生成

**Files:**
- Create: `scripts/export_rime.py`

- [ ] **Step 1: 創建腳本骨架與 main 函數**

```python
#!/usr/bin/env python3
"""Export Rime input schema files from merged.csv."""

import csv
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MERGED_CSV = PROJECT_ROOT / "export" / "merged.csv"
OUTPUT_DIR = PROJECT_ROOT / "export" / "rime"

SYSTEMS = ["poj", "tl", "puj", "bp", "dp"]

SYSTEM_NAMES = {
    "poj": "閩南語・白話字",
    "tl": "閩南語・台羅",
    "puj": "閩南語・潮州白話字",
    "bp": "閩南語・閩南話拼音",
    "dp": "閩南語・潮州話拼音",
}


def load_entries(csv_path: Path):
    """Load and deduplicate entries from merged.csv.

    Returns: dict of (latn_norm, han) -> count
    """
    counts = Counter()
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            latn_norm = (row.get("latn_norm") or "").strip()
            han = (row.get("han") or "").strip()
            if not latn_norm or not han:
                continue
            counts[(latn_norm, han)] += 1
    return counts


def write_base_dict(entries: dict, output_dir: Path):
    """Write hokkien.dict.yaml (latn_norm -> han with weights)."""
    lines = [
        "# Rime dictionary: hokkien",
        "# Generated from merged.csv - do not edit manually",
        "---",
        'name: hokkien',
        'version: "0.1"',
        'sort: by_weight',
        "...",
        "",
    ]
    for (latn_norm, han), count in sorted(entries.items()):
        code = latn_norm.replace("-", " ")
        lines.append(f"{han}\t{code}\t{count}")
    path = output_dir / "hokkien.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_entries(MERGED_CSV)
    write_base_dict(entries, OUTPUT_DIR)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 運行驗證基礎字典生成**

Run: `python3 scripts/export_rime.py`
Expected: `export/rime/hokkien.dict.yaml` 生成，包含 tab 分隔的 `漢字\tlatn_norm\t權重` 行

- [ ] **Step 3: 提交**

```bash
git add scripts/export_rime.py
git commit -m "feat: add export_rime.py with base dictionary generation"
```

---

### Task 2: 羅馬字字典生成

**Files:**
- Modify: `scripts/export_rime.py`

- [ ] **Step 1: 添加羅馬字字典生成函數**

在 `export_rime.py` 中添加：

```python
from scripts.latn import create_translator, create_converter


def latn_norm_to_system_code(latn_norm: str) -> str:
    """Convert hyphenated latn_norm to space-separated keyboard form."""
    return latn_norm.replace("-", " ")


def write_latn_dict(entries: dict, system: str, output_dir: Path):
    """Write hokkien_{system}_latn.dict.yaml (romanization output dictionary)."""
    translator = create_translator("LATN_NORM", system.upper())
    converter = create_converter(system.upper())

    lines = [
        f"# Rime dictionary: hokkien_{system}_latn",
        "# Generated from merged.csv - do not edit manually",
        "---",
        f"name: hokkien_{system}_latn",
        'version: "0.1"',
        "sort: by_weight",
        "...",
        "",
    ]

    for (latn_norm, han), count in sorted(entries.items()):
        code = latn_norm_to_system_code(latn_norm)
        try:
            handwriting = translator.translate(latn_norm.replace("-", " "))
            romanized = handwriting.replace(" ", "-")
        except Exception:
            continue
        if not romanized.strip():
            continue
        lines.append(f"{romanized}\t{code}\t{count}")

    path = output_dir / f"hokkien_{system}_latn.dict.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_entries(MERGED_CSV)
    write_base_dict(entries, OUTPUT_DIR)
    for system in SYSTEMS:
        write_latn_dict(entries, system, OUTPUT_DIR)
```

- [ ] **Step 2: 運行驗證羅馬字字典生成**

Run: `python3 scripts/export_rime.py`
Expected: 5 本羅馬字字典生成在 `export/rime/`，每本包含該系統的 handwriting 形式羅馬字

- [ ] **Step 3: 提交**

```bash
git add scripts/export_rime.py
git commit -m "feat: add romanization dictionary generation for all systems"
```

---

### Task 3: Schema 文件生成

**Files:**
- Modify: `scripts/export_rime.py`

- [ ] **Step 1: 添加各系統的 algebra 規則和 schema 模板**

在 `export_rime.py` 中添加：

```python
SYSTEM_ALGEBRA = {
    "puj": [
        "derive/-/ /",
        "derive/[1-8]//",
        "xform/tsh/chh/",
        "xform/ts/ch/",
        "derive/nn(?!g)/nn/",
    ],
    "poj": [
        "derive/-/ /",
        "derive/[1-8]//",
        "xform/oo/ou/",
        "xform/oa/ua/",
        "xform/oe/ue/",
        "derive/ou(?!a|e)/oo/",
    ],
    "tl": [
        "derive/-/ /",
        "derive/[1-8]//",
        "xform/ts/ch/",
        "xform/tsh/chh/",
    ],
    "bp": [
        "derive/-/ /",
        "derive/[1-8]//",
        "xform/bb/p/",
        "xform/gg/k/",
        "xform/dd/t/",
        "xform/ggn/ng/",
        "xform/bbn/m/",
        "xform/ln/n/",
        "xform/b/p/",
        "xform/p/ph/",
        "xform/g/k/",
        "xform/k/kh/",
        "xform/d/t/",
        "xform/t/th/",
        "xform/z/ch/",
        "xform/c/chh/",
        "xform/zz/j/",
        "xform/oo/ou/",
    ],
    "dp": [
        "derive/-/ /",
        "derive/[1-8]//",
        "xform/bh/b/",
        "xform/gh/g/",
        "xform/b/p/",
        "xform/p/ph/",
        "xform/d/t/",
        "xform/t/th/",
        "xform/g/k/",
        "xform/k/kh/",
        "xform/z/ch/",
        "xform/c/chh/",
        "xform/r/j/",
        "derive/nn$/nn/",
        "xform/^e(?!$)/ur/",
        "derive/ê/e/",
    ],
}

SCHEMA_TEMPLATE = """\
# Rime schema: {schema_id}
# Generated from merged.csv - do not edit manually

schema:
  schema_id: {schema_id}
  name: {name}
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
{algebra}

translator:
  dictionary: hokkien
  enable_correction: true

latn:
  dictionary: {latn_dict}
  enable_completion: true
"""


def format_algebra(rules: list[str]) -> str:
    return "\n".join(f"    - {r}" for r in rules)


def write_schema(system: str, output_dir: Path):
    """Write hokkien_{system}.schema.yaml."""
    schema_id = f"hokkien_{system}"
    name = SYSTEM_NAMES[system]
    latn_dict = f"hokkien_{system}_latn"
    algebra = format_algebra(SYSTEM_ALGEBRA[system])

    content = SCHEMA_TEMPLATE.format(
        schema_id=schema_id,
        name=name,
        algebra=algebra,
        latn_dict=latn_dict,
    )
    path = output_dir / f"{schema_id}.schema.yaml"
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")
```

更新 `main()`:

```python
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_entries(MERGED_CSV)
    write_base_dict(entries, OUTPUT_DIR)
    for system in SYSTEMS:
        write_latn_dict(entries, system, OUTPUT_DIR)
        write_schema(system, OUTPUT_DIR)
```

- [ ] **Step 2: 運行驗證 schema 生成**

Run: `python3 scripts/export_rime.py`
Expected: 5 個 `.schema.yaml` 文件生成在 `export/rime/`

- [ ] **Step 3: 提交**

```bash
git add scripts/export_rime.py
git commit -m "feat: add schema file generation with algebra rules for all systems"
```

---

### Task 4: default.custom.yaml 生成

**Files:**
- Modify: `scripts/export_rime.py`

- [ ] **Step 1: 添加 default.custom.yaml 生成函數**

在 `export_rime.py` 中添加：

```python
DEFAULT_CUSTOM_TEMPLATE = """\
# Rime default settings customization
# Generated from merged.csv - do not edit manually

patch:
  schema_list:
{schema_list}
"""


def write_default_custom(systems: list[str], output_dir: Path):
    """Write default.custom.yaml registering all schemas."""
    schema_list = "\n".join(
        f"    - schema_id: hokkien_{s}" for s in systems
    )
    content = DEFAULT_CUSTOM_TEMPLATE.format(schema_list=schema_list)
    path = output_dir / "default.custom.yaml"
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")
```

更新 `main()`:

```python
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_entries(MERGED_CSV)
    write_base_dict(entries, OUTPUT_DIR)
    for system in SYSTEMS:
        write_latn_dict(entries, system, OUTPUT_DIR)
        write_schema(system, OUTPUT_DIR)
    write_default_custom(SYSTEMS, OUTPUT_DIR)
    print(f"\nDone. Rime files exported to {OUTPUT_DIR}/")
```

- [ ] **Step 2: 運行完整生成**

Run: `python3 scripts/export_rime.py`
Expected: `export/rime/` 包含 12 個文件（1 基礎字典 + 5 羅馬字字典 + 5 schema + 1 default.custom）

- [ ] **Step 3: 提交**

```bash
git add scripts/export_rime.py
git commit -m "feat: add default.custom.yaml generation"
```

---

### Task 5: 集成到 build.sh

**Files:**
- Modify: `build.sh`

- [ ] **Step 1: 在 build.sh 末尾加 export_rime**

在 `build.sh` 的 `python3 scripts/merge_csv.py` 後添加：

```bash
python3 scripts/export_rime.py
```

- [ ] **Step 2: 運行完整 build 驗證**

Run: `./build.sh`
Expected: 所有步驟成功，`export/rime/` 下文件重新生成

- [ ] **Step 3: 提交**

```bash
git add build.sh
git commit -m "feat: integrate export_rime into build pipeline"
```

---

### Task 6: 測試

**Files:**
- Create: `scripts/tests/test_export_rime.py`

- [ ] **Step 1: 編寫測試**

```python
#!/usr/bin/env python3
"""Tests for export_rime.py"""

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.export_rime import load_entries, write_base_dict, write_latn_dict, write_schema, write_default_custom, MERGED_CSV, SYSTEMS


class TestExportRime(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def test_load_entries_dedup_with_counts(self):
        """Entries with same (latn_norm, han) key are deduplicated with counts."""
        entries = load_entries(MERGED_CSV)
        self.assertTrue(len(entries) > 0)
        for (latn_norm, han), count in entries.items():
            self.assertTrue(latn_norm)
            self.assertTrue(han)
            self.assertGreaterEqual(count, 1)

    def test_write_base_dict_format(self):
        entries = {("a1-bo2", "阿母"): 1, ("a1-bo5", "亞無"): 2}
        write_base_dict(entries, self.tmpdir)
        path = self.tmpdir / "hokkien.dict.yaml"
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("阿母\ta1 bo2\t1", content)
        self.assertIn("亞無\ta1 bo5\t2", content)
        self.assertIn("name: hokkien", content)
        self.assertIn("sort: by_weight", content)

    def test_write_latn_dict_poj(self):
        entries = {("a1-bo2", "阿母"): 1}
        write_latn_dict(entries, "poj", self.tmpdir)
        path = self.tmpdir / "hokkien_poj_latn.dict.yaml"
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("name: hokkien_poj_latn", content)

    def test_write_schema_puj(self):
        write_schema("puj", self.tmpdir)
        path = self.tmpdir / "hokkien_puj.schema.yaml"
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("schema_id: hokkien_puj", content)
        self.assertIn("dictionary: hokkien", content)
        self.assertIn("dictionary: hokkien_puj_latn", content)
        self.assertIn("xform/ts/ch/", content)

    def test_write_default_custom(self):
        write_default_custom(SYSTEMS, self.tmpdir)
        path = self.tmpdir / "default.custom.yaml"
        self.assertTrue(path.exists())
        content = path.read_text(encoding="utf-8")
        self.assertIn("hokkien_poj", content)
        self.assertIn("hokkien_tl", content)
        self.assertIn("hokkien_puj", content)
        self.assertIn("hokkien_bp", content)
        self.assertIn("hokkien_dp", content)

    def test_all_systems_generate(self):
        """All 5 systems produce schema and latn dict files."""
        entries = load_entries(MERGED_CSV)
        for system in SYSTEMS:
            write_schema(system, self.tmpdir)
            write_latn_dict(entries, system, self.tmpdir)
        schemas = list(self.tmpdir.glob("*.schema.yaml"))
        latn_dicts = list(self.tmpdir.glob("*_latn.dict.yaml"))
        self.assertEqual(len(schemas), 5)
        self.assertEqual(len(latn_dicts), 5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 運行測試**

Run: `PYTHONPATH=. python3 scripts/tests/test_export_rime.py`
Expected: All tests pass

- [ ] **Step 3: 提交**

```bash
git add scripts/tests/test_export_rime.py
git commit -m "test: add tests for export_rime"
```

---

### Task 7: 驗證 Rime 文件正確性

**Files:** none (manual verification)

- [ ] **Step 1: 完整 build 並檢查輸出**

Run: `./build.sh`

驗證 `export/rime/` 下 12 個文件全部存在：
- `hokkien.dict.yaml`
- `hokkien_poj_latn.dict.yaml`, `hokkien_tl_latn.dict.yaml`, `hokkien_puj_latn.dict.yaml`, `hokkien_bp_latn.dict.yaml`, `hokkien_dp_latn.dict.yaml`
- `hokkien_poj.schema.yaml`, `hokkien_tl.schema.yaml`, `hokkien_puj.schema.yaml`, `hokkien_bp.schema.yaml`, `hokkien_dp.schema.yaml`
- `default.custom.yaml`

- [ ] **Step 2: 抽查字典內容**

驗證 `hokkien.dict.yaml` 中：
- 條目用 tab 分隔
- latn_norm 中 `-` 已轉為空格
- 權重值合理

驗證 `hokkien_puj_latn.dict.yaml` 中：
- 羅馬字使用 PUJ handwriting 形式（帶變音符號）
- 多音節用 `-` 連接

- [ ] **Step 3: 提交所有變更**

```bash
git add -A
git commit -m "feat: complete Rime input schema generation pipeline"
```
