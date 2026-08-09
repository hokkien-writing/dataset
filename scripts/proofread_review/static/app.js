"use strict";

const DECISION_SCHEMA = "proofread-review-decisions/v1";
const ISSUE_LABELS = {
  cross_type: "读音＋释义冲突",
  empty_key: "空键结构修正",
  existing_key_conflict: "既有键冲突",
  truncated_gloss: "释义可能截断",
  rule_review: "规则人工复核",
};
const RULE_TYPE_LABELS = {
  reading: "读音修正",
  gloss: "释义修正",
  example_split: "例句拆分",
  review: "人工复核",
  headword_review: "字目复核",
};
const NORMAL_DISPOSITION = "normal_match";
const REVIEWABLE_STATUSES = ["accepted", "deferred", "rejected"];

const state = {
  dataset: null,
  decisions: {},
  filtered: [],
  activeId: null,
  shownPdfPage: null,
  pdfPages: 648,
  pageOffset: 0,
  viewer: { scale: 1, x: 0, y: 0, dragging: false, pointerId: null, lastX: 0, lastY: 0 },
};

const el = (id) => document.getElementById(id);
const elements = {};
const graphemeSegmenter = typeof Intl.Segmenter === "function"
  ? new Intl.Segmenter(undefined, { granularity: "grapheme" })
  : null;

function graphemes(value) {
  return graphemeSegmenter
    ? [...graphemeSegmenter.segment(value)].map((item) => item.segment)
    : Array.from(value);
}

function characterDiff(before, after) {
  const left = graphemes(before);
  const right = graphemes(after);
  const rows = Array.from({ length: left.length + 1 }, () => new Uint32Array(right.length + 1));
  for (let i = left.length - 1; i >= 0; i -= 1) {
    for (let j = right.length - 1; j >= 0; j -= 1) {
      rows[i][j] = left[i].normalize("NFC") === right[j].normalize("NFC")
        ? rows[i + 1][j + 1] + 1
        : Math.max(rows[i + 1][j], rows[i][j + 1]);
    }
  }
  const operations = [];
  let i = 0;
  let j = 0;
  while (i < left.length || j < right.length) {
    if (i < left.length && j < right.length && left[i].normalize("NFC") === right[j].normalize("NFC")) {
      operations.push({ type: "equal", value: left[i] });
      i += 1;
      j += 1;
    } else if (j < right.length && (i === left.length || rows[i][j + 1] >= rows[i + 1][j])) {
      operations.push({ type: "add", value: right[j] });
      j += 1;
    } else {
      operations.push({ type: "remove", value: left[i] });
      i += 1;
    }
  }
  return operations;
}

function appendDiff(element, operations, side, emptyLabel) {
  const visible = operations
    .filter((part) => part.type === "equal" || part.type === side)
    .reduce((runs, part) => {
      const last = runs.at(-1);
      if (last?.type === part.type) last.value += part.value;
      else runs.push({ ...part });
      return runs;
    }, []);
  if (!visible.length) {
    element.textContent = emptyLabel;
    return;
  }
  element.replaceChildren(...visible.map((part) => {
    const span = document.createElement("span");
    span.textContent = part.value;
    if (part.type !== "equal") span.className = `diff-${part.type}`;
    return span;
  }));
}

function renderDiffPair(currentElement, proposalElement, current, proposal) {
  const operations = characterDiff(current, proposal);
  appendDiff(currentElement, operations, "remove", "（空）");
  appendDiff(proposalElement, operations, "add", "（无提案）");
}

function storageKey() {
  return `proofread-review:${state.dataset.data_version}`;
}

function showError(message) {
  elements.errorBanner.textContent = message;
  elements.errorBanner.hidden = false;
}

function clearError() {
  elements.errorBanner.hidden = true;
  elements.errorBanner.textContent = "";
}

