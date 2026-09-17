# Cập nhật `CLEAN.ipynb` — đổi nguồn giá sang `Full_Prices.xlsx` (FiinPro)

Ngày: 2026-09-17 · Từ: Mạnh · Gửi: Tân, Tú, Phúc
Phản hồi cho: note gửi Mạnh ngày 14/09 (đã gộp vào `docs/data/2026-09-13-scenario-gate-volatile-loi-tcb.md`, bản gốc còn trong git history)

---

## TL;DR

- Giá 30 mã **không còn tải qua API** (Yahoo + DNSE). Notebook đọc `data/raw/Full_Prices.xlsx` (export FiinPro) rồi tách ra từng mã.
- VN-Index **vẫn tải qua API vnstock**, vì file Excel không có chỉ số.
- Bộ bàn giao chỉ cần **`CLEAN.ipynb` + `data/raw/Full_Prices.xlsx`**. Đã chạy thử trong một thư mục trống chỉ có 2 file này: chạy thông, DQ gate PASS.
- **Cả hai lỗi TCB và HDB trong báo cáo ngày 14/09 đã hết** mà không cần sửa tay. Nhưng ngày sự kiện TCB trong báo cáo đó sai, và **không được áp registry `corporate_actions` lên dữ liệu mới** (xem mục 3).
- Schema `returns.parquet` **giữ nguyên như cũ**, code phía sau không phải đổi.

---

## 1. Code đã sửa gì so với bản cũ

### 1.1. Nguồn giá cổ phiếu (Bước 2)

| | Bản cũ | Bản mới |
|---|---|---|
| Nguồn | API: 24 mã Yahoo Finance + 6 mã đa sàn DNSE | File `data/raw/Full_Prices.xlsx` (FiinPro) cho cả 30 mã |
| Cách lấy | Gọi API từng mã, có retry và fallback | Đọc Excel, tự dò dòng tiêu đề, bỏ 11 dòng rác cuối file (thông tin liên hệ FiinGroup) |
| File raw | `{ngày}_yfinance_{mã}.csv`, `{ngày}_dnse_{mã}.csv` | `{ngày}_fiinpro_{mã}.csv` — 30 file, 70,202 dòng, có checksum SHA-256 |
| `data_source` trong Universe Register | `yahoo` / `dnse` | `fiinpro` |

Lý do bỏ Yahoo: khi đối chiếu, dữ liệu Yahoo có **721 bar bị nhân bản** y hệt phiên liền trước (24/30 mã), **2,131 ngày không có giao dịch thật** (ngày nghỉ lễ Yahoo tự điền), và sai ở đúng các ngày chia thưởng (TCB, HDB). DNSE sạch hơn nhưng không có giá gốc, và khối lượng không cùng thang với giá điều chỉnh.

FiinPro có đủ thứ cả hai nguồn API đều thiếu: **giá gốc**, **giá điều chỉnh**, và **giá trị khớp lệnh thật**. Khi quét: 0 dòng trùng, 0 bar nhân bản, 0 ngày lệch lịch giao dịch.

### 1.2. VN-Index (Bước 2)

| | Bản cũ | Bản mới |
|---|---|---|
| Cách gọi | `Vnstock().stock(...)`, gọi 1 lần cho cả giai đoạn | `vnstock.api.quote.Quote`, **tải theo từng năm** rồi ghép |
| Khoảng | 2016-01-01 → 2026-07-31 | Như cũ |
| Kiểm tra | Không | **Dừng notebook** nếu VN-Index thiếu ngày so với `Full_Prices.xlsx` |

Hai vấn đề đã xử lý:
- Lớp `Vnstock()` **đã ngừng hỗ trợ từ 31/08/2025**. Bản mới dùng API mới, chỉ quay về cách cũ nếu máy cài vnstock đời cũ.
- API **chỉ trả tối đa ~2,000 phiên mỗi lần gọi, đếm lùi từ ngày `end`**. Gọi một lần cho 2016–2026 thì mất toàn bộ dữ liệu trước 02/08/2018. Vì lịch VN-Index được dùng để loại ngày không có giao dịch thật, thiếu lịch sẽ **âm thầm xoá luôn giá cổ phiếu 2016–2018**. Tải theo năm (~262 phiên/lần) thì đủ 2,642 phiên; thêm chốt kiểm tra để lỗi này không thể xảy ra âm thầm.

