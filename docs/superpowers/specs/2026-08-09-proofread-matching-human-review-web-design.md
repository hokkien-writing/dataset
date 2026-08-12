# Proofread Matching 人工审阅网页设计

## 目标

把本次验证过的本机审校网页沉淀到 `proofread-matching` skill。匹配流程遇到必须由人判断的词条时，生成通用审阅 bundle，启动本机网页收集决定，再通过现有 stale-safe review gate 回写。

## 触发范围

网页只接收：

- `real` 记录；
- `ambiguous` 配对；
- 使用者明确标记为 `deferred` 的记录；
- 无法产生安全 patch 的结构性问题。

`identical` 不进入审阅。已由 pair policy 验证安全的 `cosmetic` 与 `systematic` 保持原有 review／accepted gate，不占用人工网页。

## 架构

### Bundle adapter

在 `scripts/proof/review_bundle.py` 增加通用 bundle adapter。它把 `ReviewRecord`、residue 和调用者提供的结构问题转换为 `proofread-review-bundle/v1`，并合并稳定 ID 相同的多个问题。

每笔记录保留：stable ID、decision key、rules version、run audit、来源内容摘要、两侧原始记录、bucket、ambiguity、差异轴、headword/gloss kind、patch 提案、页码字段与证据说明。

### Local review server

在 `scripts/review_web/` 内置 Python 标准库 HTTP 服务与原生 HTML/CSS/JavaScript。服务只绑定 `127.0.0.1`，提供静态网页、bundle API、健康检查和可选 PDF 页面渲染缓存。

运行时可传入 bundle、决定输出位置、PDF 路径和缓存目录。网页只写浏览器 localStorage 和使用者明确导出的决定 JSON，不直接修改 corpus。

### Decision adapter

在 `scripts/proof/review_bundle.py` 导入 `proofread-review-decisions/v1`。导入必须同时验证 schema、bundle hash、rules version、run audit、decision key 和来源内容摘要。验证通过的结果转换回现有 `Decision`／`Patch`；只有 `accepted` 能由 `apply_accepted_records` 应用，`rejected` 与 `deferred` 只保留审计状态。

## PDF 配置与交互

Bundle 顶层可声明：

```json
{
  "document": {
    "pdf_path": "/path/to/source.pdf",
    "page_field": "page",
    "page_offset": 24
  }
}
```

`page_field` 是每笔来源记录中保存词典页码的指定列名；`page_offset` 是该值映射到 PDF 页码时使用的整数偏移。

切换词条时，网页读取新记录的 `page_field`，加上 `page_offset` 并自动定位 PDF。使用者可在页码输入框跳转到任意合法 PDF 页面，也可用前后页按钮浏览；手动浏览不改变记录来源页码。切换上一笔或下一笔时重新自动定位。提供“回到词条页”按钮。

页码必须是整数且介于 1 与 PDF 总页数之间。越界时保留当前页面并显示错误。配置、字段或值缺失时保留当前 PDF 页面并显示“本词条无来源页码”。PDF 不可用时，文字审阅区继续工作。

原书区使用鼠标滚轮以游标为中心缩放、拖曳平移、双击恢复适合宽度。

## 网页操作

使用密集审阅界面：记录列表、原书页、字段证据与决定表单并列。每个字段可选择 source、reference、proposed patch 或自订最终值；选择后仍可编辑。记录支持 accepted、rejected、deferred，并可填写备注。

浏览器草稿按 bundle hash 存入 localStorage。导出 JSON 包含完整决定证据；重新导入时执行与 Python adapter 相同的基础版本和摘要检查。

## 错误与安全边界

- 服务只接受 loopback host。
- 静态路由和 PDF 路由采用 allowlist，拒绝路径穿越和任意文件读取。
- PDF 页面采用临时文件渲染后 atomic rename；失败不留下半成品缓存。
- 任一 stale 绑定不符时整笔决定保持 stale，不部分应用。
- 网页只收集决定；实际修改仍经过 `apply_accepted_records`、精确 raw old value 比较、rollback 与重跑 audit。

## Skill 文档结构

保持 `SKILL.md` 的核心流程简洁：在 triage/review 后加入一个 “Human review web” 分支，并更新 description，使“人工审阅、人工裁定、审阅网页”能触发 skill。

详细 bundle schema、命令、PDF 配置、导入导出与失败处理放在 `references/human-review-web.md`。可执行代码放在 `scripts/review_web/` 与 `scripts/proof/review_bundle.py`。不增加 README 或重复说明。

## 测试与验收

- bundle 只包含约定人工范围；同 stable ID 的多问题合并成一笔；
- bundle → 决定 → ingest round-trip 保留完整证据；
- stale bundle hash、rules version、run audit、decision key 或 source digest 均被拒绝；
- accepted-only 回写 gate 保持不变；
- PDF `page_field` 与 `page_offset` 映射正确；
- 任意页跳转、前后翻页、回到词条页及切换词条自动定位正确；
- PDF 缺失、页码缺失与渲染失败时文字审阅可继续；
- 滚轮缩放、拖曳、双击复位、自订、筛选、自动暂存及 JSON 导入导出正常；
- 服务 loopback 与路径安全测试通过；
- skill validator、skill 自带 Python 测试、JavaScript syntax check 与浏览器桌面／窄屏测试通过。
