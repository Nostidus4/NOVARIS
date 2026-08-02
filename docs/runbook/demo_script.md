# Demo script

Kịch bản trình bày Q-SHIELD trước giám khảo/người thẩm định, đi đúng năm khu vực dashboard và ba
kịch bản UAT đã chuẩn bị sẵn tại `configs/uat/`. Chủ trì: Nguyễn Thị Ánh Ngọc (Product Owner).

Trước khi demo, đọc `docs/limitations.md` và `docs/product/disclaimer.md` — mọi câu nói trong demo
phải nằm trong phạm vi bằng chứng mà artifact hỗ trợ, không được vượt quá.

---

## 0. Chuẩn bị (trước demo 15 phút)

1. Chạy trước một `run` ở chế độ `runs` (không chạy `dev`) để có `run_id` cố định trình chiếu:
   ```bash
   uv run qshield-pipeline all --config configs/base.yaml
   ```
2. Xác nhận cổng chặn QAOA đã pass: `uv run pytest packages/quantum/tests/test_consistency.py -v`.
3. Khởi động backend + frontend (xem `docs/runbook/setup.md` §3), hoặc chuẩn bị bản offline
   (`frontend/public/demo/`) làm phương án dự phòng — xem §5 bên dưới.
4. Ghi lại `run_id` sẽ dùng xuyên suốt demo; mọi số liệu nói ra phải truy được về đúng run này.

## 1. Mở đầu (1 phút)

Nói rõ ngay từ đầu, đúng theo `docs/product/disclaimer.md`:

> "Q-SHIELD là prototype dự thi, hệ thống hỗ trợ quyết định phòng vệ tail risk bằng tiền mặt cho
> danh mục cổ phiếu. Hệ thống không tự đặt lệnh và không phải khuyến nghị đầu tư."

Giới thiệu luồng một câu: `Data → Regime → Scenarios → Risk → QUBO → Exact/QAOA → CVaR after hedge`.

## 2. Portfolio Input (khu vực 1 — `app/page.tsx`)

Chọn một trong ba danh mục UAT đã cấu hình sẵn tại `configs/uat/`:

| File | Đặc điểm | Dùng để minh họa |
|---|---|---|
| `portfolio_balanced.yaml` | Danh mục cân bằng qua nhiều ngành | Hành vi hedge "điển hình" |
| `portfolio_banking.yaml` | Tập trung nhóm ngân hàng | Rủi ro tương quan chéo cao trong một ngành |
| `portfolio_volatile.yaml` | Nghiêng về mã biến động cao | CVaR nền cao, thấy rõ giá trị của hedge |

Nhập danh mục, chọn ngày đánh giá, nhấn chạy. Nêu rõ đây là danh mục 8 mã trong phạm vi đã khóa
(`CLAUDE.md`), không phải toàn bộ VN30.

## 3. Market Regime (khu vực 2 — `app/regime/page.tsx`)

- Chỉ ra trạng thái hiện tại (Normal/Volatile/Stress) và xác suất từng trạng thái — nhấn mạnh đây là
  **xác suất**, không phải nhãn cứng.
- Nếu đang ở kịch bản `portfolio_volatile`, đây là lúc chỉ ra `p_stress` cao hơn liên hệ trực tiếp
  đến ngân sách tiền mặt mục tiêu ở bước sau.

## 4. Stress Laboratory (khu vực 3 — `app/scenarios/page.tsx`)

- Cho xem một vài đường kịch bản trong 500 kịch bản × 20 ngày.
- Nêu rằng kịch bản được sinh có điều kiện theo trạng thái (regime-conditioned bootstrap), giữ
  nguyên tương quan chéo giữa 8 tài sản — không phải cú sốc đơn lẻ giả định thủ công.

## 5. Risk Before–After (khu vực 4 — `app/risk/page.tsx`)

- Đọc CVaR 95% **trước** hedge trực tiếp từ artifact của `run_id` đang trình chiếu.
- Chuyển sang **sau** hedge sau khi Quantum/Exact solver trả nghiệm (§6): so sánh CVaR, turnover,
  transaction cost, tiền mặt trước/sau.
- Nếu CVaR sau hedge **không** cải thiện ở kịch bản đang chạy: nói thẳng điều đó, không né tránh —
  đây chính là yêu cầu nghiệm thu (`docs/limitations.md` §8), không phải lỗi trình bày.

## 6. Quantum–Classical Benchmark (khu vực 5 — `app/quantum/page.tsx`)

- Trình bày cả ba: exact solver (duyệt đủ 2⁸ = 256 tổ hợp — ground truth), QAOA (p=1, 1024 shots,
  ≥10 seed), và kết quả đã được chấm lại bằng true CVaR.
- Nếu QAOA thua exact hoặc thua classical baseline ở run này: **báo cáo trung thực**, đúng nguyên
  văn `CLAUDE.md` quy tắc 18 — "Không tuyên bố quantum advantage."
- Nhấn đúng vai trò Quantum: nó quyết định K=3 hành động nào được chọn trong 8 mã, không phải chỉ
  một phép tính trang trí phía sau một kết quả đã có sẵn.

## 7. Kết luận và Q&A (2–3 phút)

- Nhắc lại: mọi số liệu vừa trình bày có `run_id`, config version, seed — có thể chạy lại độc lập
  bởi một thành viên khác không phải module owner (`docs/runbook/setup.md` §7).
- Dẫn `docs/limitations.md` khi được hỏi về độ tin cậy, survivorship bias, hoặc vai trò thật của
  Quantum.
- Không trả lời vượt quá bằng chứng artifact hỗ trợ — nếu giám khảo hỏi điều ngoài phạm vi đã khóa
  (ví dụ mở rộng VN30, thêm phái sinh), trả lời đó là ngoài phạm vi release hiện tại theo
  `docs/product/mvp_scope.md` §15 và §22 (Change Request), không ứng biến số liệu.

---

## 8. Phương án dự phòng khi deploy/backend lỗi

`frontend/public/demo/` chứa snapshot JSON offline của một run đã kiểm chứng. Nếu backend hoặc kết
nối mạng chết giữa lúc demo:

1. Chuyển frontend sang chế độ đọc từ `public/demo/` (không chạy lại QAOA).
2. Nói rõ với người xem đây là dữ liệu đã cache từ một run đã hoàn tất, kèm timestamp — **không**
   trình bày như dữ liệu real-time.
3. Nếu cả frontend cũng không chạy được, dùng video dự phòng đã quay trước (nếu có chuẩn bị) hoặc
   trình bày trực tiếp từ artifact JSON/CSV trong `artifacts/runs/<run_id>/outputs/`.

Xem thêm `docs/runbook/troubleshooting.md` cho các lỗi kỹ thuật cụ thể có thể gặp khi demo.
