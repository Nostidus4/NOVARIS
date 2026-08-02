# Troubleshooting

Tổng hợp sự cố đã gặp thật (không phải suy đoán) trong quá trình cài đặt, phát triển và demo
Q-SHIELD, cùng nguyên nhân và cách xử lý. Xem `docs/runbook/setup.md` cho quy trình cài đặt chuẩn và
`docs/runbook/demo_script.md` §8 cho phương án dự phòng khi demo.

---

## 1. Cài đặt

### `uv sync` báo thiếu `pyproject.toml`

Một workspace member chưa có file khai báo. Kiểm tra:

```bash
ls packages/*/pyproject.toml backend/pyproject.toml
```

Phải ra đủ 7 dòng (`contracts`, `data`, `ai`, `risk`, `quantum`, `pipeline`, `backend`).

### `ModuleNotFoundError: qshield_contracts` (hoặc `qshield_*` khác)

Thiếu `src/qshield_contracts/__init__.py` (hoặc tương đương ở package khác). `uv_build` bắt buộc
file này tồn tại, kể cả rỗng.

### `Found conflicting Python requirements`

`requires-python` giữa `pyproject.toml` gốc và một package thành viên không khớp. Tất cả phải là
`>=3.14,<3.15`.

---

## 2. Qiskit / QAOA

### `ImportError` khi `from qiskit.primitives import Sampler`

Repo dùng qiskit **2.x**, primitive V1 (`Sampler`) đã bị xóa. Mọi ví dụ QAOA tìm thấy trên mạng viết
cho 1.x sẽ chết ngay dòng import này.

Đường đúng — đã test ra nghiệm khớp exact solver:

```python
from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer

sampler = StatevectorSampler(default_shots=1024, seed=42)
qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=200), reps=1)
result = MinimumEigenOptimizer(qaoa).solve(qubo)
```

### `ModuleNotFoundError` khi import thuật toán QAOA từ `qiskit_optimization`

`qiskit-optimization` chỉ cung cấp `MinimumEigenOptimizer` (cái vỏ). Thuật toán QAOA nằm ở package
riêng `qiskit-algorithms`, không nằm trong dependency của `qiskit-optimization` — phải cài và import
từ đó.

### `AerError: unknown instruction: QAOA`

Aer `SamplerV2` **không** chạy trực tiếp được QAOA ansatz vì cần transpile về ISA trước. Với 8 qubit
(bằng đúng phạm vi đã khóa: K=3 trong 8 mã), `StatevectorSampler` là đủ — để `backends/hardware.py`
trống theo kế hoạch, không cần Aer transpile pipeline.

### `StrEnum` so sánh bằng `is` cho kết quả sai

`ArtifactMode("dev") == ArtifactMode.DEV` đúng, nhưng `"dev" is ArtifactMode.DEV` sai. Luôn ép kiểu
ở biên (`__post_init__`) rồi mới so sánh. Đã dính lỗi này một lần ở `paths.py`.

---

## 3. Pandas

Repo ghim `pandas>=2.2,<3` vì pandas 3 bật copy-on-write mặc định, khiến `df[col][idx] = x` **im
lặng không có tác dụng** (không báo lỗi, nhưng không sửa được dữ liệu). Dù đang ở pandas 2.x, vẫn nên
dùng `.loc` / `.assign()` thay vì chained indexing để không dính lỗi này khi nâng version sau này.

---

## 4. Lỗi tính toán/logic hay gặp

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| CVaR sau hedge **tăng** thay vì giảm | Lẫn dấu loss/return, hoặc quên phần tiền mặt trong tổng tỷ trọng |
| CVaR giảm bất thường nhiều | Chuyển quá nhiều sang tiền mặt, chưa trừ chi phí giao dịch |
| QAOA luôn trả bitstring vi phạm K=3 | Penalty `P` quá nhỏ so với `λ₁`, `λ₂` trong `configs/quantum.yaml` |
| QAOA objective tốt nhưng CVaR thật xấu | QUBO sai — chạy `verify/consistency.py`, đừng debug QAOA trước |
| Regime đảo nhãn giữa các lần chạy | Gán tên trạng thái theo state id thay vì theo đặc trưng thống kê (vi phạm quy tắc 7, `CLAUDE.md`) |
| HMM không hội tụ | Quá nhiều feature — giữ đúng 5, dùng `covariance_type: diag` |
| Kịch bản mất tương quan chéo giữa tài sản | Bootstrap từng tài sản độc lập thay vì lấy nguyên vector 8 tài sản mỗi ngày |
| Frontend hiển thị lệch field so với API | Quên chạy `npm run types` sau khi backend đổi schema response |

---

## 5. Vận hành / demo

### Streamlit/Next.js chết lúc demo

Dùng bản offline: `frontend/public/demo/` chứa snapshot JSON của một run đã kiểm chứng. Chuyển
frontend sang đọc từ nguồn này và nói rõ đây là dữ liệu cache, kèm timestamp — không trình bày như
real-time. Quy trình đầy đủ: `docs/runbook/demo_script.md` §8.

### QAOA timeout hoặc không có nghiệm hợp lệ

Fallback về exact/classical solver và gắn nhãn rõ solver thực tế đã dùng trong artifact/dashboard —
không được hiển thị như thể QAOA đã chạy thành công.

### Một module critical fail giữa pipeline

Artifact trước lỗi được giữ lại để debug, nhưng **không** được tạo final recommendation hay đổi
trạng thái run thành hoàn tất — theo `CLAUDE.md` quy tắc kiến trúc và
`docs/product/mvp_scope.md` BR-020.

---

## 6. Khi lỗi không nằm trong danh sách này

1. Xác định chặng nào trong pipeline sinh ra artifact sai
   (`docs/architecture/pipeline.md` §2) — không đoán, đọc `logs.txt` của `run_id` tương ứng.
2. Kiểm tra artifact đầu vào của chặng đó có đúng schema không
   (`docs/architecture/data_contracts.md`) — `validate_or_raise()` phải đã pass ở ranh giới trước.
3. Nếu liên quan đến QUBO/QAOA: luôn chạy lại `verify/consistency.py` trước khi nghi ngờ bất kỳ thứ
   gì khác.
4. Nếu vẫn không rõ nguyên nhân, ghi lại triệu chứng, `run_id`, config version vào đây sau khi xử lý
   xong, để lần sau không phải điều tra lại từ đầu.