### 1.3. Chuẩn hoá dữ liệu (Bước 3)

- **Cột giá có nghĩa khác trước:** `open/high/low/close` giờ là **giá gốc** khớp trên sàn; `adjusted_close` là giá điều chỉnh của FiinPro. (Với Yahoo, `close` là một dạng giá đã điều chỉnh một phần, không phải giá gốc.)
- **`turnover_value` lấy thẳng từ "Giá trị khớp lệnh"**, không còn tính `close × volume`. Cách tính cũ trên dữ liệu API sai khoảng 23% ở các phiên trước ngày chia thưởng.
- **Thêm vào `prices_adjusted.parquet`:** `volume_negotiated`, `turnover_negotiated` (giao dịch thoả thuận).
- **Không đưa cột "Tỷ lệ điều chỉnh" của FiinPro vào dữ liệu processed.** Cột này bỏ sót sự kiện (ví dụ FPT 25/05/2018 có chia thưởng nhưng để trống), và không phép tính nào cần nó. Cột gốc `AdjRatio` vẫn còn trong CSV raw để tra cứu.
- **Lọc ngày không có giao dịch thật** giờ áp cho mọi nguồn, không riêng Yahoo. Với FiinPro kết quả là 0 dòng.
- **Thêm cờ `INVALID_OHLC`** khi `high < low` hoặc `open` nằm ngoài [low, high]. Không kiểm tra `close`, vì giá đóng cửa có thể là giá bình quân gia quyền (ví dụ trên UPCOM) nên có thể nằm ngoài [low, high].
- **Thêm `RAW_PRICE_PATCHES`** (cell Config) để vá lỗi nằm ngay trong file Excel, áp lúc tách file. Hiện có 1 bản vá:

  | Mã | Ngày | Cột | Excel ghi | Sửa thành | Căn cứ |
  |---|---|---|---|---|---|
  | VIB | 23/07/2018 | Close | 0 | 28,200 | Bảng giá lịch sử VIB: đóng cửa 28.20, điều chỉnh 3.16, O/H/L 28.00/28.90/28.00, KL 218,470, GT 6.21 tỷ |

### 1.4. Universe Register

- `data_source = "fiinpro"` cho cả 30 mã.
- **VPL: `first_trading_date` sửa từ `2025-01-01` (giá trị tạm) → `2025-05-13`** (phiên đầu tiên trong Full_Prices.xlsx). Nhờ vậy VPL trước 13/05/2025 được gắn `NOT_LISTED_AT_DATE` thay vì `INSUFFICIENT_HISTORY`.

### 1.5. Không đổi

- Schema `returns.parquet`: `date, ticker, simple_return, log_return, adjusted_close, volume, turnover_value, quality_flag, source_id, data_version, split`.
- Cách tính returns, market features, eligibility, chia train/validation/test, các check DQ-001 → DQ-010.

### 1.6. Các chỗ khác đã cập nhật

Source Register, data dictionary (`data_dictionary.xlsx`), ghi chú markdown Bước 2 và 3, ghi chú cuối DQ gate, dòng `pip install` ở cell đầu (thêm `matplotlib`, `scipy`, `requests` vốn bị thiếu; giới hạn `vnstock>=4.0,<5`).

### 1.7. Code còn trong notebook nhưng không chạy

- Các hàm `download_ticker*` cho Yahoo/DNSE/vnstock cổ phiếu — giữ để tham khảo, không được gọi.
- Cell kiểm tra kết nối DNSE — tắt bằng `RUN_NETWORK_DIAGNOSTIC = False`.
- `PRICE_CORRECTIONS` cho 2 bar HDB của Yahoo — chỉ áp khi dữ liệu đến từ Yahoo, nên **tự tắt** với FiinPro (notebook in dòng "bỏ qua").

### 1.8. Cách chạy

```
thư_mục_bất_kỳ/
├── CLEAN.ipynb
└── data/raw/Full_Prices.xlsx
```