function loadDecisions() {
  try {
    let saved = localStorage.getItem(storageKey());
    if (!saved) {
      for (const version of state.dataset.compatible_data_versions || []) {
        saved = localStorage.getItem(`proofread-review:${version}`);
        if (saved) break;
      }
    }
    state.decisions = saved ? JSON.parse(saved) : {};
    if (saved) saveDecisions();
  } catch (error) {
    state.decisions = {};
    showError(`无法读取浏览器暂存：${error.message}`);
  }
}

function saveDecisions() {
  try {
    localStorage.setItem(storageKey(), JSON.stringify(state.decisions));
    elements.saveState.textContent = `已自动暂存 · ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    showError(`自动暂存失败，请立即导出 JSON：${error.message}`);
  }
}

function currentRecord() {
  return state.dataset.records.find((record) => record.id === state.activeId) || null;
}

function currentDecision(record = currentRecord()) {
  if (!record) return null;
  if (!state.decisions[record.id]) {
    state.decisions[record.id] = {
      status: "pending",
      choices: { reading: "", gloss: "" },
      final: {
        reading: record.proposal.reading || record.current.reading,
        gloss: record.proposal.gloss || record.current.gloss,
      },
      note: "",
      disposition: NORMAL_DISPOSITION,
      updated_at: "",
    };
  }
  const decision = state.decisions[record.id];
  decision.disposition ||= NORMAL_DISPOSITION;
  migrateLegacyTreatment(decision);
  return decision;
}

function migrateLegacyTreatment(decision) {
  const legacy = [
    ["left_action", "左侧 CSV"],
    ["source_007_action", "007"],
    ["rematch_target", "改配目标"],
  ].flatMap(([key, label]) => decision[key]?.trim() ? [`${label}：${decision[key].trim()}`] : []);
  if (legacy.length) {
    decision.note = [decision.note?.trim(), ...legacy].filter(Boolean).join("\n");
  }
  delete decision.left_action;
  delete decision.source_007_action;
  delete decision.rematch_target;
  return decision;
}

function statusOf(record) {
  return state.decisions[record.id]?.status || "pending";
}

function isSplitRecord(record) {
  return record?.context?.rule_type === "example_split";
}

function applyFilters() {
  const status = elements.statusFilter.value;
  const ruleType = elements.ruleTypeFilter.value;
  const query = elements.searchInput.value.trim().toLocaleLowerCase();
  state.filtered = state.dataset.records.filter((record) => {
    if (status !== "all" && statusOf(record) !== status) return false;
    if (ruleType !== "all" && record.context.rule_type !== ruleType) return false;
    if (!query) return true;
    const haystack = [
      record.page,
      record.context.headword,
      record.context.term,
      record.context.key_reading,
      record.current.reading,
      record.current.gloss,
      record.proposal.reading,
      record.proposal.gloss,
    ].join(" ").toLocaleLowerCase();
    return haystack.includes(query);
  });
  if (!state.filtered.some((record) => record.id === state.activeId)) {
    state.activeId = state.filtered[0]?.id || null;
  }
  renderList();
  renderRecord();
}

function renderList() {
  elements.listSummary.textContent = `显示 ${state.filtered.length} / ${state.dataset.record_count} 个词条`;
  elements.recordList.replaceChildren(...state.filtered.map((record) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const status = statusOf(record);
    const ruleLabel = RULE_TYPE_LABELS[record.context.rule_type] || record.context.rule_type || "";
    button.type = "button";
    button.className = `record-item is-${status}${record.id === state.activeId ? " is-active" : ""}`;
    button.dataset.recordId = record.id;
    button.innerHTML = `<span class="record-status"></span><span class="record-main"><span class="record-top"><span>第 ${record.page} 页</span><span>${ruleLabel} · ${record.issues.length} 个问题</span></span><span class="record-name"></span><span class="record-reading"></span></span>`;
    button.querySelector(".record-name").textContent = record.context.headword || record.context.term || "未命名词条";
    button.querySelector(".record-reading").textContent = `${record.context.rule_id || ""} · ${record.proposal.reading || record.current.reading || "无读音"}`;
    item.append(button);
    return item;
  }));
}

function renderRuleKeys(record) {
  const rows = [
    ["规则 ID", record.context.rule_id || "（无）"],
    ["规则类型", record.context.rule_type || "（无）"],
    ["字目", record.context.headword || "（空）"],
    ["键读音", record.context.key_reading || "（空）"],
    ["键释义", record.context.key_gloss || "（空）"],
    ["键页码", record.context.key_page || "（空）"],
    ["解析页码", record.context.resolved_page || "（空）"],
    ["输出条数", record.context.output_count || "1"],
  ];
  const nodes = [];
  for (const [term, description] of rows) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = term;
    dd.textContent = description;
    nodes.push(dt, dd);
  }
  elements.ruleKeyList.replaceChildren(...nodes);
  elements.ruleTypeBadge.textContent = RULE_TYPE_LABELS[record.context.rule_type] || record.context.rule_type || "";
}

function escapeHtml(value) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function splitRows(decision) {
  const readings = (decision.final.reading || "").split("\n");
  const glosses = (decision.final.gloss || "").split("\n");
  const count = Math.max(readings.length, glosses.length, 1);
  return Array.from({ length: count }, (_, i) => ({
    reading: readings[i] || "",
    gloss: glosses[i] || "",
  }));
}

function collectSplitRows() {
  return [...elements.splitRows.querySelectorAll(".split-row")].map((rowElement) => ({
    reading: rowElement.querySelector('input[data-slot="reading"]').value,
    gloss: rowElement.querySelector('input[data-slot="gloss"]').value,
  }));
}

function commitSplitRows(decision) {
  const rows = collectSplitRows();
  decision.final.reading = rows.map((row) => row.reading).join("\n");
  decision.final.gloss = rows.map((row) => row.gloss).join("\n");
  decision.status = "pending";
  decision.updated_at = new Date().toISOString();
  return rows;
}

function renderSplitEditor(record, decision) {
  const rows = splitRows(decision);
  const count = rows.length;
  elements.splitRows.replaceChildren(...rows.map((row, index) => {
    const wrap = document.createElement("div");
    wrap.className = "split-row";
    wrap.dataset.rowIndex = String(index);
    wrap.innerHTML = `
      <input data-slot="reading" aria-label="第 ${index + 1} 行读音" value="${escapeHtml(row.reading)}">
      <input data-slot="gloss" aria-label="第 ${index + 1} 行释义" value="${escapeHtml(row.gloss)}">
      <div class="split-actions">
        <button type="button" class="icon-button" data-action="move" data-direction="up" aria-label="上移本行" ${index === 0 ? "disabled" : ""}>↑</button>
        <button type="button" class="icon-button" data-action="move" data-direction="down" aria-label="下移本行" ${index === count - 1 ? "disabled" : ""}>↓</button>
        <button type="button" class="icon-button" data-action="remove" aria-label="删除本行" ${count <= 1 ? "disabled" : ""}>×</button>
      </div>
    `;
    return wrap;
  }));
  elements.splitEditor.hidden = false;
  elements.splitAdd.disabled = false;
}

function validateSplitRows(record, decision) {
  if (!isSplitRecord(record)) return true;
  const rows = collectSplitRows();
  if (!rows.length || rows.some((row) => !row.reading.trim() || !row.gloss.trim())) {
    showError("拆分行必须至少一行，且每行的读音与释义都要填写");
    return false;
  }
  return true;
}

function renderRecord() {
  const record = currentRecord();
  const disabled = !record;
  elements.reviewForm.querySelectorAll("button, input, textarea").forEach((control) => { control.disabled = disabled; });
  if (!record) {
    elements.recordTitle.textContent = "没有符合筛选条件的词条";
    elements.recordPosition.textContent = "— / —";
    elements.issueTags.replaceChildren();
    elements.splitEditor.hidden = true;
    return;
  }
  const decision = currentDecision(record);
  const index = state.filtered.findIndex((item) => item.id === record.id);
  elements.recordPosition.textContent = `${index + 1} / ${state.filtered.length} · 资料列 ${record.row + 2}`;
  elements.recordTitle.textContent = record.context.headword || record.context.term || record.current.reading || "未命名词条";
  elements.issueTags.replaceChildren(...record.issues.map((issue) => {
    const tag = document.createElement("span");
    tag.className = "issue-tag";
    tag.textContent = ISSUE_LABELS[issue] || issue;
    return tag;
  }));
  renderRuleKeys(record);
  const isSplit = isSplitRecord(record);
  elements.fieldReading.hidden = isSplit;
  elements.fieldGloss.hidden = isSplit;
  if (isSplit) {
    renderSplitEditor(record, decision);
  } else {
    for (const field of ["reading", "gloss"]) {
      renderDiffPair(
        el(`${field}-current`),
        el(`${field}-proposal`),
        record.current[field] || "",
        record.proposal[field] || "",
      );
      el(`${field}-final`).value = decision.final[field] ?? "";
      updateChoiceUI(field, decision.choices[field]);
    }
  }
  elements.decisionNote.value = decision.note || "";
  elements.matchDisposition.value = decision.disposition;
  renderTreatment(decision.disposition, decision.status);
  elements.evidenceList.replaceChildren();
  const evidence = [
    ["修正表键", record.table_key.join(" · ")],
    ["左侧字目", record.context.headword || "（空）"],
    ["左侧读音", record.context.left_reading || "（空）"],
    ["左侧释义", record.context.left_gloss || "（空）"],
    ["条目类型", record.context.kind || "（未知）"],
    ["既有读音修正", record.context.existing_reading_correction || "（无）"],
  ];
  for (const [term, description] of evidence) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = term;
    dd.textContent = description;
    elements.evidenceList.append(dt, dd);
  }
  showPdfPage(record.pdf_page, record.page);
  renderList();
}

function renderTreatment(disposition, status = "pending") {
  const needsNote = status !== "rejected" && disposition !== NORMAL_DISPOSITION && disposition !== "mismatch";
  elements.acceptButton.textContent = needsNote ? "记录处理方式并下一条" : "确认并下一条";
  elements.decisionNote.required = needsNote;
  elements.treatmentHelp.textContent = needsNote
    ? "非正常匹配不会被当作普通读音／释义修正自动回写，必须填写补充说明。"
    : "拒绝规则无需补充说明；确认时可按原书自行编辑最终值。";
}

function updateChoiceUI(field, choice) {
  document.querySelectorAll(`[data-field="${field}"]`).forEach((button) => {
    button.classList.toggle("is-selected", button.dataset.choice === choice);
  });
  el(`${field}-choice-label`).textContent = choice === "proposal" ? "采用人工提案" : choice === "current" ? "保留当前值" : "已自订／未选择";
}

function chooseField(field, choice) {
  const record = currentRecord();
  const decision = currentDecision(record);
  if (isSplitRecord(record)) return;
  decision.choices[field] = choice;
  decision.final[field] = record[choice][field] || "";
  el(`${field}-final`).value = decision.final[field];
  decision.status = "pending";
  decision.updated_at = new Date().toISOString();
  updateChoiceUI(field, choice);
  saveDecisions();
  renderList();
  updateSummary();
}

function syncFormToDecision() {
  const decision = currentDecision();
  if (!decision) return;
  const record = currentRecord();
  if (!isSplitRecord(record)) {
    decision.final.reading = elements.readingFinal.value;
    decision.final.gloss = elements.glossFinal.value;
  }
  decision.note = elements.decisionNote.value;
  decision.disposition = elements.matchDisposition.value;
  if (!isSplitRecord(record)) {
    for (const field of ["reading", "gloss"]) {
      const value = decision.final[field];
      decision.choices[field] = value === record.current[field] ? "current" : value === record.proposal[field] ? "proposal" : "custom";
      updateChoiceUI(field, decision.choices[field]);
    }
  }
  decision.status = "pending";
  decision.updated_at = new Date().toISOString();
  saveDecisions();
  renderList();
  updateSummary();
  renderTreatment(decision.disposition, decision.status);
}

function setStatus(status, advance = false) {
  const decision = currentDecision();
  if (!decision) return;
  const record = currentRecord();
  syncFormToDecision();
  if (record && !validateSplitRows(record, decision)) {
    elements.splitAdd.focus();
    return;
  }
  if (
    status === "accepted"
    && ![NORMAL_DISPOSITION, "mismatch"].includes(decision.disposition)
    && !decision.note.trim()
  ) {
    showError("非正常匹配请填写补充说明，让 AI 理解应如何处理");
    elements.decisionNote.focus();
    return;
  }
  clearError();
  decision.status = status;
  decision.updated_at = new Date().toISOString();
  saveDecisions();
  if (advance) navigateRecord(1, true);
  else renderList();
  updateSummary();
}

function navigateRecord(delta, preferPending = false) {
  if (!state.filtered.length) return;
  let index = state.filtered.findIndex((record) => record.id === state.activeId);
  for (let attempt = 0; attempt < state.filtered.length; attempt += 1) {
    index = (index + delta + state.filtered.length) % state.filtered.length;
    if (!preferPending || statusOf(state.filtered[index]) === "pending") break;
  }
  state.activeId = state.filtered[index].id;
  renderRecord();
  document.querySelector(`[data-record-id="${state.activeId}"]`)?.scrollIntoView({ block: "nearest" });
}

function updateSummary() {
  const counts = { pending: 0, accepted: 0, rejected: 0, deferred: 0 };
  state.dataset.records.forEach((record) => { counts[statusOf(record)] += 1; });
  elements.datasetSummary.textContent = `${state.dataset.record_count} 个词条 · ${state.dataset.issue_count} 个问题 · 已确认 ${counts.accepted} · 已拒绝 ${counts.rejected} · 稍后 ${counts.deferred} · 未决定 ${counts.pending}`;
}

function showPdfPage(pdfPage, dictionaryPage = null) {
  state.shownPdfPage = Math.max(1, Math.min(state.pdfPages, pdfPage));
  elements.pageInput.value = String(state.shownPdfPage);
  elements.pageInput.max = String(state.pdfPages);
  elements.sourceLoading.hidden = false;
  elements.sourceLoading.textContent = "载入原书页…";
  elements.sourceImage.onload = () => {
    elements.sourceLoading.hidden = true;
    fitWidth();
  };
  elements.sourceImage.onerror = () => {
    elements.sourceLoading.hidden = false;
    elements.sourceLoading.textContent = "原书页载入失败，右侧仍可继续校订";
  };
  elements.sourceImage.src = `/api/page/${state.shownPdfPage}.jpg`;
  const mappedDictionaryPage = dictionaryPage ?? state.shownPdfPage - state.pageOffset;
  elements.pageLabel.textContent = `原书第 ${mappedDictionaryPage} 页 / PDF ${state.shownPdfPage}`;
}

function applyViewerTransform() {
  const viewer = state.viewer;
  elements.sourceStage.style.transform = `translate(${viewer.x}px, ${viewer.y}px) scale(${viewer.scale})`;
  elements.zoomValue.textContent = `${Math.round(viewer.scale * 100)}%`;
}

function fitWidth() {
  if (!elements.sourceImage.naturalWidth) return;
  const rect = elements.sourceViewer.getBoundingClientRect();
  state.viewer.scale = Math.min(3, (rect.width - 28) / elements.sourceImage.naturalWidth);
  state.viewer.x = (rect.width - elements.sourceImage.naturalWidth * state.viewer.scale) / 2;
  state.viewer.y = 14;
  applyViewerTransform();
}

function zoomAt(factor, clientX, clientY) {
  const rect = elements.sourceViewer.getBoundingClientRect();
  const oldScale = state.viewer.scale;
  const newScale = Math.max(.2, Math.min(5, oldScale * factor));
  const px = clientX - rect.left;
  const py = clientY - rect.top;
  const imageX = (px - state.viewer.x) / oldScale;
  const imageY = (py - state.viewer.y) / oldScale;
  state.viewer.scale = newScale;
  state.viewer.x = px - imageX * newScale;
  state.viewer.y = py - imageY * newScale;
  applyViewerTransform();
}

function decisionPayload() {
  const decisions = state.dataset.records
    .filter((record) => REVIEWABLE_STATUSES.includes(statusOf(record)))
    .map((record) => ({
      id: record.id,
      source_digest: record.source_digest,
      status: state.decisions[record.id].status,
      final: state.decisions[record.id].final,
      note: state.decisions[record.id].note || "",
      disposition: state.decisions[record.id].disposition || NORMAL_DISPOSITION,
      updated_at: state.decisions[record.id].updated_at,
    }));
  return { schema: DECISION_SCHEMA, data_version: state.dataset.data_version, exported_at: new Date().toISOString(), decisions };
}

function exportDecisions() {
  clearError();
  const payload = decisionPayload();
  const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `007-proofread-decisions-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function saveToServer() {
  clearError();
  const response = await fetch("/api/decisions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(decisionPayload()),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  elements.saveState.textContent = `已保存 ${result.saved} 条决定到服务`;
}

async function importDecisions(file) {
  const payload = JSON.parse(await file.text());
  if (payload.schema !== DECISION_SCHEMA) throw new Error("不支援的决定档格式");
  const compatibleVersions = new Set([state.dataset.data_version, ...(state.dataset.compatible_data_versions || [])]);
  if (!compatibleVersions.has(payload.data_version)) throw new Error("决定档对应的资料版本已经过期");
  const records = new Map(state.dataset.records.map((record) => [record.id, record]));
  for (const decision of payload.decisions || []) {
    const record = records.get(decision.id);
    if (!record || record.source_digest !== decision.source_digest) throw new Error(`词条 ${decision.id} 的原值摘要不符`);
    if (!REVIEWABLE_STATUSES.includes(decision.status)) throw new Error(`词条 ${decision.id} 的状态无效`);
    state.decisions[decision.id] = migrateLegacyTreatment({
      disposition: NORMAL_DISPOSITION,
      ...decision,
      choices: { reading: "custom", gloss: "custom" },
    });
  }
  saveDecisions();
  applyFilters();
  updateSummary();
}

function isEditableTarget(target) {
  return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement || target?.isContentEditable;
}

function keepCurrentValues() {
  const record = currentRecord();
  if (!record) return;
  if (isSplitRecord(record)) {
    const decision = currentDecision(record);
    decision.final.reading = record.current.reading;
    decision.final.gloss = record.current.gloss;
    decision.choices = { reading: "current", gloss: "current" };
    decision.status = "pending";
    decision.updated_at = new Date().toISOString();
    saveDecisions();
    renderRecord();
    updateSummary();
    return;
  }
  chooseField("reading", "current");
  chooseField("gloss", "current");
}

function bindEvents() {
  elements.statusFilter.addEventListener("change", applyFilters);
  elements.ruleTypeFilter.addEventListener("change", applyFilters);
  elements.searchInput.addEventListener("input", applyFilters);
  elements.recordList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-record-id]");
    if (!button) return;
    state.activeId = button.dataset.recordId;
    renderRecord();
  });
  elements.reviewForm.addEventListener("click", (event) => {
    const button = event.target.closest("[data-field][data-choice]");
    if (button) chooseField(button.dataset.field, button.dataset.choice);
  });
  for (const control of [elements.readingFinal, elements.glossFinal, elements.decisionNote]) control.addEventListener("input", syncFormToDecision);
  elements.matchDisposition.addEventListener("change", syncFormToDecision);
  elements.reviewForm.addEventListener("submit", (event) => { event.preventDefault(); setStatus("accepted", true); });
  elements.deferButton.addEventListener("click", () => setStatus("deferred", true));
  elements.rejectButton.addEventListener("click", () => setStatus("rejected", true));
  elements.keepButton.addEventListener("click", keepCurrentValues);
  elements.recordPrevious.addEventListener("click", () => navigateRecord(-1));
  elements.recordNext.addEventListener("click", () => navigateRecord(1));
  elements.exportButton.addEventListener("click", exportDecisions);
  elements.saveButton.addEventListener("click", async () => {
    try { await saveToServer(); }
    catch (error) { showError(`保存失败：${error.message}`); }
  });
  elements.importButton.addEventListener("click", () => elements.importFile.click());
  elements.importFile.addEventListener("change", async () => {
    try { if (elements.importFile.files[0]) await importDecisions(elements.importFile.files[0]); clearError(); }
    catch (error) { showError(`导入失败：${error.message}`); }
    elements.importFile.value = "";
  });

  elements.splitRows.addEventListener("input", (event) => {
    if (!event.target.closest(".split-row")) return;
    const decision = currentDecision();
    if (!decision) return;
    commitSplitRows(decision);
    saveDecisions();
    renderList();
    updateSummary();
  });
  elements.splitRows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const decision = currentDecision();
    if (!decision) return;
    const index = Number(button.closest(".split-row").dataset.rowIndex);
    let rows = collectSplitRows();
    if (button.dataset.action === "remove") {
      if (rows.length <= 1) return;
      rows.splice(index, 1);
    } else if (button.dataset.action === "move") {
      const target = button.dataset.direction === "up" ? index - 1 : index + 1;
      if (target < 0 || target >= rows.length) return;
      [rows[index], rows[target]] = [rows[target], rows[index]];
    } else {
      return;
    }
    decision.final.reading = rows.map((row) => row.reading).join("\n");
    decision.final.gloss = rows.map((row) => row.gloss).join("\n");
    decision.status = "pending";
    decision.updated_at = new Date().toISOString();
    saveDecisions();
    renderSplitEditor(currentRecord(), decision);
    renderList();
    updateSummary();
  });
  elements.splitAdd.addEventListener("click", () => {
    const decision = currentDecision();
    if (!decision) return;
    const rows = collectSplitRows();
    rows.push({ reading: "", gloss: "" });
    decision.final.reading = rows.map((row) => row.reading).join("\n");
    decision.final.gloss = rows.map((row) => row.gloss).join("\n");
    decision.status = "pending";
    decision.updated_at = new Date().toISOString();
    saveDecisions();
    renderSplitEditor(currentRecord(), decision);
    renderList();
    updateSummary();
    const lastRow = elements.splitRows.querySelector(".split-row:last-of-type");
    lastRow?.querySelector('input[data-slot="reading"]')?.focus();
  });

  elements.pageInput.addEventListener("change", () => {
    const value = Number(elements.pageInput.value);
    if (Number.isInteger(value) && value >= 1) showPdfPage(value);
  });

  elements.sourceViewer.addEventListener("wheel", (event) => {
    event.preventDefault();
    zoomAt(Math.exp(-event.deltaY * .0015), event.clientX, event.clientY);
  }, { passive: false });
  elements.sourceViewer.addEventListener("pointerdown", (event) => {
    state.viewer.dragging = true;
    state.viewer.pointerId = event.pointerId;
    state.viewer.lastX = event.clientX;
    state.viewer.lastY = event.clientY;
    elements.sourceViewer.setPointerCapture(event.pointerId);
    elements.sourceViewer.classList.add("is-dragging");
  });
  elements.sourceViewer.addEventListener("pointermove", (event) => {
    if (!state.viewer.dragging || event.pointerId !== state.viewer.pointerId) return;
    state.viewer.x += event.clientX - state.viewer.lastX;
    state.viewer.y += event.clientY - state.viewer.lastY;
    state.viewer.lastX = event.clientX;
    state.viewer.lastY = event.clientY;
    applyViewerTransform();
  });
  const endDrag = () => { state.viewer.dragging = false; state.viewer.pointerId = null; elements.sourceViewer.classList.remove("is-dragging"); };
  elements.sourceViewer.addEventListener("pointerup", endDrag);
  elements.sourceViewer.addEventListener("pointercancel", endDrag);
  elements.sourceViewer.addEventListener("dblclick", fitWidth);
  elements.zoomIn.addEventListener("click", () => { const rect = elements.sourceViewer.getBoundingClientRect(); zoomAt(1.2, rect.left + rect.width / 2, rect.top + rect.height / 2); });
  elements.zoomOut.addEventListener("click", () => { const rect = elements.sourceViewer.getBoundingClientRect(); zoomAt(1 / 1.2, rect.left + rect.width / 2, rect.top + rect.height / 2); });
  elements.zoomValue.addEventListener("click", fitWidth);
  elements.fitWidth.addEventListener("click", fitWidth);
  elements.pagePrevious.addEventListener("click", () => showPdfPage(state.shownPdfPage - 1));
  elements.pageNext.addEventListener("click", () => showPdfPage(state.shownPdfPage + 1));
  window.addEventListener("resize", fitWidth);
  window.addEventListener("keydown", (event) => {
    if (isEditableTarget(event.target)) return;
    if (event.key === "1") { chooseField("reading", "proposal"); chooseField("gloss", "proposal"); }
    else if (event.key === "2") { chooseField("reading", "current"); chooseField("gloss", "current"); }
    else if (event.key.toLowerCase() === "e") elements.readingFinal.focus();
    else if (event.key === "Enter") setStatus("accepted", true);
  });
}

