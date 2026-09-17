# Báo cáo cho nhóm trưởng — Scenario gate Volatile fail ở split test (hybrid v3)

Ngày: 2026-09-13 · Người điều tra: Claude Code (theo yêu cầu của Tân) · Trạng thái: **ĐÃ ĐÓNG 2026-09-17**

> **Kết cục.** Hướng sửa trong báo cáo này (registry back-adjust TCB ×2,0) **không** được dùng. Mạnh chuyển
> nguồn giá sang FiinPro; TCB/HDB/VCB đều hết bước nhảy giả mà không cần sửa tay. Ngày GDKHQ thật của TCB
> là **2024-06-20** (không phải 06-11). Registry `corporate_actions` đã gỡ; thí nghiệm chạy lại dưới
> `hybrid_qaoa_assisted_v4`. Xem `docs/data/2026-09-17-chuyen-nguon-gia-fiinpro.md`.

## 1. Tóm tắt 30 giây

- Confirmation hybrid v3 chỉ còn 20/30 instance hợp lệ vì **10/12 instance Volatile fail scenario gate**.
- Nguyên nhân gốc là **một ô dữ liệu**: TCB ngày 2024-06-11 có log return **−0,684 (−49,5%/phiên)** do
  **sự kiện thưởng cổ phiếu 1:1 chưa được điều chỉnh** trong dữ liệu Yahoo (cả `Close` lẫn `Adj Close`).
- Không phải lỗi thuật toán bootstrap, không phải lỗi code thí nghiệm.
- Áp đúng quy trình registry đã có (như VCB 2025-03-03) với hệ số 2,0 ⇒ **12/12 instance Volatile PASS**
  (đã kiểm chứng bằng chẩn đoán, chưa rebuild dữ liệu dùng chung).
- Đã sửa: thêm entry TCB vào `configs/base.yaml → corporate_actions` (có evidence, gắn
  `verification_status: PENDING_DATA_OWNER_...`). **Chưa** rebuild `data/processed` hay chạy lại pipeline.

## 2. Bằng chứng

### 2.1 Mẫu fail

| | Kết quả |
|---|---|
| Instance fail | 10 — **tất cả regime Volatile** (Normal 12/12 PASS, Stress 6/6 PASS) |
| Metric fail | 9/10 chỉ `kurtosis_abs_diff` (ngưỡng 5,0); c08 thêm `skew_abs_diff` |
| Ranh giới thời gian | c05 (as-of 2024-04-15) PASS → c08 (2024-06-14) và mọi ngày sau FAIL |

### 2.2 Ô dữ liệu gây lỗi

`data/processed/returns.parquet` và cả hai file raw `data/raw/prices/20260807_yfinance_tcb.csv`,
`20260814_yfinance_tcb.csv` (trùng nhau):

| date | Close | Adj Close | Volume |
|---|---|---|---|
| 2024-06-10 | 48.900 | 46.657,28 | 8.633.400 |
| **2024-06-11** | **24.675** | **23.543,32** | **33.173.800** |
| 2024-06-12 | 24.700 | 23.567,18 | 18.315.800 |

- Bước nhảy 1,9818 ở cả Close lẫn Adj Close ⇒ vendor không điều chỉnh.
- Giá giữ mức mới các phiên sau (không phải spike), volume ×3,8.
- Vượt biên độ HOSE ±7% — **DQ-007 đã bắt từ trước**: `reports/price_limit_violations_traced.csv`
  gắn `PERSISTS_LIKELY_CORP_ACTION`, nhưng chưa ai đăng ký vào `corporate_actions`.
- Nguồn công khai: Techcombank thưởng cổ phiếu tỷ lệ 1:1 (100%), tăng vốn điều lệ từ ~35.225 lên
  ~70.450 tỷ đồng, tháng 6/2024; giá đóng cửa 10/06/2024 là 48.900. *Các bài tóm tắt không thống nhất
  về ngày chốt quyền ⇒ Data owner phải đối chiếu thông báo HOSE/VSD để xác nhận ngày GDKHQ.*