- Python ≥ 3.10 (đã chạy thử với 3.12 + vnstock 4.0.5). Bỏ dấu `#` ở cell cài package và chạy một lần.
- Cần **internet** để tải VN-Index.
- Mở notebook với thư mục làm việc là thư mục chứa `CLEAN.ipynb`, rồi **Run All**.

---

## 2. Những điều cần chú ý về bộ data này

### Dễ dùng sai

1. **`adjusted_close` neo theo ngày export (16/09/2026), không phải ngày cuối dữ liệu (31/07/2026).** 7 mã có giá điều chỉnh khác giá gốc ngay ở phiên cuối: VHM ×0.50, SSI ×0.80, MBB ×0.83, VIB ×0.91, BID ×0.94, PLX ×0.97, BSR ×0.99 — có vẻ do các sự kiện có ngày không hưởng quyền sau 31/07. **Returns không bị ảnh hưởng.** Nhưng **không dùng `adjusted_close` làm "giá hiện tại"** (số lô, ngân sách, định giá danh mục) — dùng `close`.
2. **Chỉ giá đóng cửa có bản điều chỉnh.** `open/high/low` là giá gốc. Feature dùng biên độ trong phiên (ATR, high − low, gap mở cửa) sẽ nhảy giả ở mọi ngày chia thưởng.
3. **Không áp thêm điều chỉnh corporate action nào lên dữ liệu này** (kể cả registry `corporate_actions` bên pipeline khác). Dữ liệu đã được điều chỉnh sẵn — áp thêm là điều chỉnh hai lần.
4. **`turnover_value` chỉ gồm khớp lệnh**, không gồm thoả thuận.

### Đặc điểm cần biết khi mô hình hoá

5. **VHM: FiinPro gộp lịch sử lạ vào trước ngày niêm yết.** File Excel có 381 phiên VHM từ 04/01/2016 → 13/07/2017 (chỉ 02–04/2016 có giao dịch, tổng 9,800 cổ phiếu), rồi 209 phiên trống, rồi niêm yết 17/05/2018 ở 110,500 (+268%). **Pipeline đã tự loại** nhờ quy tắc bỏ dòng trước `first_trading_date` (PR-DAT-017): trong `returns.parquet` VHM bắt đầu 17/05/2018, |return| lớn nhất 7.0%. Đoạn gộp vẫn nằm trong CSV raw. Đã kiểm tra SSB, VRE, VIC, HDB: **không bị gộp**.
6. **Chốt chặn duy nhất cho lịch sử bị gộp là `first_trading_date`** trong Universe Register. Ngày này khai sai thì dữ liệu gộp lọt thẳng vào returns.
7. **6 mã từng chuyển sàn thiếu vài phiên lúc chuyển** — tổng 39 phiên, được gắn `SUSPENDED_OR_NO_DATA`:

   | Mã | Khoảng trống | Sự kiện |
   |---|---|---|
   | GVR | 09–16/03/2020 (6 phiên) | UPCOM → HOSE |
   | LPB | 26/10–06/11/2020 (10 phiên) | UPCOM → HOSE |
   | VIB | 30/10–09/11/2020 (7 phiên) | UPCOM → HOSE |
   | ACB | 02–08/12/2020 (5 phiên) | HNX → HOSE |
   | SHB | 06–08/10/2021 (3 phiên) | HNX → HOSE |
   | BSR | 07–16/01/2025 (8 phiên) | UPCOM → HOSE |

   Return phiên đầu sau khoảng trống gộp nhiều ngày. Trước khi lên HOSE biên độ là ±10% (HNX) / ±15% (UPCOM), nên biến động giai đoạn đó lớn hơn — ảnh hưởng tới ước lượng đuôi/CVaR. |return| lớn nhất toàn bộ dữ liệu là −14.51% (BSR 15/11/2022, khi còn trên UPCOM).
