# dieghv 潮語字典匯入實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 從 dieghv repo 匯入潮州話單字讀音（dictionary.tsv），篩選潮州音，映射至 DP 羅馬字，納入 merged.csv。

**Architecture:** DieghvImporter 讀取 dictionary.tsv 及 dieziu.dict.yaml，後者提供字→DP code 對照表。TSV 的階層式韻母/聲母/聲調搭配口音旗標篩選潮州音，再透過 initial+tone 匹配從 dieziu.dict.yaml 取得 DP code。

**Tech Stack:** Python 3.10+, csv/ pathlib, unittest

---

## 檔案結構

| 操作 | 路徑 | 職責 |
|---|---|---|
| 修改 | `external/README.md` | 加 dieghv 條目 |
| 修改 | `sync_external.sh` | 加 dieghv clone |
| 修改 | `scripts/import_external.py` | 加 TSV 支援 + 註冊 DieghvImporter |
| 建立 | `scripts/importers/dieghv.py` | DieghvImporter 實作 |
| 建立 | `scripts/tests/test_import_dieghv.py` | 測試 |

---

### Task 1: 更新外部資料集文件與同步腳本

**Files:**
- Modify: `external/README.md`
- Modify: `sync_external.sh`

- [ ] **Step 1: 更新 `external/README.md`，加入 dieghv 條目**

在 ChhoeTaigiDatabase 區塊之後加入：

```markdown
## dieghv

- Source: https://github.com/kahaani/dieghv
- Commit: _record after sync_
- License: GPL-3.0
- Files: `dictionary.tsv` (潮州話字音字典，8867 行), `dieziu.dict.yaml` (潮州音 Rime 字典)
```

- [ ] **Step 2: 更新 `sync_external.sh`，加入 dieghv clone**

在最後一行 `sync_repo ChhoeTaigiDatabase ...` 之後加入：

```bash
sync_repo dieghv kahaani/dieghv master
```

- [ ] **Step 3: 驗證腳本語法**

Run: `bash -n sync_external.sh`
Expected: 無輸出（語法正確）

---

### Task 2: 建立 DieghvImporter 核心邏輯

**Files:**
- Create: `scripts/importers/dieghv.py`

- [ ] **Step 1: 建立 `scripts/importers/dieghv.py`**

```python
from __future__ import annotations

import csv
import re
from pathlib import Path

from scripts.importers.base import ExternalEntry, ExternalImporter

DP_INITIALS = sorted(
    ["bh", "gh", "ng", "b", "p", "m", "d", "t", "n", "l", "g", "k", "h", "z", "c", "r", "s"],
    key=len,
    reverse=True,
)


def _parse_initial_from_code(code: str) -> str:
    base = code.rstrip("0123456789")
    for ini in DP_INITIALS:
        if base.startswith(ini):
            return ini
    return "null"


def _parse_tone_from_code(code: str) -> int | None:
    m = re.search(r"(\d+)$", code)
    return int(m.group(1)) if m else None


def _load_dieziu_dict(dict_yaml_path: Path) -> dict[str, list[tuple[str, str, int]]]:
    lookup: dict[str, list[tuple[str, str, int]]] = {}
    past_header = False
    with open(dict_yaml_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not past_header:
                if line.strip() == "...":
                    past_header = True
                continue
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            char, code = parts[0].strip(), parts[1].strip()
            if len(char) != 1:
                continue
            initial = _parse_initial_from_code(code)
            tone = _parse_tone_from_code(code)
            if tone is None:
                continue
            if char not in lookup:
                lookup[char] = []
            lookup[char].append((code, initial, tone))
    return lookup


def _is_dieziu(dialect_flag: str) -> bool:
    if not dialect_flag:
        return True
    return len(dialect_flag) >= 5 and dialect_flag[4] == "1"


class DieghvImporter(ExternalImporter):
    def get_source_name(self) -> str:
        return "dieghv"

    def import_file(self, tsv_path: Path, source_id: str) -> list[ExternalEntry]:
        dict_yaml_path = tsv_path.parent / "dieziu.dict.yaml"
        if not dict_yaml_path.exists():
            print(f"  ⚠ {dict_yaml_path.name} not found, skipping.")
            return []

        lookup = _load_dieziu_dict(dict_yaml_path)
        entries: list[ExternalEntry] = []

        current_initial = "null"
        current_tone = ""

        with open(tsv_path, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            header = next(reader, None)

            for row in reader:
                if len(row) < 4:
                    continue
                rhyme = row[0].strip()
                initial = row[1].strip()
                tone = row[2].strip()
                char = row[3].strip()
                variant = row[4].strip() if len(row) > 4 else ""
                dialect = row[5].strip() if len(row) > 5 else ""

                if not char:
                    continue

                if rhyme == header[0] and initial == header[1]:
                    continue

                if initial:
                    current_initial = initial
                if tone:
                    current_tone = tone

                if not _is_dieziu(dialect):
                    continue

                matched_code = self._match_code(
                    lookup, char, current_initial, int(current_tone)
                )
                if matched_code is None:
                    continue

                han_variants = variant

                entries.append(
                    ExternalEntry(
                        dp=matched_code,
                        han=char,
                        han_variants=han_variants,
                        source=f"{self.get_source_name()} > {source_id}",
                    )
                )

        return entries

    def _match_code(
        self,
        lookup: dict[str, list[tuple[str, str, int]]],
        char: str,
        initial: str,
        tone: int,
    ) -> str | None:
        codes = lookup.get(char)
        if not codes:
            return None
        for code, code_initial, code_tone in codes:
            if code_initial == initial and code_tone == tone:
                return code
        for code, code_initial, code_tone in codes:
            if code_tone == tone:
                return code
        return None
```

