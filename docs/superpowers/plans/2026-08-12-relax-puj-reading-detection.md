# 放宽 PUJ 读音识别实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让含第一调无调号音节的 PUJ 片段仍可被识别，并将连续的 PUJ／英文例句正确拆分。

**Architecture:** 保留现有字符白名单、小写开头和 PUJ 调号证据，只把判定阈值从“至少半数 token 带调号”改为“至少一个 token 带调号”。通过 `postprocess()` 公共入口验证真实 wikitext，同时用纯英文反例防止过度拆分。

**Tech Stack:** Python 3.10+、`re`、`unittest`、现有 007 wikisource 后处理器。

## Global Constraints

- 不新增第三方依赖。
- 不加入 Python 源码注释。
- 纯英文片段不得被识别为 PUJ。
- 正式产物必须由生成命令覆盖，不手工编辑。

---

### Task 1: 放宽 PUJ 片段识别并锁定真实案例

**Files:**
- Modify: `scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.py`
- Test: `scripts/tests/test_wikisource_007.py`

**Interfaces:**
- Consumes: `postprocess(text: str, title: str = "") -> str`
- Produces: 包含至少一个 PUJ 调号 token 的合法小写罗马字片段可作为读音参与拆分。

- [ ] **Step 1: 写失败测试**

在 `TestReformatEntries` 中用真实 `; ...`／`: ...` wikitext 断言最终输出两条例句，并断言纯英文冒号释义仍保持一条。

- [ ] **Step 2: 运行测试确认失败**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_wikisource_007.TestReformatEntries.test_puj_with_unmarked_first_tone_tokens_splits_embedded_example -v`

Expected: FAIL，输出仍为一条例句。

- [ ] **Step 3: 最小实现**

修改 `_is_reading_seg()`，保留格式约束并改为 `marked >= 1`。

- [ ] **Step 4: 运行相关测试**

Run: `PYTHONPATH=. .venv/bin/python -m unittest scripts.tests.test_wikisource_007 scripts.tests.test_processor_007 -v`

Expected: PASS。

### Task 2: 重建并验证正式产物

**Files:**
- Modify: `books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md`
- Modify: `export/books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv`

**Interfaces:**
- Consumes: 007 `postprocess()` 输出。
- Produces: 更新后的正式 Markdown 与保序 CSV。

- [ ] **Step 1: 离线重建 Markdown**

Run: `PYTHONPATH=. .venv/bin/python -m scripts.wikisource --title "Dictionary of the Swatow dialect.djvu" --start 1 --end 648 --output books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md --cache-dir tmp/dictionary_of_the_swatow_dialect --offline`

- [ ] **Step 2: 仅导出 007 CSV**

Run: `PYTHONPATH=. .venv/bin/python scripts/export_csv.py --book 007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect --preserve-order`

- [ ] **Step 3: 验证目标条目和确定性**

确认目标内容拆成两项、648 个页标记连续，并以第二次生成的 SHA-256 核对结果稳定。
