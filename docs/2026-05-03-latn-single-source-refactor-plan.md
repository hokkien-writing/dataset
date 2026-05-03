# Latn 單一事實來源重構計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 `scripts/latn/` 各系統的轉換規則、`export_rime.py` 中的 Rime algebra、以及 `mappings.py` 的跨系統對照表，統整到各自的單一系統文件（如 `systems/poj.py`），消除重複定義，並清除死碼。

**Architecture:** 以 `systems/{system}.py` 為各系統的唯一事實來源（Single Source of Truth）。每個系統文件定義：(1) 系統配置（vowels, initials, tone rules），(2) 與 LATN_NORM 的雙向映射，(3) Rime algebra 規則生成函數。`mappings.py` 和 `export_rime.py` 中的硬編碼規則改為從系統文件讀取。

**Tech Stack:** Python 3.10+, dataclasses, Rime YAML generation

---

## 現狀問題分析

### 重複 #1: 初始/韻母/韻尾映射 — 三處定義

| 知識 | Python `mappings.py` | `export_rime.py` SYSTEM_ALGEBRA | YAML schema |
|---|---|---|---|
| DP `g->gh` | `initial_map={"g": "gh"}` | `"xform/^g/gh/"` | generated |
| DP `ur->e` | `vowel_map={"ur": "e"}` | `"xform/ur/v/"` | generated |
| BP `g->gg` | `initial_map={"g": "gg"}` | `"xform/^g/gg/"` | generated |
| POJ `ou->oo` | `vowel_map={"ou": "oo"}` | `"xform/ou/oo/"` | generated |
| TL `ch->ts` | `initial_map={"ch": "ts"}` | `"xform/ch/ts/"` | generated |
| DP `p->b` ending | `ending_map={"p": "b"}` | `"xform/p(\\d)$/b$1/"` | generated |

**問題**: `mappings.py` 定義了結構化的 `initial_map/vowel_map/ending_map`，`export_rime.py` 又以 Rime algebra 字串重新定義了等價的轉換。改一處忘改另一處就會出錯。

### 重複 #2: DP entering endings — 三處定義

- `systems/dp.py`: `entering_endings=["b", "d", "g", "h"]`
- `export_rime.py` SYSTEM_ALGEBRA DP: `"xform/p(\\d)$/b$1/"`, `"xform/t(\\d)$/d$1/"`, `"xform/k(\\d)$/g$1/"`
- `mappings.py` DP: `ending_map={"p": "b", "t": "d", "k": "g"}`

三處都在描述同一事實：DP 的入聲韻尾是 b/d/g 而非 p/t/k。

### 死碼: COMMENT_FORMAT 和 format_comment_format

`export_rime.py` 中的 `COMMENT_FORMAT` dict（lines 453-506）和 `format_comment_format()` 函數（line 1245）**從未被引用**。Comment（候選詞注釋）的轉換完全由 Lua filter 中的 `SYLLABLE_MAP` 查表完成，不需要 Rime 的 algebra。這些是死碼，可直接刪除。

---

## Rime Algebra 與 Comment 的作用說明

### `SYSTEM_ALGEBRA` → `speller/algebra:`

**作用**: 決定用戶的鍵盤輸入如何匹配字典碼。字典中存的是 LATN_NORM 格式（如 `lian5 go2`），algebra 負責在使用者輸入和字典碼之間建立映射。

**Rime algebra 操作符**:
- `xform` — 破壞性替換（只保留轉換結果）
- `derive` — 添加性替換（保留原始 + 新增變體，讓多種輸入都能匹配）
- `abbrev` — 縮寫

**舉例**: POJ 的 `xform/ou/oo/` 表示用戶輸入 `oo` 會被轉成 `ou` 去匹配字典。PUJ 的 `derive/^ch/ts/` 表示用戶輸入 `ts` 或 `ch` 都能匹配。

### Comment 顯示（Lua filter 處理）

