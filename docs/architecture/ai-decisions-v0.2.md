# AI Decisions v0.2 — quyết định thực thi cho Regime + Scenarios

**Status:** ADOPTED FOR IMPLEMENTATION — mọi run sinh ra dưới quyết định này đều là
`NON_BASELINE_RUN` cho tới khi owner tương ứng ở §3 phê duyệt.

**Owner:** Nguyễn Anh Tú (AI/ML). **Supersedes:** một phần `ai-scope-decision-record-v0.1.md`.

## 1. Vì sao có v0.2

Proposal v0.1 viết tại commit `05d787e`. Từ đó `main` đã đổi: `Config`, `ArtifactPaths`,
`RunContext`, `validate_or_raise` và toàn bộ `schemas/*` đã hiện thực; `configs/universe.yaml`
và `configs/data.yaml` đã điền; `returns.parquet` + `market_features.parquet` đã có dữ liệu
thật. Quan trọng nhất: `schemas/features.py` — nơi Feature Contract v0.1 từng sống — nay là
`MarketFeaturesSchema` của Tân. Contract v0.1 không còn chỗ đứng trong repo.

## 2. Quyết định

| ID | Quyết định | Thay thế gì trong DR v0.1 |
|---|---|---|
| AD-01 | Feature HMM = 4 cột `market_features.parquet` (`market_log_return`, `realized_vol_20d`, `drawdown`, `liquidity_20d`) + `mean_pairwise_corr_60d` do AI tính từ `returns.parquet` | Rút Feature Contract v0.1 và DR §4. DR-R-03 trở nên vô nghĩa |
| AD-02 | Transform: `log` cho volatility, Fisher-z cho correlation; `StandardScaler` fit CHỈ trên train | Mới |
| AD-03 | Lưới `n_states ∈ {2,3,4,5} × covariance ∈ {diag, full} × 10 seed` được BÁO CÁO; champion ghim ở `3/diag` | Dung hòa PR-REG-002 với phạm vi khóa. `RegimeDailySchema` chặn `state_id` ở `{0,1,2}` nên >3 state không thể là champion |
| AD-04 | Champion seed = medoid theo mức đồng thuận nhãn; tie-break val log-likelihood rồi seed nhỏ nhất | Cụ thể hóa DR §6 |
| AD-05 | Nhãn gán theo `z(vol) − z(return) + z(abs(drawdown))`, kèm cổng nhất quán kinh tế | Cụ thể hóa DR §gán nhãn theo thống kê |
| AD-06 | `regime_daily.parquet` = 8 cột hợp đồng (giá trị filtered/nhân quả) + cột chẩn đoán đặt tên riêng. Ngày warm-up KHÔNG có dòng | Giải DR-R-04 mà không sửa schema của Tân: `strict=False` cho phép cột thừa, null thì không |
| AD-07 | Fallback rule-based ghi `regime_daily_rule_based.parquet` riêng, KHÔNG có cột xác suất, và chặn scenarios | Giải DR-R-04 phía fallback |
| AD-08 | Cube chứa CẢ hai: `scenarios` (simple, primary) và `scenarios_log`; manifest ghi `return_type: simple` | Thay đề xuất log-only của DR-R-06 |
| AD-09 | `t` = `configs/scenarios.yaml: evaluation_date`; `null` ⇒ ngày cuối có nhãn regime và đủ N mã | Giải DR-R-05 |
| AD-10 | Anchor pool = mọi ngày ≤ t có nhãn filtered hợp lệ (train+val+test); manifest ghi thành phần split và tỷ lệ tái sử dụng | Cụ thể hóa DR §Block eligibility + SCN-OD-02 |
| AD-11 | Lịch giao dịch chuẩn = ngày trong `market_features.parquet`; block = 5 vị trí LIỀN NHAU trên lịch đó, đủ N mã. 12 ngày thiếu mã bị loại như absent asset | Giải SCN-OD-07 |
| AD-12 | Một cube bàn giao (theo `filtered_label(t)`) + ba cube theo regime làm bằng chứng validation | Giải IN-RISK-06 |
| AD-13 | Ngưỡng validation PROVISIONAL nằm trong config; mỗi metric có verdict PASS/WARN/FAIL | Giải IN-RISK-03 tạm thời |
| AD-14 | `S = 500` (phạm vi khóa), code generic `(S,H,N)` | Hạ DR §1 xuống đề xuất mở, đúng DR-R-01 |
| AD-15 | CVAE không hiện thực | Theo Đóng băng phạm vi của CLAUDE.md |
| AD-16 | Tương quan 60 phiên tính trên panel ĐỦ N mã (2571 ngày thay vì 2401) | Mới. Khác luật block: tương quan là thống kê tổng hợp point-in-time, không phải một đường đi |

## 3. Ai còn phải phê duyệt

| Quyết định | Owner | Trạng thái |
|---|---|---|
| AD-14 (`S`), AD-07 (tư cách bằng chứng của fallback) | Ngọc | Chờ (IN-PO-01, IN-PO-02) |
| AD-08 (đơn vị return), AD-09 (`t`), AD-13 (ngưỡng gate) | Phúc | Chờ (IN-RISK-01/02/03) |
| AD-06 (cột thừa trong `regime_daily.parquet`) | Tân | Chờ (IN-CTR-01) |
| Giá trị đã điền vào `configs/*.yaml` | Ngọc | Chờ (IN-PO-04) |

Owner chốt khác default ⇒ sinh **run ID mới** cho scenario/risk/optimization, không sửa số run cũ.
