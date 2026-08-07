# Data audit — 30 mã VN30 (2026-08-07)

Sau Decision-package và cập nhật universe của Minh Anh.

## Đã xác nhận trên đĩa

| Artifact | Trạng thái |
|---|---|
| `configs/universe.yaml` | `expected_ticker_count: 30`, đủ 30 ticker |
| `data/processed/prices_adjusted.parquet` | **30** tickers |
| `data/processed/returns.parquet` | **30** tickers |
| `data/processed/eligibility_daily.parquet` | **30** tickers |
| `data/metadata/universe_asof_20260803.csv` | 30 rows |
| `data/metadata/universe_30_asof_20260803.csv` | đã tạo (alias TL-001) |

## Đã sửa trong phiên này

1. `sample_portfolio_weights` → equal-weight **30 mã** (+ `sample_portfolio_cash_weight: 0`).
2. `configs/data.yaml` → `asset_train_start: 2016-01-01` (TL-003).
3. Registry ghi thêm `universe_30_asof_{date}.csv`.
4. Thêm `reports/adjusted_close_evidence_report.csv` (TL-002) — hiện:
   - 23 `ADJ_VENDOR` (Yahoo)
   - 6 `ADJ_UNVERIFIED` (DNSE assume Close≈Adj)
   - 1 `ADJ_REGISTERED` (VCB)
   - **`baseline_ok=False` toàn bộ** tới khi Data Gate ký

## Vẫn chưa đủ để gọi Data Gate PASS / BASELINE

- `ticker_list_status` vẫn TBD_001 (chưa phải Universe Registry owner-approved).
- Adjusted-close evidence chưa có cross-check owner cho từng mã (TL-002).
- VPL vẫn ghi chú cold-start / placeholder verify.
- Scenario config mặc định vẫn `num_scenarios: 500` (AI pha sau sẽ đổi profile-driven 2000).

## Notebook để bạn chạy lại Data (có timing)

`notebooks/exploration/01_data_workflow_update.ipynb` — gọi subprocess từng bước, in elapsed.