async function init() {
  Object.assign(elements, {
    errorBanner: el("error-banner"), datasetSummary: el("dataset-summary"), saveState: el("save-state"), importButton: el("import-button"), saveButton: el("save-button"), exportButton: el("export-button"), importFile: el("import-file"),
    statusFilter: el("status-filter"), ruleTypeFilter: el("rule-type-filter"), searchInput: el("search-input"), listSummary: el("list-summary"), recordList: el("record-list"),
    sourceViewer: el("source-viewer"), sourceStage: el("source-stage"), sourceImage: el("source-image"), sourceLoading: el("source-loading"), pageLabel: el("page-label"), pageInput: el("page-input"), pagePrevious: el("page-previous"), pageNext: el("page-next"), zoomIn: el("zoom-in"), zoomOut: el("zoom-out"), zoomValue: el("zoom-value"), fitWidth: el("fit-width"),
    reviewForm: el("review-form"), recordPosition: el("record-position"), recordTitle: el("record-title"), issueTags: el("issue-tags"), recordPrevious: el("record-previous"), recordNext: el("record-next"),
    readingFinal: el("reading-final"), glossFinal: el("gloss-final"), decisionNote: el("decision-note"), evidenceList: el("evidence-list"), deferButton: el("defer-button"), rejectButton: el("reject-button"), keepButton: el("keep-button"), acceptButton: el("accept-button"),
    matchDisposition: el("match-disposition"), ruleKeyList: el("rule-key-list"), ruleTypeBadge: el("rule-type-badge"), splitEditor: el("split-editor"), splitRows: el("split-rows"), splitAdd: el("split-add"),
    fieldReading: el("field-reading"), fieldGloss: el("field-gloss"), treatmentHelp: el("treatment-help"),
  });
  bindEvents();
  try {
    const healthResponse = await fetch("/api/health", { cache: "no-store" });
    const dataResponse = await fetch("/api/data", { cache: "no-store" });
    if (!healthResponse.ok) throw new Error(`HTTP ${healthResponse.status}`);
    if (!dataResponse.ok) throw new Error(`HTTP ${dataResponse.status}`);
    const health = await healthResponse.json();
    state.pdfPages = health.pdf_pages || 648;
    state.pageOffset = health.page_offset || 0;
    state.dataset = await dataResponse.json();
    loadDecisions();
    state.filtered = [...state.dataset.records];
    state.activeId = state.filtered.find((record) => statusOf(record) === "pending")?.id || state.filtered[0]?.id || null;
    updateSummary();
    renderList();
    renderRecord();
    elements.saveState.textContent = "浏览器自动暂存已启用";
  } catch (error) {
    showError(`无法载入审校资料：${error.message}`);
  }
}

document.addEventListener("DOMContentLoaded", init);