候選詞的注釋（comment）由 Lua filter 的 `SYLLABLE_MAP` 查表完成。`SYLLABLE_MAP` 是由 `export_rime.py` 的 `generate_syllable_map()` 函數在 build 時從 Python latn 系統預計算生成，不需要運行時 algebra。

---

## 目標架構

每個 `systems/{system}.py` 成為該系統的 **唯一定義點**，包含：

```python
# systems/poj.py (重構後)
SYSTEM_NAME = "POJ"
def create_config() -> LatnSystemConfig: ...
def create_latn_norm_mapping() -> PhoneticMapping: ...   # POJ -> LATN_NORM
def create_reverse_mapping() -> PhoneticMapping: ...      # LATN_NORM -> POJ
def create_rime_algebra() -> list[str]: ...               # Rime speller algebra
def create_variant_rules() -> dict: ...                   # (optional) variant rules
```

`mappings.py` 和 `export_rime.py` 不再硬編碼任何系統規則，改為：

```python
# mappings.py (重構後)
def register_default_translators(registry):
    for module in _discover_system_modules():
        fwd = module.create_latn_norm_mapping()
        rev = module.create_reverse_mapping()
        if fwd: registry.register_translator(module.SYSTEM_NAME, "LATN_NORM", fwd)
        if rev: registry.register_translator("LATN_NORM", module.SYSTEM_NAME, rev)
```

```python
# export_rime.py (重構後)
def _get_system_algebra(system: str) -> list[str]:
    mod = get_system_module(system)
    return mod.create_rime_algebra()
```

---

## 文件結構

| 文件 | 職責 | 變更類型 |
|---|---|---|
| `scripts/latn/systems/poj.py` | POJ 唯一定義點 | 重構：新增映射/algebra 函數 |
| `scripts/latn/systems/puj.py` | PUJ 唯一定義點 | 重構：新增映射/algebra/variant 函數 |
| `scripts/latn/systems/tl.py` | TL 唯一定義點 | 重構：新增映射/algebra 函數 |
| `scripts/latn/systems/bp.py` | BP 唯一定義點 | 重構：新增映射/algebra 函數 |
| `scripts/latn/systems/dp.py` | DP 唯一定義點 | 重構：新增映射/algebra 函數 |
| `scripts/latn/systems/latn_norm.py` | LATN_NORM pivot 定義 | 不變 |
| `scripts/latn/systems/__init__.py` | 自動發現和註冊 | 微調：新增 get_system_module |
| `scripts/latn/mappings.py` | 跨系統映射註冊 | 重構：改為從系統模組讀取 |
| `scripts/latn/variants.py` | 變體規則生成 | 微調：通用化，不硬編碼 PUJ |
| `scripts/latn/config.py` | 配置類 | 不變 |
| `scripts/latn/converter.py` | 轉換器核心 | 不變 |
| `scripts/latn/translator.py` | 跨系統翻譯器 | 不變 |
| `scripts/latn/registry.py` | 註冊表 | 不變 |
| `scripts/export_rime.py` | Rime 導出 | 重構：從系統模組讀取 algebra；刪除死碼 |

---

## 任務分解

### Task 1: 統一系統模組接口 — 為每個系統文件新增函數

**Files:**
- Modify: `scripts/latn/systems/poj.py`
- Modify: `scripts/latn/systems/puj.py`
- Modify: `scripts/latn/systems/tl.py`
- Modify: `scripts/latn/systems/bp.py`
- Modify: `scripts/latn/systems/dp.py`
- Modify: `scripts/latn/systems/__init__.py`
- Test: `scripts/tests/test_latn_systems.py` (新建)

每個系統文件新增以下函數（按各系統從 `mappings.py` 和 `export_rime.py` 中遷移對應邏輯）：

#### 1a. POJ (`systems/poj.py`)

- [ ] **Step 1: 新增 `SYSTEM_NAME = "POJ"` 常量**

