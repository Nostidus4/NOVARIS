# Gửi Manh — Lỗi corporate action TCB & HDB trong dữ liệu giá (cần Data xử lý)

Ngày: 2026-09-14 · Từ: Tân · Mức ưu tiên: **Cao** (đang chặn scenario gate Volatile và làm sai CVaR)
Báo cáo đầy đủ: `docs/experiments/2026-09-13-volatile-scenario-gate-tcb.md`

---

## TL;DR

Dữ liệu Yahoo có **2 sự kiện chia cổ phiếu chưa được điều chỉnh đúng**. DQ-007 đã gắn cờ cả hai trong
`reports/price_limit_violations_traced.csv` nhưng chưa được đăng ký vào `corporate_actions`.

| Mã | Ngày | Biến động trong data | Sự kiện thật | Hệ quả |
|---|---|---|---|---|
| **TCB** | 2024-06-11 | **−49,5%** trong 1 phiên | Thưởng cổ phiếu **1:1** | 10/12 instance Volatile fail scenario gate; kịch bản chứa "cú sập giả" ⇒ CVaR phóng đại |
| **HDB** | 2025-12-18 / 19 | **+29,7%** rồi **−19,2%** | Cổ tức CP 25% + thưởng 4,69% (tổng **29,69%**) | Chưa làm fail gate, nhưng return 2 phiên này sai |

Cả hai đều vượt biên độ HOSE ±7% ⇒ không thể là giao dịch thật.

---

## 1. TCB 2024-06-11 — đã đề xuất cách sửa, cần Manh xác nhận

**Dữ liệu** (trùng khớp ở cả `data/raw/prices/20260807_yfinance_tcb.csv` và `20260814_yfinance_tcb.csv`):

| date | Close | Adj Close | Volume |
|---|---|---|---|
| 2024-06-10 | 48.900 | 46.657,28 | 8.633.400 |
| **2024-06-11** | **24.675** | **23.543,32** | **33.173.800** |
| 2024-06-12 | 24.700 | 23.567,18 | 18.315.800 |

- `Close` và `Adj Close` cùng giảm một nửa ⇒ Yahoo **không** điều chỉnh sự kiện.
- Giá giữ mức mới các phiên sau (không phải spike), volume ×3,8.
- Techcombank công bố thưởng cổ phiếu tỷ lệ 1:1 (100%) tháng 6/2024.

**Đã làm:** thêm entry vào `configs/base.yaml → corporate_actions` theo đúng mẫu VCB:

```yaml
- ticker: TCB
  event_date: '2024-06-11'
  type: bonus_share_1_for_1
  adjustment_factor: 2.0
  evidence: >-
    ...
  verification_status: PENDING_DATA_OWNER_CONFIRM_EX_DATE_AGAINST_HOSE_NOTICE
```

Hệ số **2,0** lấy từ tỷ lệ công bố (không dùng 1,9818 quan sát, để không xóa return thật +0,92% của phiên).
Sau điều chỉnh, return TCB ngày 2024-06-11 = **+0,916%**. Mình đã thử bằng script (không đổi data trên
đĩa): **12/12 instance Volatile PASS** scenario gate.

**Manh cần làm:**
- [ ] Đối chiếu **thông báo HOSE/VSD** để chốt ngày GDKHQ. Các bài báo tóm tắt ghi ngày chốt quyền không
      thống nhất, còn giá trong data giảm từ 2024-06-11. Nếu ngày GDKHQ khác ⇒ sửa `event_date`.
- [ ] Xác nhận hệ số 2,0 (thưởng 1:1 thuần, không kèm quyền mua/cổ tức cổ phiếu khác cùng ngày).
- [ ] Đổi `verification_status` sang `CONFIRMED` (hoặc sửa entry nếu mình sai).

---

## 2. HDB 2025-12-18 — CHƯA sửa, cần Manh quyết cách xử lý

**Dữ liệu** (trùng ở `20260807_yfinance_hdb.csv` và `20260814_yfinance_hdb.csv`):

| date | Close | Adj Close | Ghi chú |
|---|---|---|---|
| 2025-12-16 | 24.751,33 | 24.751,33 | giá lẻ ⇒ vendor đã điều chỉnh |
| 2025-12-17 | 24.751,33 | 24.751,33 | **lặp y hệt phiên trước** |
| **2025-12-18** | **32.100** | **32.100** | giá chẵn ⇒ chưa điều chỉnh |
| 2025-12-19 | 25.950 | 25.950 | |
| 2025-12-22 | 27.000 | 27.000 | |