- [ ] **Step 2: 驗證模組可匯入**

Run: `PYTHONPATH=. python3 -c "from scripts.importers.dieghv import DieghvImporter; print('OK')"`
Expected: `OK`

---

### Task 3: 註冊 DieghvImporter 到 import_external.py

**Files:**
- Modify: `scripts/import_external.py`

- [ ] **Step 1: 修改 `scripts/import_external.py`**

1. 加 import：
   在 `from scripts.importers.chhoetaigi import ChhoeTaigiImporter` 後加：

```python
from scripts.importers.dieghv import DieghvImporter
```

2. 加註冊：
   在 `IMPORTERS` dict 中加 `"dieghv": DieghvImporter()`：

```python
IMPORTERS = {
    "ChhoeTaigiDatabase": ChhoeTaigiImporter(),
    "dieghv": DieghvImporter(),
}
```

3. 修改檔案掃描，支援 TSV：
   將 `csv_files = sorted(src_dir.rglob("*.csv"))` 改為：

```python
        csv_files = sorted(
            f for f in src_dir.rglob("*.csv*") if f.suffix in (".csv", ".tsv")
        )
```

   注意：實際上用 `rglob` 改成掃描兩種模式更好：

```python
        csv_files = sorted(
            src_dir.rglob("*.csv")
        ) + sorted(
            src_dir.rglob("*.tsv")
        )
```

   但為避免重複，更簡潔的做法是改迴圈讓 DieghvImporter 直接讀 `dictionary.tsv`。在 main() 迴圈中，掃描邏輯改為：

```python
        all_files = sorted(
            p for ext in ("*.csv", "*.tsv")
            for p in src_dir.rglob(ext)
        )
```

   替換原本的 `csv_files = sorted(src_dir.rglob("*.csv"))`。

4. 將迴圈變數 `csv_files` → `data_files`，`csv_file` → `data_file`。

- [ ] **Step 2: 驗證語法**

Run: `PYTHONPATH=. python3 -c "from scripts.import_external import IMPORTERS; print(list(IMPORTERS.keys()))"`
Expected: `['ChhoeTaigiDatabase', 'dieghv']`

---

### Task 4: 建立測試

**Files:**
- Create: `scripts/tests/test_import_dieghv.py`

- [ ] **Step 1: 建立測試檔案**

