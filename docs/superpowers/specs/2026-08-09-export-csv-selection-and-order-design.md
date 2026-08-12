# CSV 導出選擇與順序設計

## 目標

讓 `scripts/export_csv.py` 可選擇保留處理器輸出的來源順序，並可只導出指定書籍，同時保持既有無參數行為相容。

## 命令介面

- `--preserve-order`：不按讀音排序，依 processor 回傳順序寫入 CSV。未指定時維持現有 `puj/poj` 排序。
- `--book STEM`：只處理 `books/STEM.md`；參數可重複，以一次選擇多本書。
- 未指定 `--book`：維持現行行為，處理 `books`、`clippings`、`lyrics` 中所有具有 processor 的來源。

## 錯誤處理

指定的書籍不存在或沒有對應 processor 時，以非零狀態結束並顯示具體書名。不得靜默跳過使用者明確指定的書籍。

## 驗證

測試應證明：預設模式仍排序、`--preserve-order` 保留輸入順序、單本及多本選擇正確、未知書籍及缺少 processor 時失敗。