- HDBank công bố ngày GDKHQ **2025-12-18**, tổng tỷ lệ **29,69%** ⇒ hệ số 1,2969.
- 32.100 / 24.751,33 = **1,29690** — đúng bằng hệ số sự kiện ⇒ Yahoo đã điều chỉnh các phiên trước nhưng
  **đặt điểm cắt lệch ngày** (ô 12-18 là giá chưa điều chỉnh, 12-17 là giá lặp).

**Vì sao không sửa bằng registry như TCB:** `apply_registered_adjustments` chia `adjusted_close` các phiên
trước `event_date` cho hệ số — với HDB các phiên đó **đã** được Yahoo điều chỉnh rồi ⇒ sẽ điều chỉnh hai lần.

**Manh cần làm:**
- [ ] Đối chiếu DNSE (hoặc nguồn thứ hai) giá HDB 2025-12-15 → 2025-12-23.
- [ ] Quyết định xử lý ô 2025-12-17/18: thay bằng nguồn đã đối chiếu có evidence, hoặc gắn cờ và loại
      return 2 phiên đó theo `missing_data_policy` (có log). **Không xóa im lặng, không forward-fill.**

---

## 3. Chặn tái diễn (đề xuất)

Hiện DQ-007 chỉ **báo cáo** vi phạm biên độ, không **chặn**. VCB, TCB, HDB đều lọt qua với
`quality_flag = OK`.

- [ ] Data gate **FAIL** nếu `price_limit_violations_traced.csv` còn dòng `PERSISTS_LIKELY_CORP_ACTION`
      hoặc `SPIKE_REVERSES_AMBIGUOUS` **chưa có** entry trong `corporate_actions` hoặc chưa có quyết định
      ghi nhận (vd. `accepted_as_real_move` + evidence).
- [ ] Rà lại các dòng khác cùng loại trong file đó (vd. TCB 2021-02-17, HDB 2019-12-06, HDB 2025-11-03…):
      phần lớn vượt ngưỡng ít (~1–3pp), có thể là biên độ ngày đầu niêm yết/sàn cũ, nhưng nên có quyết định.

---

## 4. Sau khi Manh xác nhận

1. Rebuild: `uv run qshield-data clean` → `features` → `eligibility`.
2. Báo Tú chạy lại `regime` → `scenarios` (return đổi ⇒ regime/kịch bản có thể đổi).
3. Báo Tân: thí nghiệm hybrid sẽ chạy lại dưới **experiment_id mới (v4)** — kết quả v3 giữ nguyên, không trộn.

## 5. Kiểm tra nhanh sau rebuild

```bash
uv run python -c "
import pandas as pd
r = pd.read_parquet('data/processed/returns.parquet'); r['date'] = pd.to_datetime(r['date'])
print(r[(r.ticker=='TCB') & r.date.between('2024-06-10','2024-06-12')][['date','close','adjusted_close','simple_return']])
print(r[(r.ticker=='HDB') & r.date.between('2025-12-16','2025-12-22')][['date','close','adjusted_close','simple_return']])
print('max |simple_return|:', r.simple_return.abs().max())
"
```

Kỳ vọng: TCB 2024-06-11 `simple_return` ≈ +0,92%; không còn |return| > 7,5% nào chưa có giải thích.

---

**Nguồn công khai:**
- [Techcombank (TCB) thực hiện chia cổ phiếu thưởng, tỷ lệ 1:1 — Tin nhanh chứng khoán](https://www.tinnhanhchungkhoan.vn/techcombank-tcb-thuc-hien-chia-co-phieu-thuong-ty-le-11-post347060.html)
- [Techcombank chốt danh sách cổ đông nhận thưởng cổ phiếu tỷ lệ 100% — Mekong ASEAN](https://mekongasean.vn/techcombank-chot-danh-sach-co-dong-nhan-thuong-co-phieu-ty-le-100-30005.html)
- [HDBank chốt quyền chia cổ tức và cổ phiếu thưởng gần 30% — Vietstock](https://vietstock.vn/2025/12/hdbank-chot-quyen-chia-co-tuc-va-co-phieu-thuong-gan-30-757-1380182.htm)
- [HDBank chốt quyền chia gần 30% cổ tức và cổ phiếu thưởng — HDBank](https://hdbank.com.vn/vi/news/detail/tin-tuc/hdbank-chot-quyen-chia-gan-30-co-tuc-va-co-phieu-thuong-vao-ngay-ca-nuoc-khoi-cong-khanh-thanh-245-du-an-lon)