- [ ] **Step 2: 新增 `create_latn_norm_mapping()`**

從 `mappings.py` lines 41-52 遷移：
```python
def create_latn_norm_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        vowel_map={"oo": "ou", "oa": "ua", "oe": "ue"},
        ending_map={
            "n": lambda ending, tone: "t" if tone in (4, 8) else ending,
            "m": lambda ending, tone: "p" if tone in (4, 8) else ending,
            "ng": lambda ending, tone: "k" if tone in (4, 8) else ending,
        },
    )
```

- [ ] **Step 3: 新增 `create_reverse_mapping()`**

從 `mappings.py` lines 54-60 遷移：
```python
def create_reverse_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        vowel_map={"ou": "oo", "ua": "oa", "ue": "oe"},
    )
```

- [ ] **Step 4: 新增 `create_rime_algebra()`**

從 `export_rime.py` lines 524-535 遷移：
```python
_CASE_FOLD = [f"derive/{c.lower()}/{c}/" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

def create_rime_algebra() -> list[str]:
    return [
        "derive/ /-/",
        "derive/[1-8]//",
        "xform/ou/oo/",
        "xform/ua/oa/",
        "xform/ue/oe/",
        "derive/nn//",
    ] + _CASE_FOLD + [
        "abbrev/^([a-z]).+$/$1/",
    ]
```

#### 1b. PUJ (`systems/puj.py`)

- [ ] **Step 1: 新增 `SYSTEM_NAME = "PUJ"` 常量**

- [ ] **Step 2: 新增 `create_latn_norm_mapping()`**

從 `mappings.py` lines 13-19 遷移：
```python
def create_latn_norm_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={"ts": "ch", "tsh": "chh", "z": "j"},
    )
```

- [ ] **Step 3: 新增 `create_reverse_mapping()`**

從 `mappings.py` lines 23-37 遷移：
```python
def create_reverse_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={
            "ch": lambda init, vowel: "ch" if vowel and vowel[0] in ("i", "e") else "ts",
            "chh": lambda init, vowel: "chh" if vowel and vowel[0] in ("i", "e") else "tsh",
            "j": lambda init, vowel: "j" if vowel and vowel[0] in ("i", "e") else "z",
        },
    )
```

- [ ] **Step 4: 新增 `create_rime_algebra()`**

從 `export_rime.py` lines 509-523 遷移：
```python
_CASE_FOLD = [f"derive/{c.lower()}/{c}/" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

def create_rime_algebra() -> list[str]:
    return [
        "derive/ /-/",
        "derive/[1-8]//",
        "derive/^ch/ts/",
        "derive/^chh/tsh/",
        "derive/^j/z/",
        "derive/oinn/ainn/",
        "derive/ien/ian/",
        "derive/iet/iat/",
        "derive/nn//",
    ] + _CASE_FOLD + [
        "abbrev/^([a-z]).+$/$1/",
    ]
```

- [ ] **Step 5: `create_variant_rules()` 已存在（lines 132-138），保持不變**

#### 1c. TL (`systems/tl.py`)

- [ ] **Step 1: 新增 `SYSTEM_NAME = "TL"` 常量**

- [ ] **Step 2: 新增 `create_latn_norm_mapping()`**

從 `mappings.py` lines 64-69 遷移：
```python
def create_latn_norm_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={"ts": "ch", "tsh": "chh"},
    )
```

- [ ] **Step 3: 新增 `create_reverse_mapping()`**

從 `mappings.py` lines 73-78 遷移：
```python
def create_reverse_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={"ch": "ts", "chh": "tsh"},
    )
```

- [ ] **Step 4: 新增 `create_rime_algebra()`**

從 `export_rime.py` lines 536-545 遷移：
```python
_CASE_FOLD = [f"derive/{c.lower()}/{c}/" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

def create_rime_algebra() -> list[str]:
    return [
        "xform/ch/ts/",
        "xform/chh/tsh/",
        "derive/ /-/",
        "derive/[1-8]//",
    ] + _CASE_FOLD + [
        "abbrev/^([a-z]).+$/$1/",
    ]
```

