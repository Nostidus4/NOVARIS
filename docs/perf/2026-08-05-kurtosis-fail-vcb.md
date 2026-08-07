# Truy nguyên FAIL kurtosis ở regime `volatile` — cấu hình main, 2026-08-05

Doc đồng hành với [`2026-08-04-scenario-scaling.md`](2026-08-04-scenario-scaling.md). Doc kia đo
thời gian chạy và ghi nhận "cổng kiểm định trên dữ liệu thật hiện FAIL" như một điều kiện biên. Doc
này trả lời câu bị bỏ ngỏ ở đó: **FAIL vì cái gì.**

**Kết luận ngắn:** cổng FAIL vì **đúng một quan sát** trong 21.088 dòng — VCB ngày 2025-03-03, một
sự kiện chia cổ tức bằng cổ phiếu ~49,5% **chưa được điều chỉnh**. Trung hòa riêng dòng đó đưa
metric từ 16,25 (FAIL) xuống 0,11 (PASS). Không có nguyên nhân thứ hai.

Phạm vi doc này là **chẩn đoán**, không phải sửa. Việc sửa nằm ở `packages/data` (§6).

## 1. Triệu chứng

Cấu hình main (`configs/scenarios.yaml`: `S=500, H=20, block=5`), dữ liệu thật, run
`run_20260804_180123`. Trong 27 dòng của `scenario_validation.csv` có **đúng một** FAIL:

| target_regime | metric | scenario | reference | statistic | ngưỡng | verdict |
|---|---|---|---|---|---|---|
| volatile | `kurtosis_abs_diff` | 45,49 | 29,25 | **16,25** | 5,0 | **FAIL** |

26 metric còn lại PASS, gồm cả `skew_abs_diff` của chính regime volatile (0,68 < 1,0). `normal` và
`stress` PASS toàn bộ, kurtosis lần lượt 3,40/3,31 và 2,67/2,88 — tức **cùng một pipeline cho ra
kurtosis ~3 ở hai regime kia và ~45 ở volatile**. Chênh lệch một bậc độ lớn giữa các regime là dấu
hiệu đầu tiên cho thấy nguyên nhân nằm ở dữ liệu, không ở thuật toán.

## 2. Nguyên nhân gốc: VCB 2025-03-03

Quan sát cực đoan nhất toàn panel:

| date | ticker | log_return | simple return |
|---|---|---|---|
| **2025-03-03** | **VCB** | **−0,402126** | **−33,11%** |
| 2025-10-13 | VIC | +0,134784 | +14,43% |
| 2021-07-09 | MWG | +0,118350 | +12,56% |

Ba lý do độc lập cho thấy đây **không phải biến động giá thật**:

1. **Vượt biên độ sàn.** HOSE giới hạn ±7%/phiên. −33,11% là bất khả thi về mặt cấu trúc, không
   phải "hiếm".
2. **Lớn gấp 2,9 lần quan sát kế tiếp** trong hơn 6 năm dữ liệu (VIC +14,43%).
3. **Không có tài sản nào khác động đậy.** Cùng phiên: ACB 0,00% · CTG −0,60% · FPT +0,14% ·
   HPG +0,18% · MWG +0,86% · VIC +2,06% · VNM +1,61%. Một cú sốc thị trường thật không đánh trúng
   duy nhất một mã ngân hàng đầu ngành.

Giá thô xác nhận là sự kiện doanh nghiệp:

| date | Adj Close | Close |
|---|---|---|
| 2025-02-28 | 91.862,35 | 93.300,00 |
| 2025-03-03 | 61.446,39 | 62.408,03 |

Tỷ lệ **1,4950** ở *cả hai* cột — khớp với chia cổ tức bằng cổ phiếu ~49,5% (nhận thêm ~1 cổ phiếu
cho mỗi 2 cổ phiếu đang giữ). Tài sản của nhà đầu tư không đổi; chỉ mệnh giá mỗi cổ phiếu đổi.

### 2.1 Giả định đã hỏng

`packages/data/src/qshield_data/clean/corporate_actions.py:5` ghi rõ giả định thiết kế:

> Split/dividend adjustment KHÔNG cần re-implement ở đây: Yahoo (`Adj Close`) và DNSE đều đã trả
> giá điều chỉnh cổ tức + chia tách sẵn

**Giả định này sai với sự kiện VCB 2025-03-03.** `Adj Close` mang **đúng cùng bước nhảy 1,4950** với
`Close` — Yahoo không điều chỉnh sự kiện này. Đây không phải lỗi cài đặt: code làm đúng những gì nó
tuyên bố. Đây là một giả định về nguồn dữ liệu, đúng trong đa số trường hợp, và im lặng khi sai.