### 2.3 Vì sao một ô làm fail cả gate

- Kurtosis gộp (30 mã × mọi ngày) cực kỳ nhạy với một điểm −68%: kurtosis kịch bản 118,3 vs tham chiếu
  36,4 (c08).
- Cửa sổ tham chiếu dài **20 ngày và chồng nhau** ⇒ ô ngoại lai bị đếm tối đa 20 lần; bootstrap chỉ lấy
  **block 5 ngày** ⇒ tần suất khác ⇒ chênh lệch kurtosis vượt ngưỡng 5,0 dù cả hai đều "đúng".

### 2.4 Kiểm chứng (script chẩn đoán, không đổi dữ liệu trên đĩa)

| Instance | kurtosis diff (dữ liệu hiện tại) | Gate | kurtosis diff (TCB điều chỉnh ×2,0) | Gate |
|---|---|---|---|---|
| c02 | 0,30 | PASS | 0,30 | PASS |
| c05 | 0,31 | PASS | 0,31 | PASS |
| c08 | **81,83** | FAIL | 0,30 | **PASS** |
| c11 | 5,45 | FAIL | 0,22 | **PASS** |
| c14 | 10,39 | FAIL | 0,47 | **PASS** |
| c17 | 9,39 | FAIL | 0,23 | **PASS** |
| c20 | 14,28 | FAIL | 0,62 | **PASS** |
| c22 | 27,94 | FAIL | 0,31 | **PASS** |
| c24 | 17,16 | FAIL | 0,13 | **PASS** |
| c26 | 6,56 | FAIL | 0,02 | **PASS** |
| c28 | 10,62 | FAIL | 0,03 | **PASS** |
| c30 | 8,40 | FAIL | 0,24 | **PASS** |

`apply_registered_adjustments` với entry mới cho return TCB 2024-06-11 = **+0,916%** (khớp chẩn đoán).

## 3. Phát hiện phụ cần Data owner xử lý (CHƯA sửa)

**HDB 2025-12-18/19:** +29,69% rồi −19,16% — vượt biên độ ±7% (DQ-007: `SPIKE_REVERSES_AMBIGUOUS`).
HDBank công bố cổ tức cổ phiếu 25% + thưởng 4,69% (tổng 29,69%), ngày GDKHQ 2025-12-18. Dữ liệu vendor:
giá lẻ (đã điều chỉnh) đến 12-17, giá chẵn (chưa điều chỉnh) từ 12-18, và 32.100/24.751,33 = **1,29690**
đúng bằng hệ số sự kiện ⇒ vendor **đặt điểm điều chỉnh lệch ngày**. Không thể sửa bằng registry
back-adjust (sẽ điều chỉnh hai lần các phiên trước). Cần Data owner đối chiếu DNSE/HOSE và quyết định
cách xử lý ô 2025-12-18 (gắn cờ, không xóa im lặng). Ô này **không** làm fail gate hiện tại.

## 4. Những gì đã thay đổi trong repo

| File | Thay đổi |
|---|---|
| `configs/base.yaml` | Thêm entry `corporate_actions` TCB 2024-06-11, `adjustment_factor: 2.0`, evidence, `verification_status: PENDING_DATA_OWNER_CONFIRM_EX_DATE_AGAINST_HOSE_NOTICE` |
| `docs/data/2026-09-13-scenario-gate-volatile-loi-tcb.md` | Báo cáo này |

Test sau thay đổi (không đổi code): data + config 71 passed; contracts, ai, risk, pipeline, backend xanh.
Artifact thí nghiệm v3 **giữ nguyên** (không ghi đè).

## 5. Tác động và rủi ro