#### 1d. BP (`systems/bp.py`)

- [ ] **Step 1: 新增 `SYSTEM_NAME = "BP"` 常量**

- [ ] **Step 2: 新增 `create_latn_norm_mapping()`**

從 `mappings.py` lines 83-105 遷移：
```python
def create_latn_norm_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={
            "b": "p", "p": "ph", "bb": "b", "bbn": "m", "ln": "n",
            "dd": "d", "d": "t", "t": "th",
            "g": "k", "k": "kh", "ggn": "ng", "gg": "g",
            "z": "ch", "c": "chh", "zz": "j",
        },
        vowel_map={"oo": "ou"},
    )
```

- [ ] **Step 3: 新增 `create_reverse_mapping()`**

從 `mappings.py` lines 107-131 遷移：
```python
def create_reverse_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={
            "p": "b", "ph": "p", "b": "bb", "m": "bbn", "n": "ln",
            "d": "dd", "t": "d", "th": "t",
            "k": "g", "kh": "k", "ng": "ggn", "g": "gg",
            "ch": "z", "chh": "c", "j": "zz",
        },
        vowel_map={"ou": "oo"},
        nasal_prefix={"nn": ("n", ""), "nnh": ("n", "h")},
    )
```

- [ ] **Step 4: 新增 `create_rime_algebra()`**

從 `export_rime.py` lines 546-570 遷移：
```python
_CASE_FOLD = [f"derive/{c.lower()}/{c}/" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

def create_rime_algebra() -> list[str]:
    return [
        "xform/^g/gg/",
        "xform/^b/bb/",
        "xform/^j/zz/",
        "xform/^chh/c/",
        "xform/^ch/z/",
        "xform/^k(?=[^h])/g/",
        "xform/^kh/k/",
        "xform/^p(?=[^h])/b/",
        "xform/^ph/p/",
        "xform/^t(?=[^h])/d/",
        "xform/^th/t/",
        "xform/ou/oo/",
        "xform/^n(?=[^g])/ln/",
        "xform/([aeiou]+)nnh(\\d)$/n$1h$2/",
        "xform/([aeiou]+)nn(\\d)$/n$1$2/",
        "xform/^ng/ggn/",
        "xform/^m/bbn/",
        "derive/ /-/",
        "derive/[1-8]//",
    ] + _CASE_FOLD + [
        "abbrev/^([a-z]).+$/$1/",
    ]
```

#### 1e. DP (`systems/dp.py`)

- [ ] **Step 1: 新增 `SYSTEM_NAME = "DP"` 常量**

- [ ] **Step 2: 新增 `create_latn_norm_mapping()`**

從 `mappings.py` lines 136-155 遷移：
```python
def create_latn_norm_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={
            "b": "p", "p": "ph", "bh": "b",
            "d": "t", "t": "th",
            "g": "k", "k": "kh", "gh": "g",
            "z": "ch", "c": "chh", "r": "j",
        },
        vowel_map={"e": "ur", "ê": "e", "uê": "ue", "iê": "ie"},
        ending_map={"b": "p", "d": "t", "g": "k"},
    )
```

- [ ] **Step 3: 新增 `create_reverse_mapping()`**

從 `mappings.py` lines 157-177 遷移：
```python
def create_reverse_mapping() -> PhoneticMapping:
    return PhoneticMapping(
        initial_map={
            "p": "b", "ph": "p", "b": "bh",
            "t": "d", "th": "t",
            "k": "g", "kh": "k", "g": "gh",
            "ch": "z", "chh": "c", "j": "r",
        },
        vowel_map={"ur": "e", "e": "ê", "ue": "uê", "ie": "iê"},
        ending_map={"p": "b", "t": "d", "k": "g"},
    )
```

