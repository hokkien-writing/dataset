# Page Marker Matching Redesign

Date: 2026-06-06

## Problem

`scripts/add_page_markers.py` 對 book 001（Handbook of the Swatow Vernacular）產生的 page marker 大量錯位。根因是 cumul-based matching 假設 WS 與 MD 按相同順序排列且條目數對等，但實際：

- **WS pages 按字母順序**（Abandon, Accumulate, ..., Chapel, Church, ..., Relationships, ...）
- **MD 按課/主題**（Lesson I, II, ..., XXIV, Relationships, ..., Vocabulary A-Z）

兩個維度的條目數量級不對等，cumul 從 page 1 累積漂移到 page 162 已相差數千條條目。

### 具體例子（page 162）

WS 顯示 page 162 內容包含 `Church, building, R. C.`, `Cross`, ..., `Censor, a,`（19 條），但搜尋窗口被 cumul 漂移到 MD 的錯誤區段，找不到匹配。fallback 機制把 marker 放到 `Church, members` 之前（line 3311），而非 `Church, building, Roman Catholics` 之前（line 3315）。

對 user 來說這造成：點 `Church, members` 跳到「page 162」，但實際印刷的 page 162 第一個 entry 應該是 `Church, building, R. C.`。

### 為什麼 page 138 之前能修對

page 138 修復是 manual/cumulative 計算，沒有自動驗證：cumul 漂移小於窗口大小時隨機匹配對了。漂移大於窗口時（如 page 162 漂移數千條）就完全失敗。

## Goals

1. **正確性優先**：每個 page 的 marker 必須對應到 WS 上該 page 的第一個 entry
2. **保守**：算法不確定時**保留現有 marker**，不亂改
3. **冪等**：重跑結果一致
4. **可驗證**：失敗時輸出診斷資訊（哪個 page 為什麼沒匹配）
5. **最小侵入**：只改 `add_page_markers.py` 的 matching 邏輯，不動 WS 抓取、MD 解析、insert 邏輯

## Non-Goals

- book 002（English-Chinese Vocabulary）暫不處理 — 結構差異大（`source_type: index`），等 book 001 驗證後再 port
- 不重寫整個 `add_page_markers.py` — 只替換 `build_markers_with_components` 和 `build_markers_anchored` 兩個函數

## Input Contract

現有 `extract_page_entries(cache, config) -> dict[int, list[tuple[han, puj, en]]]` 已經正確：

- 對 book 001 (subpages)：每個 page 的 entries 從 WS 對應 subpage 的 `data-page-index="N"` 之後提取
- 對 book 002 (index)：每個 page 的 entries 從 `Page:.../N` 頁面提取

驗證過：page 162 的 `entries[0] = ('Church, building, R. C.', 'Sèng-tn̂g', '聖堂')` 是正確的。

現有 `find_md_entries(lines, md_entry_re, source_type) -> list[(line_idx, han_orig, han_corr, puj, en)]` 也正確。

問題只在「如何用這兩個 input 算 marker 位置」。

## Algorithm

### 單 page 匹配（page P，前一個 page P-1 結束於 `prev_end`）

```
search_lo = prev_end + 1
search_hi = min(len(md_entries), prev_end + max_window_size)  # max_window_size = 300
```

1. **First entry 搜尋**：在 `[search_lo, search_hi)` 範圍內，找 `entries[0]` 的最佳 MD 匹配位置 `first_pos`（用 `entry_score`，取最低分且 `s_han < 99`）

2. **Last entry 搜尋**：在 `[first_pos + 1, first_pos + len(entries) + 5)` 範圍內，找 `entries[-1]` 的最佳匹配位置 `last_pos`（同樣 `s_han < 99`）

3. **距離驗證**：
   - `expected_dist = len(entries) - 1`
   - `actual_dist = last_pos - first_pos`
   - **通過**：`actual_dist ∈ [expected_dist - 2, expected_dist + 5]`

