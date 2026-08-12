# 007 人工校订网页

这个本机工具提供两种审校模式：

- **proofread 模式**：对照校对 131 个唯一词条中的 133 个未决问题。
- **corrections 模式**：将权威 CSV 中 3,021 条 007 修正规则逐条对照原书 PDF 审查，并把已接受的决定经显式门控回写到 CSV。

审校网页本身绝不直接修改 CSV、007 修正表、Markdown 或原书 PDF；回写是独立的显式 CLI 步骤（见「回写决定到 CSV」）。

## 启动（proofread 模式）

从项目根目录运行：

```bash
PYTHONPATH=. python3 scripts/run_proofread_review.py \
  --pdf "/Users/lim/Desktop/A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.pdf"
```

服务只监听 `127.0.0.1:8765`，启动后自动打开浏览器。若端口被占用，可传入 `--port 8766`。不想自动打开浏览器时使用 `--no-open`。

## 审校（proofread 模式）

- 资料中的页码已经是 PDF 页码，原书按该值直接定位，不再增加偏移。
- 游标停在原书区时，滚动鼠标滚轮缩放；按住拖曳移动；双击恢复适合宽度。
- 每个字段可选择当前值或人工提案，选择后仍可编辑最终值。
- 「如何处理此匹配」可标记错配、单侧修改、左右分别处理、拆分或改配，并在单一「补充说明」中自然描述具体做法。
- 错配／取消配对本身即表示排除普通回写；拆分、改配、单侧或分别处理必须填写补充说明，由 AI 结合处理选项与证据逐项理解。
- 「确认并下一条」会把记录标为已确认；「稍后决定」保留为待处理决定。
- 浏览器会按资料版本自动暂存。不要用无痕模式进行长期审校。

## 备份与恢复

随时点击「导出 JSON」。决定档包含资料版本、稳定 ID、原值摘要、最终值、备注与时间。导出的 `accepted` 记录才可进入后续回写；`deferred` 记录不会被应用。

点击「导入决定」可恢复进度。资料版本或原值摘要不符时，导入会失败，避免旧决定覆盖新资料。

## 页面缓存

PDF 页面按需渲染到 `tmp/proofread-review-pages/`。删除该目录只会让页面在下次查看时重新渲染，不影响决定。渲染需要 Poppler 的 `pdfinfo` 与 `pdftoppm`。

## 重建审校资料

审计证据保存在 `review_actions_source.json`。重新生成 proofread 资料（默认模式）：

```bash
PYTHONPATH=. python3 -m scripts.proofread_review.build_data
```

生成器会读取权威合并校对 CSV 与当前 007 读音修正表，并验证稳定 ID、页码和问题分类。

## 修正规则审查（corrections 模式）

### 重建修正审校资料

```bash
PYTHONPATH=. .venv/bin/python -m scripts.proofread_review.build_data \
  --mode corrections \
  --corrections scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv \
  --output tmp/007-correction-review-data.json
```

生成队列必须完全清点：3,021 条记录 ＝ reading 997 ＋ gloss 2 ＋ example_split 4 ＋ review 2,015 ＋ headword_review 3，且 `unresolved=0 ambiguous=0 page_offset=0`。任一非零都必须停止并导出診斷，不得啟動不完整的隊列。

### 启动修正审查服务器

```bash
PYTHONPATH=. .venv/bin/python scripts/run_proofread_review.py \
  --data tmp/007-correction-review-data.json \
  --decisions tmp/007-correction-review-decisions.json \
  --pdf "/Users/lim/Desktop/A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.pdf" \
  --page-field page \
  --page-offset 0 \
  --port 8765
```

- `--page-field page --page-offset 0`：修正规则的 `page` 即 PDF 页码，不加偏移。
- 键值字段（rule_id、rule_type、headword、key_reading、key_gloss、key_page）只读；可编辑 replacement 最终值并添加备注。
- `example_split` 渲染为成对行编辑器：新增／移除／重排行，序列化时对齐换行字段并在接受前校验行数一致。

### 决定语义

| 决定 | CSV 结果 |
| --- | --- |
| `accepted` 且最终值 ＝ 现值 | `enabled=false`、`review_status=rejected`、保留原 replacement |
| `accepted` 且最终值 ≠ 现值 | `enabled=true`、`review_status=accepted`、replacement 更新为最终值 |
| `rejected` | `enabled=false`、`review_status=rejected`、保留原 replacement（不写入最终值） |
| `deferred` | 不改 CSV，rule_id 列入回写计划的 `deferred` 清单 |

拒绝不需要备注；结构性动作（拆分行数变化等）与键值／页码异议必须填写备注。

### 回写决定到 CSV（dry-run → apply）