- [ ] **Step 4: 新增 `create_rime_algebra()`**

從 `export_rime.py` lines 571-598 遷移：
```python
_CASE_FOLD = [f"derive/{c.lower()}/{c}/" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

def create_rime_algebra() -> list[str]:
    return [
        "xform/^g/gh/",
        "xform/^b/bh/",
        "xform/^j/r/",
        "xform/^chh/c/",
        "xform/^ch/z/",
        "xform/^k(?=[^h])/g/",
        "xform/^kh/k/",
        "xform/^p(?=[^h])/b/",
        "xform/^ph/p/",
        "xform/^t(?=[^h])/d/",
        "xform/^th/t/",
        "xform/ur/v/",
        "xform/p(\\d)$/b$1/",
        "xform/t(\\d)$/d$1/",
        "xform/k(\\d)$/g$1/",
        "derive/ /-/",
        "derive/[1-8]//",
        "derive/d/g/",
        "derive/([aeiu])n$/$1ng/",
        "derive/oinn/ainn/",
        "derive/nn//",
    ] + _CASE_FOLD + [
        "abbrev/^([a-z]).+$/$1/",
    ]
```

#### 1f. 系統模組 `__init__.py` 更新

- [ ] **Step 5: 更新 `systems/__init__.py`**

新增一個 helper 函數來發現所有系統模組：
```python
def get_system_module(system_name: str):
    """Get the module for a specific system by name."""
    return importlib.import_module(f"scripts.latn.systems.{system_name.lower()}")
```

- [ ] **Step 6: 寫測試驗證所有系統模組都有必要的函數**

```python
import unittest
from scripts.latn.systems import register_default_systems, get_system_module
from scripts.latn.registry import LatnRegistry

SYSTEMS = ["poj", "puj", "tl", "bp", "dp"]

class TestSystemModules(unittest.TestCase):
    def test_all_modules_have_required_functions(self):
        for name in SYSTEMS:
            mod = get_system_module(name)
            self.assertTrue(hasattr(mod, "SYSTEM_NAME"), f"{name} missing SYSTEM_NAME")
            self.assertTrue(hasattr(mod, "create_config"), f"{name} missing create_config")
            self.assertTrue(hasattr(mod, "create_latn_norm_mapping"), f"{name} missing create_latn_norm_mapping")
            self.assertTrue(hasattr(mod, "create_reverse_mapping"), f"{name} missing create_reverse_mapping")
            self.assertTrue(hasattr(mod, "create_rime_algebra"), f"{name} missing create_rime_algebra")

    def test_system_name_matches(self):
        for name in SYSTEMS:
            mod = get_system_module(name)
            self.assertEqual(mod.SYSTEM_NAME, name.upper())

    def test_rime_algebra_returns_list(self):
        for name in SYSTEMS:
            mod = get_system_module(name)
            algebra = mod.create_rime_algebra()
            self.assertIsInstance(algebra, list)
            self.assertTrue(len(algebra) > 0)
            for rule in algebra:
                self.assertIsInstance(rule, str)

    def test_mapping_round_trip(self):
        registry = LatnRegistry()
        register_default_systems(registry)
        for name in SYSTEMS:
            mod = get_system_module(name)
            fwd = mod.create_latn_norm_mapping()
            rev = mod.create_reverse_mapping()
            self.assertIsNotNone(fwd)
            self.assertIsNotNone(rev)
```

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_latn_systems -v`

- [ ] **Step 7: Commit**

```bash
git add scripts/latn/systems/ scripts/tests/test_latn_systems.py
git commit -m "refactor: add mapping/algebra functions to each latn system module"
```

---

### Task 2: 重構 `mappings.py` — 改為從系統模組讀取

**Files:**
- Modify: `scripts/latn/mappings.py`
- Test: `scripts/tests/test_latn_systems.py`

- [ ] **Step 1: 重寫 `mappings.py`**

```python
from scripts.latn.config import PhoneticMapping
from scripts.latn.systems import get_system_module