8. **44 phiên khối lượng = 0 là có thật:** HOSE ngừng giao dịch 23–24/01/2018 (chính VN-Index cũng đi ngang, KL 0) → return = 0 cho mọi mã HOSE hai ngày đó; cùng vài phiên tăng trần không khớp lệnh ngay sau niêm yết (VRE 07–09/11/2017, VHM 18–21/05/2018).
9. **VIB 04/07/2019: close 16,800 thấp hơn low 16,900** — giữ nguyên, không coi là lỗi (giá đóng cửa trên UPCOM là bình quân gia quyền). Lưu ý: bình quân gia quyền tính từ giá trị/khối lượng của chính phiên đó ra 17,347 (khớp lệnh) hoặc 17,460 (gồm thoả thuận), đều ≥ low.
10. **VPL có rất ít lịch sử:** niêm yết 13/05/2025, đủ điều kiện từ 15/05/2026 (56 phiên), không có trong train/validation. Tên công ty trong Universe Register vẫn là giá trị tạm.

### Quản lý dữ liệu

11. **Dữ liệu là ảnh chụp tĩnh tới 31/07/2026.** Cập nhật phải export lại từ FiinPro — và lần export mới sẽ **thay đổi toàn bộ `adjusted_close` lịch sử** (vì mốc neo dời đi). Mỗi lần export nên đánh phiên bản dữ liệu mới, không trộn kết quả giữa các lần.
12. **Giá (FiinPro) và VN-Index (vnstock/VCI) đến từ hai nhà cung cấp.** Hiện lịch giao dịch khớp 100%. Khi export lại tới ngày mới hơn, phải tải VN-Index tới cùng ngày.
13. **DQ gate chưa có check tự động bắt return vượt biên độ sàn.** Dữ liệu hiện tại đạt, nhưng lần export sau có lỗi tương tự sẽ không bị chặn.
14. **FiinPro là dữ liệu thương mại** — chỉ dùng nội bộ, không đưa lên repo công khai.

---

## 3. Đối chiếu với báo cáo lỗi ngày 14/09 (TCB & HDB)

### 3.1. TCB — ✅ đã hết lỗi, nhưng ngày sự kiện trong báo cáo sai

| date | close (giá gốc) | adjusted_close | simple_return |
|---|---|---|---|
| 10/06/2024 | 48,900 | 23,328.51 | −0.41% |
| **11/06/2024** | 49,350 | 23,543.19 | **+0.92%** |
| 12/06/2024 | 49,400 | 23,567.05 | +0.10% |
| 19/06/2024 | 48,300 | 23,042.28 | −1.02% |
| **20/06/2024** | **24,800** | 23,662.46 | **+2.69%** |

- Không còn cú −49.5%. Return 11/06/2024 = **+0.92%**, đúng như kỳ vọng ở mục 5 của báo cáo.
- **Ngày không hưởng quyền thật là 20/06/2024, không phải 11/06/2024.** Giá gốc FiinPro giữ quanh 49,000 từ 11/06 đến 19/06, và giảm một nửa vào 20/06. Yahoo đã chia đôi giá **sớm 7 phiên**: từ 11/06 đến 19/06 Yahoo báo giá bằng đúng một nửa giá thật (24,675 so với 49,350) và khối lượng gấp đôi.
- ⚠️ **Entry TCB đã thêm vào `configs/base.yaml → corporate_actions` (`event_date: 2024-06-11`, `adjustment_factor: 2.0`) không được áp lên dữ liệu FiinPro.** `adjusted_close` đã được điều chỉnh sẵn — áp thêm sẽ điều chỉnh hai lần và *tạo ra* một bước nhảy khoảng −50% đúng vào 11/06/2024. Đề nghị xoá entry, hoặc đổi trạng thái thành không áp dụng cho nguồn đã điều chỉnh.

### 3.2. HDB — ✅ đã hết lỗi

| date | close (giá gốc) | adjusted_close | simple_return |
|---|---|---|---|
| 16/12/2025 | 32,100 | 24,752.31 | +7.00% |
| 17/12/2025 | 32,100 | 24,752.31 | 0.00% |
| **18/12/2025** | **25,600** | **25,600.00** | **+3.42%** |
| 19/12/2025 | 25,950 | 25,950.00 | +1.37% |
| 22/12/2025 | 27,000 | 27,000.00 | +4.05% |