4. **Middle 驗證**：
   - 在 `[first_pos, last_pos]` 範圍內，逐個比對 `entries[1:-1]` 與 `md_entries[first_pos+1:last_pos]`
   - 計算「正確匹配數 / 中間條目數」
   - **通過**：匹配率 ≥ 50%（容許 ditto 標記 `„` 和變體）

5. **結果**：
   - 三項驗證全通過 → marker 放在 `first_pos`，更新 `prev_end = first_pos + actual_dist + 1`
   - 任何一項失敗 → **保留現有 marker 位置不變**（不改），不更新 `prev_end`

### 第一個 page（page = first_entry_page）

- `prev_end = -1`（從 MD 開頭開始搜）
- `search_lo = 0`
- 其餘同上

### 空 page（無 entries）

- 沿用現有 front/back matter 邏輯（line 575-577 of current script）
- 跳過 entry matching

### max_window_size 設計

- book 001 WS 每個 page 平均 ~17 條 entries，但 MD 結構不同
- 取 300 是經驗值：足夠覆蓋一個 page 在 MD 中的最大可能長度（含 ditto 展開），又不會讓 search 過慢
- 276 pages × 300 entries = ~83K 次 `entry_score` 計算，可接受

## Scoring（沿用現有 `entry_score`）

`entry_score(ws_entry, md_entry) -> (s_han, s_puj, s_en)`：
- 越小越好
- `s_han < 99` 視為「可能匹配」
- 現有啟發式（exact=0, prefix=1, levenshtein ≤ threshold=2, else=99）保留

不重寫 scoring — 之前已驗證對 book 002 有效。

## Fallback 策略

**核心原則**：算法不確定時不亂動。

- 找不到 first entry 匹配 → 保留現有 marker
- 距離驗證失敗 → 保留現有 marker
- Middle 匹配率 < 50% → 保留現有 marker
- 保留現有 marker = 在 cleaned text 中以 `<!-- page:N -->` 形式存在的 marker（如果存在）

**首次運行**（MD 沒有 marker）時，所有 page 都會走算法結果。即使算法失敗，會用 `cumul = prev_end + 1` 作為最保守 fallback（保持單調遞增，不倒退）。

## Error Reporting

`--verbose` flag（新增）：每個 page 輸出
- `ANCHORED`: marker placed by algorithm
- `KEPT-EXISTING`: marker kept from existing MD
- `FALLBACK-CUMUL`: first run, cumul fallback used

範例輸出：
```
page 161: ANCHORED at line 3137 (md_idx 18) dist=17/17 mid=12/15
page 162: KEPT-EXISTING at line 3311 (verify failed: dist=18 vs expected 19)
page 163: ANCHORED at line 3174 (md_idx 38) dist=19/19 mid=14/15
```

## Architecture Changes

### 替換函數

`add_page_markers.py` 改動：

- 刪除 `build_markers_with_components`（line 487-524，cumul-based，已壞）
- 刪除 `build_markers_anchored`（line 183 in committed version，cumul-based，已壞）
- 新增 `build_markers_anchored_multi`：

```python
def build_markers_anchored_multi(
    page_entries: dict[int, list[tuple[str, str, str]]],
    md_entries: list[tuple[int, str, str, str, str]],
    existing_markers: dict[int, int] | None = None,  # page_num -> line_idx
    max_window: int = 300,
) -> list[tuple[int, int, str]]:  # (line_idx, page_num, status)
    """Multi-entry joint matching with cross-validation.
    
    Returns list of (line_idx, page_num, status) where status is one of:
    - "ANCHORED": algorithm placed marker here
    - "KEPT-EXISTING": marker kept from existing_markers
    - "FALLBACK-CUMUL": no existing marker, used cumul fallback
    """
```

### 保留的函數

- `extract_page_entries` — WS 提取，不動
- `find_md_entries` — MD 解析，不動
- `entry_score` — 評分，不動
- `parse_md_entry` — 條目解析，不動
- `insert_markers` — 插入邏輯，**需小幅修改**：接受 `(line_idx, pg, status)` 而非 `(line_idx, pg)`，status 寫入 `<!-- page:N -->` 後的 `<!-- status:... -->` 註解（如要 verbose 輸出可選）