PIVOT = "LATN_NORM"

_SYSTEM_NAMES = ["poj", "puj", "tl", "bp", "dp"]


def register_default_translators(registry):
    for name in _SYSTEM_NAMES:
        mod = get_system_module(name)
        system_name = mod.SYSTEM_NAME
        fwd = mod.create_latn_norm_mapping()
        rev = mod.create_reverse_mapping()
        if fwd:
            registry.register_translator(system_name, PIVOT, fwd)
        if rev:
            registry.register_translator(PIVOT, system_name, rev)
```

- [ ] **Step 2: 執行現有測試確保映射行為不變**

Run: `PYTHONPATH=. python3 -m unittest scripts.tests.test_latn_systems -v`

- [ ] **Step 3: Commit**

```bash
git add scripts/latn/mappings.py
git commit -m "refactor: mappings.py reads from system modules"
```

---

### Task 3: 重構 `export_rime.py` — 移除硬編碼的 SYSTEM_ALGEBRA，刪除死碼

**Files:**
- Modify: `scripts/export_rime.py`
- Test: 運行 `bash build.sh` 驗證生成結果

- [ ] **Step 1: 新增系統模組導入**

在 `export_rime.py` 中新增：
```python
from scripts.latn.systems import get_system_module
```

- [ ] **Step 2: 刪除死碼 `COMMENT_FORMAT` dict（lines 453-506）**

整個 `COMMENT_FORMAT = {...}` dict 從未被引用，直接刪除。

- [ ] **Step 3: 刪除死碼 `format_comment_format()` 函數（line 1245）**

同樣從未被調用，直接刪除。

- [ ] **Step 4: 刪除 `SYSTEM_ALGEBRA` dict（lines 508-598），改為動態讀取**

```python
def _get_system_algebra(system: str) -> list[str]:
    mod = get_system_module(system)
    return mod.create_rime_algebra()
```

更新 `write_schema()` 中引用 `SYSTEM_ALGEBRA[system]` 的地方（line 1472）改為 `_get_system_algebra(system)`。

- [ ] **Step 5: 刪除 `CASE_FOLD` 定義（line 451）**

`CASE_FOLD` 已內嵌在各系統模組的 `create_rime_algebra()` 中，`export_rime.py` 不再需要獨立定義。確認無其他引用後移除。

- [ ] **Step 6: 完整 build 驗證**

Run: `bash build.sh`

比對新生成的 YAML schema 文件中的 algebra 段落與重構前的一致：
```bash
diff <(grep -A 30 "algebra:" export/rime/rime-hokkien/hokkien_poj.schema.yaml) \
     <(git show HEAD:export/rime/rime-hokkien/hokkien_poj.schema.yaml | grep -A 30 "algebra:")
```

對所有 5 個系統（poj, tl, bp, puj, dp）重複此比對，確認 algebra 段落完全一致。

- [ ] **Step 7: Commit**

```bash
git add scripts/export_rime.py
git commit -m "refactor: export_rime.py reads algebra from system modules; remove dead COMMENT_FORMAT"
```

---

### Task 4: 重構 `variants.py` — 通用化 variant 規則發現

**Files:**
- Modify: `scripts/latn/variants.py`

- [ ] **Step 1: 改為通用化發現**

```python
import re
import itertools
from scripts.latn.systems import get_system_module


def _compile_rules(raw_rules):
    return [(re.compile(pat), variants) for pat, variants in raw_rules.items()]


def _split_syllables(text):
    syllable_re = re.compile(r"[A-Za-z\u00C0-\u1EFF\u0300-\u036F\u207F]+")
    parts = []
    last = 0
    for m in syllable_re.finditer(text):
        if m.start() > last:
            parts.append(("sep", text[last : m.start()]))
        parts.append(("syl", m.group()))
        last = m.end()
    if last < len(text):
        parts.append(("sep", text[last:]))
    return parts