Chính docstring đó đã lường trước lối thoát: tên file giữ là `corporate_actions.py` thay vì
`pre_listing.py` "để có chỗ mở rộng nếu sau này chuyển sang raw price + tự tính adjustment factor".

## 3. Vì sao chỉ `volatile` gãy

Ngày 2025-03-03 mang nhãn regime `volatile`. Đếm số lần nó lọt vào pool từng regime:

| regime | pool | có mặt trong block-5d | có mặt trong cửa sổ ref-20d |
|---|---|---|---|
| normal | 599 | **0** | **0** |
| volatile | 864 | 5 | 20 |
| stress | 1083 | **0** | **0** |

`normal` có anchor cuối 2020-01-22 nên không thể chạm tới 2025. `stress` không neo vào vùng đó.
Hai regime kia PASS **không phải vì chúng khỏe hơn** — mà vì chúng chưa bao giờ nhìn thấy dòng dữ
liệu hỏng.

## 4. Cơ chế khuếch đại

Một quan sát hỏng đủ để phá metric vì bootstrap **nhân bản** nó:

- Ngày đó nằm trong 5 block trên tổng 864 block của pool volatile.
- Mỗi cube rút 2.000 block ⇒ kỳ vọng `2000 × 5/864 = 11,57` lần xuất hiện.
- Đo thật trên 40 seed: trung bình **11,30**, sd **3,24**, dao động **6 → 21**.
- **Tương quan(số lần xuất hiện, kurtosis cube) = 0,983.**

Tức ~97% phương sai của verdict chỉ là chuyện *một con số sai được rút trúng bao nhiêu lần*.

Hệ quả thứ hai, đáng lo hơn cả FAIL: **verdict không ổn định theo seed.** Trên 40 seed, kurtosis
cube trải từ 20,0 đến 52,1 (sd 6,83) và **23/40 seed cho FAIL** — cùng code, cùng dữ liệu, kết quả
gần như tung đồng xu.

Phân rã chênh lệch 16,25:

| Thành phần | Đóng góp |
|---|---|
| Lệch day-set (cube ghép block 5 ngày; reference là cửa sổ 20 ngày) | 4,16 |
| Resampling (nhân bản quan sát hỏng) | 12,09 |

Cả hai chỉ là **bộ khuếch đại**, không phải nguyên nhân — xem §5.

## 5. Phép thử phản chứng

Trung hòa **đúng một dòng** (VCB 2025-03-03 → `log_return = 0`), giữ nguyên mọi thứ khác:

| | Nguyên trạng | Bỏ 1 dòng / 21.088 |
|---|---|---|
| kurtosis cube | 45,49 | **4,40** |
| kurtosis reference | 29,25 | **4,29** |
| \|chênh lệch\|, ngưỡng 5,0 | **16,25 FAIL** | **0,11 PASS** |
| số seed FAIL / 40 | 23 | **0** |
| sd của ước lượng qua 40 seed | 6,83 | **0,15** |

Hai điều đọc được:

1. **Không có nguyên nhân thứ hai.** Kurtosis rơi từ 45,49 về 4,40 — mức bình thường cho return
   ngày, khớp với `normal` (3,40) và `stress` (2,67).
2. **Metric không hề mong manh.** Sau khi gỡ quan sát hỏng, sd của ước lượng co từ 6,83 xuống 0,15
   (45 lần) và 0/40 seed FAIL. Ngưỡng 5,0 là hợp lý; **nới ngưỡng sẽ là che một lỗi dữ liệu thật.**

> Phản chứng này là **bằng chứng nhân quả**, không phải đề xuất sửa dữ liệu. CLAUDE.md quy tắc 5:
> không tự xóa outlier — gắn cờ và báo cáo. Không dòng dữ liệu nào bị sửa trong repo.

## 6. Không cổng nào bắt được — và đó mới là phát hiện

`packages/data/src/qshield_data/quality/checks.py` có 6 kiểm tra: `check_no_duplicates`,
`check_positive_prices`, `check_no_negative_volume`, `check_no_pre_listing`,
`check_universe_count`, `check_split_no_overlap`.

Comment đầu file liệt kê `outlier` trong phạm vi trách nhiệm, **nhưng không có kiểm tra outlier
nào tồn tại.**