### main() 改動

```python
# 改動 1：先讀取現有 markers
existing = {}
for i, line in enumerate(lines):
    m = re.match(r'<!-- page:(\d+) -->', line)
    if m:
        existing[int(m.group(1))] = i

# 改動 2：傳入 existing
markers = build_markers_anchored_multi(page_entries, md_entries, existing)

# 改動 3：診斷輸出
if args.verbose:
    for line_idx, pg, status in markers:
        if status != "ANCHORED":
            print(f"  page {pg}: {status} at line {line_idx}")
```

## Verification Plan

### 1. 寫 failing test 前

先在 `scripts/tests/test_page_markers.py` 寫 unit test：
- 構造 mock `page_entries` 和 `md_entries`
- 驗證 algorithm 在已知場景下行為正確

### 2. 跑 pilot（book 001 only）

```bash
# 第一次跑：使用現有 MD 作為 baseline
cp books/001_Handbook_of_the_Swatow_Vernacular.md /tmp/001_baseline.md
python3 scripts/add_page_markers.py --md books/001_Handbook_of_the_Swatow_Vernacular.md --verbose 2>&1 | tee /tmp/001_run.log

# Spot-check 5 個 page
for pg in 17 50 100 138 162 200 250 287; do
    echo "=== page $pg ==="
    grep -A 2 "page:$pg" books/001_Handbook_of_the_Swatow_Vernacular.md | head -4
done
```

預期：
- 5 個 page 的 marker 都在 WS 對應 first entry 之前
- 沒有 `KEPT-EXISTING`（因為算法應該都能匹配）

### 3. 冪等測試

```bash
md5sum books/001_Handbook_of_the_Swatow_Vernacular.md > /tmp/001_md5_1.txt
python3 scripts/add_page_markers.py --md books/001_Handbook_of_the_Swatow_Vernacular.md
md5sum books/001_Handbook_of_the_Swatow_Vernacular.md > /tmp/001_md5_2.txt
diff /tmp/001_md5_1.txt /tmp/001_md5_2.txt  # 應為空
```

### 4. 完整驗證（book 001 全 276 pages）

寫 verification script `scripts/verify_page_markers.py`：
- 對每個 page，提取 WS first entry
- 找到對應的 marker 位置
- 讀取 marker 之後的 MD entry
- 確認該 entry 的 `(han, puj, en)` 與 WS first entry 相似（`entry_score < (99, 99, 99)`）
- 輸出 pass/fail summary

## Risks

1. **max_window=300 太大**：可能跨 section 邊界搜尋，匹配到錯誤 entry
   - 緩解：先用 300 跑，觀察 spot-check 結果；若錯誤多，收緊到 100

2. **book 001 特殊情況**：某些 page 的 first entry 在 MD 中找不到匹配（例如空 page 或 WS 與 MD 結構不一致）
   - 緩解：KEPT-EXISTING fallback，至少不會比現在更差

3. **Middle 匹配率 50% 門檻太鬆/太嚴**：
   - 太鬆（< 30%）：可能誤通過驗證
   - 太嚴（> 70%）：可能拒絕正確匹配
   - 緩解：先設 50%，跑完看結果再調

4. **算法比 cumul 慢**：276 pages × 300 window × scoring = O(83K) operations
   - 緩解：scoring 函數 fast，總時間 < 1 分鐘

## Success Criteria

1. book 001 的 276 個 entry page marker 全部對應到 WS first entry 之前
2. Spot-check 5 個 page（含 138, 162, 163）視覺確認正確
3. 冪等：兩次跑結果 MD5 一致
4. 沒有 page 的 marker 倒退（page N+1 在 MD 中的位置必須 > page N）
5. `entry_score` 計算總數 < 100K（性能預算）

## Out of Scope (Future Work)

- book 002 適配（`source_type: index`）
- 自動偵測 WS vs MD section 對應（subpage 邊界 + MD `###` 標題）
- 視覺化 marker 驗證（HTML 報告）
- `add_page_markers.py` 重構（目前 600 行，耦合 WS fetch + MD parse + matching + insert）