def get_variants(text, system_name):
    mod = get_system_module(system_name.lower())
    if not hasattr(mod, "create_variant_rules"):
        return [text]

    rules = _compile_rules(mod.create_variant_rules())
    parts = _split_syllables(text)
    syl_indices = [i for i, (t, _) in enumerate(parts) if t == "syl"]

    if not syl_indices:
        return [text]

    applicable_per_syl = []
    for idx in syl_indices:
        syl = parts[idx][1]
        matched = []
        for ri, (pat, _) in enumerate(rules):
            if pat.search(syl):
                matched.append(ri)
        applicable_per_syl.append(matched)

    combo_choices = []
    for ri, (pat, variants) in enumerate(rules):
        choices = set()
        for matched in applicable_per_syl:
            if ri in matched:
                choices.update(variants)
        if not choices:
            choices = {None}
        combo_choices.append(sorted(choices, key=lambda x: (x is None, x)))

    results = []
    for combo in itertools.product(*combo_choices):
        rebuilt = list(parts)
        for syl_i, idx in enumerate(syl_indices):
            syl = parts[idx][1]
            for ri in applicable_per_syl[syl_i]:
                if combo[ri] is None:
                    continue
                pat, _ = rules[ri]
                syl = pat.sub(combo[ri], syl)
            rebuilt[idx] = ("syl", syl)

        results.append("".join(v for _, v in rebuilt))

    return results
```

- [ ] **Step 2: 驗證**

Run: `PYTHONPATH=. python3 -c "from scripts.latn.variants import get_variants; print(get_variants('sṳ', 'PUJ'))"`

Expected: `['sṳ', 'su', 'si']`

- [ ] **Step 3: Commit**

```bash
git add scripts/latn/variants.py
git commit -m "refactor: variants.py uses generic system module discovery"
```

---

### Task 5: 驗證 — 完整回歸測試

**Files:** All modified files

- [ ] **Step 1: 運行完整測試套件**

Run: `bash test.sh`

- [ ] **Step 2: 完整 build 並 diff 輸出**

Run: `bash build.sh`

```bash
for pkg in rime-hokkien rime-teochew; do
  for schema in export/rime/$pkg/*.schema.yaml; do
    echo "=== $schema ==="
  done
done
```

確認所有生成文件與重構前功能等價。

- [ ] **Step 3: Commit（如果有測試調整）**

```bash
git add -A
git commit -m "refactor: latn single source of truth - final cleanup"
```

---

## 風險與注意事項

1. **Rime algebra 的 xform vs derive 語義差異**: `SYSTEM_ALGEBRA` 中的 `xform` 是破壞性替換（只保留最後結果），`derive` 是添加性替換（保留原來的+新的）。從 `mappings.py` 的結構化映射生成 Rime algebra 時需特別注意這個差異。本計劃直接遷移已驗證的 algebra 字串，不做自動生成，以降低風險。

2. **BP 和 DP 的 nasal prefix 處理**: BP 的 `nasal_prefix` 在 `mappings.py` 和 Rime algebra 中用了完全不同的表達方式（結構化 vs regex），但語義等價。遷移時保持各自範式的表達，不做跨範式自動轉換。

3. **CASE_FOLD**: 重構後每個系統模組的 `create_rime_algebra()` 自帶 CASE_FOLD，`export_rime.py` 不再需要獨立定義。需確保移除時不影響其他引用。

4. **向後兼容**: `mappings.py` 的公共接口 `register_default_translators(registry)` 不變，所有調用方（`__init__.py`）不需修改。

5. **COMMENT_FORMAT 刪除安全**: 經確認 `COMMENT_FORMAT` dict 和 `format_comment_format()` 函數在整個 codebase 中無任何調用點。Comment 顯示完全由 Lua filter 的 `SYLLABLE_MAP` 查表處理，刪除不影響任何功能。
