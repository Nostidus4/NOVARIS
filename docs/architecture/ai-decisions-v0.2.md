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

---

## 4. Kết quả run tham chiếu (NON_BASELINE_RUN)

Chạy trên dữ liệu thật, `configs/base.yaml`, `artifacts.mode: dev`, ngày 2026-08-04. Số dưới đây
KHÔNG được dùng làm bằng chứng cuối/UAT/slide cho tới khi các owner ở §3 phê duyệt.

### Regime — cổng ĐẠT

| Chỉ số | Giá trị |
|---|---|
| Số dòng `regime_daily.parquet` | 2571 (2016-04-04 → 2026-07-30) |
| Champion | seed 303, 3 state, `diag`, converged=true |
| Log-likelihood train / validation | −7650.6476 / −1668.1255 |
| AIC / BIC | 15377.2951 / 15583.5492 (38 tham số) |
| Đồng thuận nhãn giữa seed (mean/min/max) | 0.8093 / 0.5495 / 1.0000 trên 10 seed hợp lệ |
| Occupancy normal/volatile/stress | 0.2369 / 0.3399 / 0.4232 |
| Độ dài trung bình mỗi lượt (phiên) | 203.00 / 109.25 / 98.91 |
| Cổng | **OK** |

Đồng thuận trung bình 0.8093 vượt xa ngưỡng PROVISIONAL `min_mean_label_agreement = 0.60`
(ngẫu nhiên với 3 nhãn ≈ 0.33). Cả 10 seed đăng ký đều hợp lệ.

### Scenarios — cổng KHÔNG ĐẠT

| Chỉ số | Giá trị |
|---|---|
| Ngày đánh giá `t` | 2026-07-30 |
| Regime mục tiêu tại `t` | `volatile` |
| Nguồn nhãn | `hmm_champion`, `conditioning_method = hard_filtered_label` |
| Số block hợp lệ | 864 |
| Block bị loại | `beyond_evaluation_date` 5, `incomplete_panel` 5, `anchor_off_calendar` 0 |
| Tỷ lệ tái sử dụng block | 0.6175 (765 block khác nhau trên 2000 lượt rút) |
| Thành phần split của anchor | train 284 / validation 85 / test 495 |
| Khoảng anchor | 2020-10-23 → 2026-07-23 |
| Shape cube | (500, 20, 8) |
| Cổng validation | **FAIL** |
| Metric FAIL | `kurtosis_abs_diff` = 16.2451 (ngưỡng 5.0), regime `volatile` |

`stress_scenarios.npz` **không được ghi** — đúng thiết kế. `scenarios_by_regime.npz`,
`scenario_validation.csv`, `scenario_manifest.json` vẫn được ghi để bằng chứng của lần fail này
không mất đi.

### Ghi chú trung thực

**1. Cổng scenario FAIL trên dữ liệu thật.** Regime `volatile` — chính là regime tại `t` — trượt
`kurtosis_abs_diff` ở 16.2451 so với ngưỡng 5.0. Tám metric còn lại đều PASS
(`mean_abs_diff` 0.000016, `std_ratio` 0.9640, `skew_abs_diff` 0.6825, `q05/q95_rel_error`
0.0484/0.0477, `autocorr_abs_diff` 0.0168, `corr_mean_abs_diff` 0.0585,
`tail_coverage_ratio` 0.9897). Hai regime còn lại PASS toàn bộ 9/9.

**Đây KHÔNG phải lỗi mẫu mỏng:** tập tham chiếu có 834 cửa sổ cho `volatile` (569 cho `normal`,
1068 cho `stress`), `small_sample = False` ở cả ba. Vi phạm đứng trên bằng chứng đầy đủ.

Cách đọc: moving-block bootstrap ghép các block 5 phiên rời rạc, nên đuôi phân phối 20 ngày do nó
sinh ra nặng hơn hẳn đuôi của cửa sổ 20 ngày liên tục có thật. Kurtosis là metric nhạy nhất với
đúng hiệu ứng này. Chưa kết luận được là **ngưỡng 5.0 quá chặt** hay **engine sinh đuôi sai** —
đó là quyết định của Phúc (IN-RISK-03), người sở hữu Scenario Validation Gate. Ngưỡng do AI đề
xuất, chưa ai ký. **Không tự nới ngưỡng để lấy màu xanh.**

**2. Battery kiểm định là IN-SAMPLE theo cấu tạo (SCN-OD-04):** `reference_windows`
(`packages/ai/src/qshield_ai/scenarios/validate.py`) lấy cửa sổ tham chiếu từ chính
`pool.block_starts` — đúng tập anchor mà bootstrap resample — nên các con số 8/9 và 9/9 ở trên chỉ
đo việc resampling có bóp méo phân phối của chính tập anchor đó hay không, KHÔNG phải bằng chứng
out-of-sample và không thể phát hiện over-fitting *vào* tập anchor.

**3. Không có bất thường nào khác.** Cả 10 seed hội tụ và hợp lệ; không regime nào bị bỏ qua vì
khan hiếm block; chỉ 10/874 block bị loại (5 vượt `t`, 5 thiếu mã).

**4. Toàn bộ run mang nhãn `NON_BASELINE_RUN`** với danh sách decision ID chưa phê duyệt ở §3.