Hệ quả: một biến động −33% trên thị trường có biên độ ±7% đi qua **toàn bộ** cổng chất lượng dữ
liệu, chảy xuôi ba chặng, và chỉ lộ ra ở chặng 3 dưới dạng một sai lệch thống kê. Scenario
Validation Gate đã làm đúng việc của nó như tuyến phòng thủ **cuối**, nhưng nó không nên là tuyến
**đầu tiên** phát hiện chuyện này.

## 7. Việc cần làm

| Việc | Chủ sở hữu | Trạng thái |
|---|---|---|
| **Phát hiện** — cổng chặn biến động vượt biên độ sàn ở chặng data | Nguyễn Anh Tú (`ai`) đề xuất, `data` duyệt | ✅ Xong — đã merge (`db38ee6`, `500a30b`, `1c39455`, `61ef99a`, `16aa20e`), `check_price_limit` (DQ-007) chạy thật trong `qshield-data quality` |
| **Sửa** — điều chỉnh sự kiện VCB 2025-03-03 (lấy adjustment factor hoặc đổi nguồn) | **Nguyễn Đỗ Minh Anh (`packages/data`)** | ✅ Xong — xem §9 |

Hai việc **tách rời có chủ ý**. Phát hiện là rẻ, tổng quát, và chặn cả lớp lỗi này về sau. Sửa là
phần khó — cần nguồn adjustment factor — và thuộc về người sở hữu chặng data.

## 9. Kết quả sau khi sửa (2026-08-06)

Hệ số điều chỉnh (1,4950) lấy trực tiếp từ bằng chứng đã có trong §2 của doc này — không cần nguồn
mới. Đăng ký thủ công (không suy diễn tự động, đúng CLAUDE.md quy tắc 5) trong
`configs/data.yaml["corporate_actions"]`, áp dụng qua
`qshield_data.clean.corporate_actions.apply_registered_adjustments()`: back-adjust `adjusted_close`
của mọi phiên VCB **trước** 2025-03-03 theo `1/1,4950` — không đụng `open/high/low/close/volume` thô.

Chạy lại full `qshield-data build` + `qshield-ai scenarios --force` trên dữ liệu thật
(`configs/base.yaml`):

| | Trước sửa | Sau sửa |
|---|---|---|
| DQ-007 (`price_limit_violations.csv`) | 24 dòng | **23 dòng** — VCB 2025-03-03 không còn |
| `volatile / kurtosis_abs_diff` (cube) | 45,49 | **4,40** |
| `volatile / kurtosis_abs_diff` (reference) | 29,25 | **4,29** |
| `volatile / kurtosis_abs_diff` verdict | **FAIL** (statistic 16,25 > ngưỡng 5,0) | **PASS** (statistic 0,113) |
| Toàn bộ 27 metric scenario validation | 26 PASS / 1 FAIL | **27 PASS / 0 FAIL** |

Số liệu sau sửa khớp gần như tuyệt đối với phép thử phản chứng đã dự đoán ở §5 (kurtosis cube dự
đoán 4,40, đo thật 4,40) — xác nhận back-adjustment đúng cách, không phải trùng hợp.

Test hồi quy: `packages/data/tests/test_corporate_actions.py` (8 test — back-adjust đúng ngày/hệ
số, không đụng cột thô, return sau sửa ≈0, ticker/entry không khớp bị bỏ qua an toàn, lỗi input rõ
ràng). `notebooks/exploration/01_data_workflow_update.ipynb` đã đồng bộ theo (bug cũ: gọi
`run_all_checks()` thiếu tham số `price_limit_violations` — đã sửa, đã chạy thử
`jupyter nbconvert --execute` full end-to-end thành công.

Lưu ý cho người làm phát hiện: ngưỡng ±7% cho ra **36/21.088 dòng** vượt (0,171%), trong đó chỉ
VCB 2025-03-03 là bất khả thi thật sự. Phần còn lại nằm khoảng 8–14% và cần soi từng dòng — ACB
niêm yết HNX trước 2020 (biên độ ±10%), nên một ngưỡng phẳng sẽ báo nhầm. Đây là lý do phát hiện
cần được thiết kế chứ không phải hard-code một con số.

## 8. Tái lập

```bash
PYTHONIOENCODING=utf-8 uv run qshield-ai scenarios --force --config configs/base.yaml
```

Đọc `artifacts/dev/scenarios/scenario_validation.csv`, dòng
`volatile,...,kurtosis_abs_diff,...,FAIL`. Giá thô đối chiếu tại
`data/raw/prices/20260804_yfinance_vcb.csv`.

`--force` đánh dấu run là `NON_BASELINE_RUN`. Artifact từ run này **không** được dùng làm đầu vào
cho Risk.