```bash
PYTHONPATH=. .venv/bin/python -m scripts.proofread_review.correction_writeback \
  --data tmp/007-correction-review-data.json \
  --decisions tmp/007-correction-review-decisions.json \
  --corrections scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv \
  --plan tmp/007-correction-writeback-plan.json
```

- 默认只写出计划（dry-run），不修改 CSV。加 `--apply` 才真正套用。
- 计划 schema：`007-correction-csv-writeback-plan/v1`，含 `catalog_digest`、`changes`（`rule_id` ＋ 原始 `old_rows` ＋ 新 `new_rows` ＋ `decision_id`）、`unchanged`、`deferred`。
- 防呆：资料版本或原值摘要不符时导入失败；CSV digest 不符或任一条 `old_rows` 与现档不一致时拒绝套用；套用后以 `load_correction_catalog()` 重新验证，写同目录暂存文件后原子替换（`os.replace`）。
- 被拒绝的规则保留在 CSV 中供稽核，但 `enabled=false`；deferred 规则保持原样。

## 重新生成正式产物

已审校的 CSV 提交后，重新生成 Markdown 与所选书的汇出 CSV：

```bash
PYTHONPATH=. .venv/bin/python -m scripts.wikisource \
  --title "Dictionary of the Swatow dialect.djvu" \
  --start 1 --end 648 \
  --output books/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.md \
  --cache-dir tmp/dictionary_of_the_swatow_dialect \
  --offline

PYTHONPATH=. .venv/bin/python scripts/export_csv.py \
  --book 007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect \
  --preserve-order
```

## 稽核检查

重新生成后必须验证：

- 页标记 1–648，解析／汇出条目 48,597。
- catalog 验证零错误。
- catalog digest 与 review ID 稳定（CSV 行重排后不变）。
- 第二次重新生成得到完全相同的产物哈希（确定性）。

## 回滚

权威 CSV 在迁移时已提交（`data(007): migrate correction rules to CSV`）。回写出错时，从该提交恢复 CSV：

```bash
git restore --source=bb80a0b -- scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv
```

然后按「重新生成正式产物」重做 Markdown 与汇出 CSV。之后的修正与审查一律在 CSV 上进行，不再有 Python 常量来源。

## 迁移不变量

- 权威来源：`scripts/wikisource/007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.csv`。
- 當前邏輯規則數：reading 997、gloss 2、example_split 4、review 2,015、headword_review 3，共 3,021；7 條 example_split 與 3 條 reading／review 規則已由通用解析器或 007 專屬正規化穩定取代。
- 键值在 UTF-8 CSV 往返后逐字节保留；不归一化 PUJ、英文、空白、标点或 Unicode。
- 优先序固定：headword review → review → example split → gloss → reading。
- 每条普通规则一列；`example_split` 每个输出一列，同 `rule_id` 的 `output_index` 连续从 1 开始。
- 对 007 修正键，`page` 即 PDF 页码，offset 恰为 0。
- 只有 accepted 且绑定数据版本的决定能改 CSV；逐条 exact old-value 比对为必要条件。
- 重建相同输入必须重现已有的 catalog digest、review ID、bundle 版本、Markdown 与汇出 CSV。
- 不加第三方依赖、不手改产出的汇出 CSV、不加 Python 源码注释。

## CSV 栏位

固定表头与顺序：

```text
rule_id,rule_type,headword,key_reading,key_gloss,page,output_index,replacement_reading,replacement_gloss,enabled,review_status,note
```

- `rule_type`：`reading | gloss | example_split | review | headword_review`
- `enabled`：`true | false`
- `review_status`：`pending | accepted | rejected | deferred`
- `reading`：`replacement_reading` 必填，`replacement_gloss` 空，`output_index=1`。
- `gloss`：`replacement_gloss` 必填，`replacement_reading` 空，`output_index=1`。
- `review` / `headword_review`：至少一个 replacement 字段非空，`output_index=1`。
- `headword_review`：`headword` 必填；其余类型必须为空。
- `example_split`：每 `rule_id` 至少两列，两个 replacement 字段皆必填，`output_index=1..N` 不跳号。
- `page` 为正十进制 PDF 页码。
- `rule_id` 为确定值：`007-<rule_type>-<SHA-256(headword/key 栏)前 16 hex>`。

## 验证

```bash
PYTHONPATH=. .venv/bin/python -m unittest \
  scripts.tests.test_proofread_review \
  scripts.tests.test_proofread_review_static \
  scripts.tests.test_correction_writeback \
  scripts.tests.test_wikisource_corrections \
  scripts.tests.test_wikisource_007 \
  scripts.tests.test_processor_007 \
  scripts.tests.test_export_csv_cli
```