- **Scenario/CVaR bị nhiễm**: mọi cube Volatile có anchor đủ gần 2024-06-11 chứa một "cú sập −49,5%" giả
  của TCB ⇒ CVaR phóng đại cho danh mục giữ TCB (vd archetype banking_concentrated). Trong hybrid v3 các
  instance này đã bị loại nhờ gate — gate làm đúng việc. Pipeline sản phẩm hiện tại (evaluation
  2026-07-30, anchor chỉ từ 2026-03) không chứa ô này, nhưng run sản phẩm dùng lịch sử dài hơn thì có.
- **Rebuild dữ liệu kéo theo toàn pipeline**: `returns.parquet` đổi ⇒ feature/regime HMM có thể đổi ⇒
  manifest instance có thể đổi ⇒ **mọi kết quả sau rebuild là experiment mới** (không trộn với v3).

## 6. Đề xuất và owner

| # | Việc | Owner | Ghi chú |
|---|---|---|---|
| 1 | Xác nhận ngày GDKHQ TCB theo thông báo HOSE/VSD, đổi `verification_status` sang CONFIRMED | Minh Anh (Data) | Nếu ngày khác 2024-06-11 ⇒ sửa `event_date` |
| 2 | Quyết định xử lý HDB 2025-12-18 | Minh Anh | §3 |
| 3 | **Chặn tái diễn**: Data gate FAIL nếu còn vi phạm DQ-007 loại `PERSISTS_LIKELY_CORP_ACTION` chưa có trong `corporate_actions` hoặc chưa có quyết định ghi nhận | Minh Anh + Ngọc | Hiện DQ-007 chỉ báo cáo, không chặn |
| 4 | Rebuild `qshield-data clean → features → eligibility` rồi `regime → scenarios` | Minh Anh, Tú | Chỉ sau (1) |
| 5 | Xem lại độ bền của `kurtosis_abs_diff` (một ô ngoại lai hợp lệ, vd sự kiện thật như COVID, cũng có thể fail): cân nhắc so reference **block-aligned** (cùng hỗ trợ 5 ngày với bootstrap) hoặc thang log | Tú đề xuất, **Phúc quyết** ngưỡng | Không tự đổi ngưỡng |
| 6 | Chạy lại thí nghiệm hybrid dưới experiment_id mới (v4) trên dữ liệu đã rebuild để đủ n ≥ 30 | Tân | Manifest mới, khóa trước khi chạy |

## 7. Tái lập

Script chẩn đoán (chạy trong scratchpad của phiên, logic tóm tắt): dựng lại panel/pool/cube đúng như
`qshield_pipeline.hybrid.instances.build_instance_inputs` cho từng instance Volatile trong
`manifest_confirmation.json` (v3), chấm `build_validation_report` hai lần — dữ liệu gốc và dữ liệu chỉ thay
return TCB 2024-06-11 bằng giá trị sau back-adjustment ×2,0.

Nguồn công khai tham khảo:
- [Techcombank (TCB) thực hiện chia cổ phiếu thưởng, tỷ lệ 1:1 — Tin nhanh chứng khoán](https://www.tinnhanhchungkhoan.vn/techcombank-tcb-thuc-hien-chia-co-phieu-thuong-ty-le-11-post347060.html)
- [Techcombank chốt danh sách cổ đông nhận thưởng cổ phiếu tỷ lệ 100% — Mekong ASEAN](https://mekongasean.vn/techcombank-chot-danh-sach-co-dong-nhan-thuong-co-phieu-ty-le-100-30005.html)
- [HDBank chốt quyền chia cổ tức và cổ phiếu thưởng gần 30% — Vietstock](https://vietstock.vn/2025/12/hdbank-chot-quyen-chia-co-tuc-va-co-phieu-thuong-gan-30-757-1380182.htm)
- [HDBank chốt quyền chia gần 30% cổ tức và cổ phiếu thưởng — HDBank](https://hdbank.com.vn/vi/news/detail/tin-tuc/hdbank-chot-quyen-chia-gan-30-co-tuc-va-co-phieu-thuong-vao-ngay-ca-nuoc-khoi-cong-khanh-thanh-245-du-an-lon)
