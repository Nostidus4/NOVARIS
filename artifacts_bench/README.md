# artifacts_bench/

Solver bakeoff outputs (`NON_BASELINE_RUN`). **Không** trộn với `artifacts/dev/`.

---

## ⚠️ CẢNH BÁO 1 — Số trong thư mục này KHÔNG TÁI LẬP ĐƯỢC

Mọi artifact ở đây được sinh **trước** bản sửa 2026-09-04 cho lỗi seed QAOA.

Trước bản sửa, `seed` chỉ được truyền cho `StatevectorSampler` (seed việc **lấy mẫu**), còn
`QAOA(initial_point=None)` bốc điểm khởi tạo tham số qua `algorithm_globals.random` — một RNG
toàn cục không liên quan gì tới `seed`. Đo được: ba lần chạy cùng `seed=101` cho hai kết quả
khác nhau.

Hệ quả: `winning_bitstring`, `optimality_gap`, `success_prob`, `energy_stats`,
`qaoa_beats_classical` trong các file này **không dựng lại được**, dù artifact mang đủ
`registered_seeds`, `qubo_hash` và `candidate_order_hash`.

**Được phép dùng:** làm ghi chép lịch sử về việc "QAOA đã từng chạy ở quy mô 10-bit".
**KHÔNG được dùng:** làm bằng chứng cho bất kỳ so sánh solver nào, hoặc cho chữ ký duyệt trên
run hash (`plan.md` G3).

Muốn dùng làm bằng chứng ⇒ **phải chạy lại** sau bản sửa. Xem `reponse.md` F.5.

---

## ⚠️ CẢNH BÁO 2 — Không so các thư mục này với nhau

Đây chính là rủi ro `plan.md` R08 nêu: *"So sánh 8/10-bit full settings với 20-bit dev settings
để kết luận scaling chất lượng… chỉ mô tả các kết quả đã đo, chưa phải thí nghiệm scaling có
kiểm soát."*

| Thư mục | Quy mô | shots | maxiter | seeds | warm-start |
|---|---|---|---|---|---|
| `warm_start_run/` | 10-bit (5 mã) | 1024 | 200 | 10 | **bật** |
| `no_warm_start_run/` | 10-bit (5 mã) | 1024 | 200 | 10 | tắt |
| `stress_run/` | 10-bit **synthetic** | 256 | 30 | 1 | tắt |
| `narrative_run/` | 8–16 bit synthetic | 128 | 20 | 1 | tắt |
| `artifacts/runs/job_*/` | **20-bit** (10 mã) | **128** | **10** | **1** | tắt |

Các cấu hình lệch nhau tới **20 lần** ở `maxiter` và **8 lần** ở `shots`. Đặt cạnh nhau để suy ra
"chất lượng giảm khi tăng số bit" là kết luận sai.

Thí nghiệm scaling **có kiểm soát** (cùng settings, cùng máy, n = 8…20) nằm ở `reponse.md` F.2.

---

## ⚠️ CẢNH BÁO 3 — `stress_run/` và `narrative_run/` là instance TỔNG HỢP

Hai thư mục này dùng QUBO **do script sinh ra**, không phải QUBO cash-hedge thật. Lý do tồn tại
được ghi trong chính `tools/qaoa_stress_bakeoff.py`: QUBO thật gần như tuyến tính (nghiệm tối ưu
ở góc all-1s) nên exact == classical và không phân biệt được solver.

Không trộn số của chúng với bằng chứng true-CVaR của `workflow_update`.

---

## Tái tạo

Dùng `configs/workflow_update.yaml` (hoặc override tạm giảm bit). File
`qaoa_benchmark_10bit.yaml` không còn trong repo — profile của `warm_start_run`/
`no_warm_start_run` (`profile_id: qaoa_benchmark_10bit`) **không tái dựng được từ repo hiện tại**.