```python
#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.importers.dieghv import (
    DieghvImporter,
    _parse_initial_from_code,
    _parse_tone_from_code,
    _is_dieziu,
)


class TestParseInitialFromCode(unittest.TestCase):
    def test_null_initial(self):
        self.assertEqual(_parse_initial_from_code("a1"), "null")

    def test_simple_initial(self):
        self.assertEqual(_parse_initial_from_code("ba1"), "b")

    def test_digraph_initial(self):
        self.assertEqual(_parse_initial_from_code("bho2"), "bh")
        self.assertEqual(_parse_initial_from_code("ngang5"), "ng")

    def test_entering_tone(self):
        self.assertEqual(_parse_initial_from_code("dah8"), "d")
        self.assertEqual(_parse_initial_from_code("ah4"), "null")


class TestParseToneFromCode(unittest.TestCase):
    def test_single_digit(self):
        self.assertEqual(_parse_tone_from_code("ba1"), 1)
        self.assertEqual(_parse_tone_from_code("dah8"), 8)

    def test_no_tone(self):
        self.assertIsNone(_parse_tone_from_code("ba"))


class TestIsDieziu(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(_is_dieziu(""))

    def test_dieziu_yes(self):
        self.assertTrue(_is_dieziu("11111"))
        self.assertTrue(_is_dieziu("00001"))

    def test_dieziu_no(self):
        self.assertFalse(_is_dieziu("11110"))
        self.assertFalse(_is_dieziu("00000"))


class TestDieghvImporter(unittest.TestCase):
    def setUp(self):
        self.importer = DieghvImporter()
        self.tmpdir = Path(tempfile.mkdtemp())

    def _write_dict_yaml(self, entries: list[tuple[str, str]]):
        path = self.tmpdir / "dieziu.dict.yaml"
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Rime dictionary\n")
            f.write("---\nname: dieziu\n...\n")
            for char, code in entries:
                f.write(f"{char}\t{code}\n")
        return path

    def _write_tsv(self, rows: list[list[str]]):
        path = self.tmpdir / "dictionary.tsv"
        with open(path, "w", encoding="utf-8") as f:
            f.write("韻母\t聲母\t聲調\t字頭\t異體\t安澄饒揭潮\t附加語音特徵\n")
            for row in rows:
                f.write("\t".join(row) + "\n")
        return path

    def test_basic_import(self):
        self._write_dict_yaml([
            ("巴", "ba1"),
            ("爸", "ba1"),
            ("把", "ba2"),
        ])
        tsv_path = self._write_tsv([
            ["亞", "b", "1", "巴", "", "", ""],
            ["", "", "", "爸", "", "", ""],
            ["", "", "2", "把", "", "", ""],
        ])
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].dp, "ba1")
        self.assertEqual(entries[0].han, "巴")
        self.assertEqual(entries[1].dp, "ba1")
        self.assertEqual(entries[1].han, "爸")
        self.assertEqual(entries[2].dp, "ba2")
        self.assertEqual(entries[2].han, "把")

    def test_dialect_filter(self):
        self._write_dict_yaml([
            ("澳", "au3"),
        ])
        tsv_path = self._write_tsv([
            ["窩", "null", "3", "澳", "", "11110", ""],
            ["", "", "", "澳", "", "00001", ""],
        ])
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].han, "澳")
        self.assertIn("dieghv", entries[0].source)

    def test_variant_characters(self):
        self._write_dict_yaml([
            ("叩", "kau3"),
        ])
        tsv_path = self._write_tsv([
            ["亞", "k", "3", "扣", "釦", "", ""],
            ["", "", "", "叩", "", "", ""],
        ])
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertTrue(any(e.han == "叩" for e in entries))

    def test_state_inheritance(self):
        self._write_dict_yaml([
            ("巴", "ba1"),
            ("疤", "ba1"),
            ("把", "ba2"),
            ("打", "da2"),
        ])
        tsv_path = self._write_tsv([
            ["亞", "b", "1", "巴", "", "", ""],
            ["", "", "", "疤", "", "", ""],
            ["", "", "2", "把", "", "", ""],
            ["", "d", "", "打", "", "", ""],
        ])
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 4)
        self.assertEqual(entries[3].dp, "da2")

    def test_missing_code_skipped(self):
        self._write_dict_yaml([])
        tsv_path = self._write_tsv([
            ["亞", "b", "1", "巴", "", "", ""],
        ])
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 0)

    def test_null_initial(self):
        self._write_dict_yaml([
            ("亞", "a1"),
            ("阿", "a1"),
        ])
        tsv_path = self._write_tsv([
            ["亞", "null", "1", "亞", "", "", ""],
            ["", "", "", "阿", "", "", ""],
        ])
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].dp, "a1")

    def test_get_source_name(self):
        self.assertEqual(self.importer.get_source_name(), "dieghv")

    def test_missing_dict_yaml(self):
        tsv_path = self._write_tsv([
            ["亞", "null", "1", "亞", "", "", ""],
        ])
        (self.tmpdir / "dieziu.dict.yaml").unlink(missing_ok=True)
        entries = self.importer.import_file(tsv_path, "dictionary")
        self.assertEqual(len(entries), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試**

Run: `PYTHONPATH=. python3 scripts/tests/test_import_dieghv.py -v`
Expected: 全部 PASS

---

### Task 5: 整合驗證

**Files:** 無新檔

- [ ] **Step 1: 執行 sync_external.sh 拉取 dieghv**

Run: `bash sync_external.sh`
Expected: `[dieghv] Cloning kahaani/dieghv (master)...`，完成後 `external/dieghv/` 存在

- [ ] **Step 2: 執行 build.sh 驗證管線**

Run: `bash build.sh`
Expected: `[dieghv] Processing ... file(s)...\n  ✓ dictionary.tsv (NNN entries)`

- [ ] **Step 3: 檢查輸出**

Run: `head -20 export/external/dictionary.tsv.csv`（或 `ls export/external/` 確認有新檔）

- [ ] **Step 4: 執行全量測試**

Run: `bash test.sh`
Expected: 全部 PASS