- Không còn cặp +29.7% / −19.2%.
- FiinPro xác nhận đúng như báo cáo: ngày không hưởng quyền **18/12/2025**, hệ số **1.2969** (FiinPro ghi tỷ lệ 0.7711 = 1/1.2969 ở phiên 17/12/2025).
- Giá 18/12/2025 khớp bảng giá lịch sử: mở 25.00 / cao 26.00 / thấp 24.75 / đóng 25.60.
- **Chẩn đoán "17/12 lặp y hệt phiên trước" trong báo cáo chưa đúng.** Đóng cửa hai phiên bằng nhau là có thật: giá gốc cả hai đều 32,100, nhưng mở/cao/thấp và khối lượng khác nhau (16/12 tăng trần +7%, 17/12 đóng cửa lại đúng mức đó). Lỗi thật của Yahoo nằm ở dòng 18/12: đó chính là bar của phiên 17/12 (giá gốc 32,000 / 32,550 / 31,700 / 32,100, KL 23,353,800) bị gán sang ngày sau.

### 3.3. Kiểm tra toàn bộ

- |return| lớn nhất: **14.51%** (BSR, khi còn trên UPCOM, biên độ ±15%).
- Số phiên **trên HOSE** có |return| > 7.5%: **0**. Kỳ vọng "không còn |return| > 7.5% nào chưa có giải thích" ở mục 5 của báo cáo đã đạt.

### 3.4. Trạng thái từng việc trong báo cáo

| Việc | Trạng thái |
|---|---|
| TCB: chốt ngày không hưởng quyền | ✅ **20/06/2024** (theo FiinPro), không phải 11/06 |
| TCB: xác nhận hệ số 2.0 | ✅ FiinPro ghi tỷ lệ 0.5000 = 1/2.0 |
| TCB: đổi `verification_status` sang `CONFIRMED` | ❌ **Không nên** — entry sai ngày, và không được áp lên dữ liệu đã điều chỉnh |
| HDB: đối chiếu nguồn thứ hai 15→23/12/2025 | ✅ FiinPro và bảng giá lịch sử khớp nhau |
| HDB: quyết định xử lý ô 17/12 và 18/12 | ✅ Không cần xử lý — dữ liệu FiinPro đúng sẵn |
| Mục 3: data gate FAIL khi còn vi phạm biên độ chưa giải thích | ⏳ **Chưa làm** trong `CLEAN.ipynb` |
| Mục 3: rà các dòng khác (TCB 17/02/2021, HDB 06/12/2019, HDB 03/11/2025…) | ✅ Trên dữ liệu mới không còn phiên HOSE nào vượt 7.5% |
| Mục 4: rebuild dữ liệu | ✅ Đã chạy lại toàn bộ `CLEAN.ipynb` |
| Mục 4: báo Tú chạy lại regime → scenarios; Tân chạy lại thí nghiệm | ⏳ Cần làm — returns đã đổi |

### 3.5. Lưu ý khi chạy lệnh kiểm tra ở mục 5 của báo cáo

- Báo cáo viết cho pipeline khác (`uv run qshield-data`, `configs/base.yaml`, `price_limit_violations_traced.csv`) — các thành phần này **không có** trong thư mục dùng `CLEAN.ipynb`. DQ-007 của `CLEAN.ipynb` là "Ticker trong returns khớp universe", không phải check biên độ.
- Script ở mục 5 chọn cột `close` từ `returns.parquet` — **cột này không có** trong `returns.parquet` nên sẽ báo lỗi. `close` nằm trong `prices_adjusted.parquet`. Dùng thay thế:

```python
import pandas as pd
p = pd.read_parquet('data/processed/prices_adjusted.parquet')
r = pd.read_parquet('data/processed/returns.parquet')
m = p.merge(r[['date', 'ticker', 'simple_return']], on=['date', 'ticker'])
cols = ['date', 'close', 'adjusted_close', 'simple_return']
print(m[(m.ticker == 'TCB') & m.date.between('2024-06-10', '2024-06-21')][cols])
print(m[(m.ticker == 'HDB') & m.date.between('2025-12-16', '2025-12-22')][cols])
print('max |simple_return|:', r.simple_return.abs().max())
```
