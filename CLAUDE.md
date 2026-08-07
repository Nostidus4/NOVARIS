# CLAUDE.md

Hướng dẫn cho Claude Code khi làm việc trên repository này.

---

## Dự án

Q-SHIELD — prototype dự thi, 5 người, 7 ngày. Mô phỏng stress thị trường và đề xuất hành động
phòng vệ bằng tiền mặt, tối ưu bằng QUBO/QAOA.

Pipeline đầy đủ (baseline `workflow_update`):

```
Data (30 mã) → Regime → Scenarios → Risk (chọn dynamic top 10) → QUBO (20-bit) → Exact/QAOA
  → Rerank/Polish → CVaR after hedge → Dashboard/UAT
```

### Hai profile — đọc `configs/profiles/README.md` trước khi hiểu mục này

Từ **2026-08-06, team đã thống nhất chốt** `workflow_update` làm baseline sản phẩm chính thức,
thay cho việc chỉ tạm khóa vĩnh viễn ở 8 mã. Hai profile khai báo máy đọc được ở
`configs/profiles/`:

- **`workflow_update`** (`configs/profiles/workflow_update.yaml`, status `BASELINE_TARGET`) — **đích
  chính thức**: 30 mã VN30 (universe) → Risk chọn **dynamic top 10** theo net risk score → Quantum
  **20-bit** (2 bit/mã × 10 mã, 4 mức hành động 0/10/20/30%) → **rerank + local polishing** (owner
  Phúc) → dashboard/UAT. Cần 3 approval gate (`data_gate`/Minh Anh, `scenario_gate`/Phúc,
  `product_gate`/Ngọc) trước khi được dùng làm baseline/UAT chính thức — xem file yaml để biết đủ
  output bắt buộc từng gate.
- **`demo_fast`** (`configs/profiles/demo_fast.yaml`, status `NON_BASELINE_RUN`) — scope thu gọn
  cho debug/demo nhanh: 8 mã cố định, cả 8 mã đưa thẳng vào Quantum (không chọn top 10), QUBO
  **8-bit** chọn đúng K=3, một mức hành động duy nhất (giảm 20%). **Đây là scope mà `packages/*`
  hiện đang hiện thực** (kể cả `packages/quantum`, `packages/pipeline`) — `workflow_update` vẫn
  đang trong quá trình nâng cấp lên, chưa code xong. Không xóa `demo_fast` khi nâng cấp — nó vẫn
  cần cho vòng lặp dev/debug nhanh và integration smoke test.

**Không được trộn số liệu hai profile trong cùng một báo cáo/so sánh.** Run `demo_fast` luôn gắn
`profile_id=demo_fast` và báo cáo `NON_BASELINE_RUN`. Quy tắc "Quantum" bên dưới (14-18) mô tả công
thức của scope `demo_fast` (code hiện tại) — khi nâng cấp lên `workflow_update`, các công thức đó
phải viết lại cho đúng 20-bit/4-mức và mục này phải cập nhật theo, chưa được coi là xong chỉ vì đã
đổi config.

**Stack:** uv workspace (7 member), Python 3.14, FastAPI, Next.js 15 + Tailwind, qiskit 2.x.

---

## Quy tắc bất **biến**

Vi phạm những điều dưới đây làm sai kết quả, không chỉ làm xấu code. Nếu một yêu cầu buộc phải
vi phạm, hãy dừng và nói ra thay vì âm thầm làm.

### Tài chính

1. **Quy ước dấu:** `L_s = -R^(H)_{p,s}`. Loss dương = lỗ. CVaR tính trên phân phối **loss**,
   không phải return. CVaR cao = xấu. Mọi so sánh trước–sau phải cùng quy ước.
2. **CVaR:** `VaR_α = Q_α(L)`, `CVaR_α = E[L | L ≥ VaR_α]`, α = 0.95 (Rockafellar–Uryasev).
   Đây là trung bình phần đuôi, **không phải** giá trị tại phân vị.
3. **Không forward-fill lợi suất.** Giá thiếu xử lý theo quy tắc trong `configs/data.yaml` và
   phải ghi log. Không bao giờ `.ffill()` trên cột return.
4. **Không dùng dữ liệu tương lai.** Mọi rolling feature chỉ dùng dữ liệu đến `t`. Scaler `fit`
   **chỉ** trên train rồi `transform` cho validation và test.
5. **Không tự xóa outlier.** Gắn cờ và báo cáo.
6. **Tổng tỷ trọng luôn bằng 1.0** sau mọi hành động, kể cả phần tiền mặt.
7. **Đặt tên regime theo đặc trưng thống kê**, không theo state id. HMM trả state 0/1/2 theo thứ
   tự ngẫu nhiên tùy seed. Phải xếp hạng theo return/volatility/drawdown rồi mới gán
   Normal/Volatile/Stress. Giả định "state 0 = Normal" là bug im lặng.

### Kiến trúc

8. **Không hard-code** đường dẫn, ticker, seed, ngày, ngưỡng. Tất cả nằm trong `configs/*.yaml`,
   đọc qua `qshield_contracts.config.Config`. Đường dẫn artifact **chỉ** sinh từ
   `qshield_contracts.paths.ArtifactPaths` — không nối chuỗi path ở nơi khác.
9. **Backend không chứa công thức tài chính.** `backend/` gọi `qshield_risk` / `qshield_quantum`
   hoặc đọc artifact. Một dòng tính CVaR trong `routers/` là bug, kể cả khi ra số đúng.
10. **Frontend không chứa logic tài chính.** Chỉ hiển thị số backend trả về.
11. **Chiều phụ thuộc một chiều:**
    ```
    contracts ← data, ai, risk, quantum
    risk      ← quantum      (exact solver cần true CVaR — import chéo DUY NHẤT được phép)
    tất cả    ← pipeline ← backend ← frontend (qua HTTP)
    ```
    Cần mũi tên ngược nghĩa là hợp đồng dữ liệu đang thiếu gì đó — sửa `contracts`, đừng import tắt.
12. **Validate ở mọi ranh giới module.** Gọi `validate_or_raise()` cho cả input lẫn output.
    Fail fast tại chỗ, không để dữ liệu sai trôi xuống ba tầng.
13. **Chỉ `RunContext` được ghi** `config.json`, `data_version.json`, `metrics.json`, `logs.txt`.
    Module tính toán trả về dữ liệu, không tự ghi metadata.

### Quantum

> Quy tắc 14-16 dưới đây mô tả đúng code **hiện tại** — scope `demo_fast` (8-bit, K=3 trong 8 mã).
> Baseline `workflow_update` (20-bit, top-10, 4 mức hành động 0/10/20/30%) cần công thức khác —
> `g`/`C`/`c` không còn là hệ số nhị phân đơn giản mà phải tham số hóa theo 4 mức mỗi mã, và ràng
> buộc không còn là "đúng K trong N" mà theo `configs/profiles/workflow_update.yaml` (`quantum.mode:
> top10_four_level_actions`). Việc viết lại `formulation/` cho 20-bit **chưa thực hiện** — khi làm,
> phải cập nhật lại mục này cho khớp, không được để CLAUDE.md mô tả sai code thật.

14. **`formulation/objective.py` là ground truth** (scope `demo_fast`). Hàm NumPy thuần định nghĩa
    `f(z) = −g'z + λ₁·z'Cz + λ₂·c'z + P·(Σz − K)²`. `QuadraticProgram` và QUBO sau convert phải
    khớp với nó.
15. **Chạy `verify/consistency.py` trước khi tin bất kỳ kết quả QAOA nào.** Ba cách tính lệch nhau
    ⇒ dừng, sửa formulation. Đừng debug QAOA khi QUBO còn sai.
16. **Exact solver là thước đo, không phải đối thủ.** Duyệt hết không gian trạng thái (256 với
    8-bit `demo_fast`; 1.048.576 với 20-bit `workflow_update`) là ground truth để chấm QAOA. Không
    bỏ để "tiết kiệm thời gian".
17. **Nghiệm QAOA phải chấm lại bằng true CVaR** qua `qshield_risk.evaluate`, không phải bằng giá
    trị objective. Objective thấp mà CVaR thực tế không giảm thì nghiệm vô nghĩa. Ở `workflow_update`
    bước này là "rerank" bắt buộc (owner Phúc), theo sau bởi "local polishing" (±5pp, khóa
    zero-action) — cả hai chưa hiện thực trong `packages/risk`.
18. **Không tuyên bố quantum advantage.** QAOA thua exact hay thua classical thì báo cáo trung
    thực. Đây là yêu cầu nghiệm thu, áp dụng cho cả hai profile.

---

## Bẫy kỹ thuật đã xác minh

Những điều dưới đây đã test thật trên Python 3.14.4, không phải suy đoán.

### qiskit là 2.x — API khác hẳn 1.x

`qiskit.primitives.Sampler` (primitive V1) **đã bị xóa**. Mọi ví dụ QAOA trên mạng viết cho 1.x
sẽ chết ngay dòng import.

```python
# SAI — ImportError trên qiskit 2.x
from qiskit.primitives import Sampler

# ĐÚNG — đã test, ra nghiệm khớp exact solver
from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer

sampler = StatevectorSampler(default_shots=1024, seed=seed)
qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=200), reps=1)
result = MinimumEigenOptimizer(qaoa).solve(qubo)
```

### `qiskit-algorithms` là package riêng

`qiskit-optimization` chỉ cung cấp `MinimumEigenOptimizer` (cái vỏ). Thuật toán QAOA nằm ở
`qiskit-algorithms` và **không** nằm trong dependency của qiskit-optimization.

### Aer SamplerV2 không chạy trực tiếp QAOA ansatz

`AerError: 'unknown instruction: QAOA'` — Aer V2 chỉ nhận mạch đã transpile về ISA. Với 8 qubit,
dùng `StatevectorSampler`; để `backends/hardware.py` trống theo kế hoạch.

### StrEnum so sánh bằng `is` sẽ sai

`ArtifactMode("dev") == ArtifactMode.DEV` đúng, nhưng `"dev" is ArtifactMode.DEV` sai. Luôn ép
kiểu ở biên (`__post_init__`) rồi mới so sánh. Đã dính lỗi này một lần ở `paths.py`.

### pandas ghim dưới 3.0

Repo ghim `pandas>=2.2,<3` vì pandas 3 bật copy-on-write mặc định, khiến `df[col][idx] = x` im
lặng không có tác dụng. Dù vậy vẫn nên dùng `.loc` / `.assign`.

---

## Bản đồ repo

| Đường dẫn | Nội dung | Owner |
|---|---|---|
| `packages/contracts/` | Schema, đường dẫn, config, run context, mock | Tân |
| `packages/data/` | Thu thập, làm sạch, feature, split, quality | Minh Anh |
| `packages/ai/` | HMM regime + sinh kịch bản stress | Tú |
| `packages/risk/` | CVaR, drawdown, chi phí, `g`/`C`/`c` | Phúc |
| `packages/quantum/` | QUBO, exact solver, QAOA, benchmark | Tân |
| `packages/pipeline/` | Orchestrator end-to-end | Tân |
| `backend/` | FastAPI, chỉ đọc artifact | Tân |
| `frontend/` | Next.js 15 + Tailwind, 5 trang | Ngọc + Tân |
| `configs/` | Toàn bộ tham số | Ngọc duyệt |

Trước khi sửa file trong `packages/X/`, đọc docstring đầu mỗi module — chúng mô tả trách nhiệm và
công thức cần hiện thực.

Baseline `workflow_update` thêm 2 chặng chưa có package tương ứng trong bảng trên: **rerank_polish**
(owner Phúc, hiện thực trong `packages/risk`) và **dashboard_uat** (owner Tân + Ngọc, trong
`backend/`+`frontend/`) — xem `configs/profiles/workflow_update.yaml` khóa `pipeline.stages` để biết
input/output từng chặng.

---

## Lệnh

```bash
uv sync --all-packages          # cài toàn bộ, 1 venv chung

uv run qshield-pipeline all --config configs/base.yaml --mock   # chạy trên dữ liệu giả
uv run qshield-pipeline all --config configs/base.yaml          # dữ liệu thật

uv run pytest                   # test
uv run pytest -m "not slow"     # bỏ QAOA nhiều seed
uv run ruff check . && uv run ruff format .
uv run mypy packages backend

uv run uvicorn qshield_api.main:app --reload --port 8000
cd frontend && npm run dev
cd frontend && npm run types    # sinh lib/types.ts từ OpenAPI
```

Thêm dependency cho một package cụ thể:

```bash
uv add --package qshield-risk "scipy>=1.14"
```

Không `pip install`. Không tạo virtualenv riêng.

---

## Hợp đồng dữ liệu

Định nghĩa nằm trong code tại `packages/contracts/src/qshield_contracts/schemas/`, không trong tài
liệu. Cần biết artifact có cột gì thì đọc schema, đừng suy đoán từ tên file.

| Artifact | Schema | Hình dạng |
|---|---|---|
| `data/processed/returns.parquet` | `schemas/returns.py` | long format (date, ticker) |
| `data/processed/features.parquet` | `schemas/features.py` | 1 dòng / ngày |
| `.../regime/regime_daily.parquet` | `schemas/regime.py` | 1 dòng / ngày + 3 xác suất |
| `.../scenarios/stress_scenarios.npz` | `schemas/scenarios.py` | tensor `(S, 20, N)` — `demo_fast`: `(500, 20, 8)`; `workflow_update`: `(2000\|5000, 20, 30)` |
| `.../risk/action_effects.csv` | `schemas/risk.py` | 1 dòng / action (`demo_fast`); `workflow_update` thêm `candidate_top10.csv` trước bước này |
| `.../optimization/qaoa_result.json` | `schemas/optimization.py` | bitstring + metrics |

Đổi schema là breaking change: sửa `contracts` trước, rồi sửa cả bên ghi lẫn bên đọc trong cùng
một PR.

---

## Phát triển song song

Cả 5 người bắt đầu từ ngày 1 trên **mock**, không ai chờ ai. `contracts/mocks/` sinh dữ liệu giả
đúng schema. Khi dữ liệu thật xong thì chỉ đổi nguồn.

Khi viết module mới, luôn nhận dữ liệu qua tham số hoặc qua `ArtifactPaths` — đừng giả định file
thật đã có trên đĩa.

---

## Đóng băng phạm vi

**Đã bỏ khỏi danh sách đóng băng (2026-08-06, team thống nhất):** mở rộng lên 30 mã VN30 → Risk
chọn dynamic top 10 → Quantum 20-bit, 4 mức hành động 0/10/20/30%, có rerank/local polishing. Đây
giờ là baseline chính thức `workflow_update` (`configs/profiles/workflow_update.yaml`), không còn
bị coi là mở rộng ngoài phạm vi — nhưng vẫn cần qua đủ 3 approval gate của profile đó trước khi dùng
làm bằng chứng UAT/baseline. `demo_fast` (8 mã) **không bị xóa** — vẫn giữ nguyên cho debug/demo
nhanh, luôn gắn `profile_id=demo_fast` khi báo cáo.

**Vẫn không thêm** những thứ sau trừ khi người dùng yêu cầu rõ ràng:

- Chatbot
- Mô hình mới ngoài HMM + moving-block bootstrap
- CVAE (chỉ bật khi bootstrap đã pass toàn bộ check phân phối)
- Quantum hardware thật (`backends/hardware.py` cố ý để trống)
- Dữ liệu thời gian thực
- Biểu đồ ngoài 5 khu vực dashboard đã định
- Universe vượt quá 30 mã VN30 đã snapshot (`configs/profiles/workflow_update.yaml`), hoặc bất kỳ
  action level nào ngoài 0/10/20/30%

Cổng nghiệm thu cuối ngày 4 chưa đạt ⇒ mọi việc trên dừng vô điều kiện, tập trung tích hợp.

---

## Quy ước code

- Python 3.14, `ruff` (line-length 100), type hint ở mọi hàm public.
- Ưu tiên hàm thuần và mảng NumPy. Truyền tham số tường minh, không dùng biến toàn cục.
- Ngẫu nhiên: nhận `seed` từ config, tạo `np.random.default_rng(seed)` cục bộ. Không
  `np.random.seed()` toàn cục.
- Lỗi: raise exception có ngữ cảnh (giá trị nào, file nào, module nào). Không `except: pass`.
- Không `print()` trong package — dùng `logging` qua `RunContext.logger()`. `print` chỉ trong
  `cli.py`.
- Test: mỗi công thức tài chính cần một test so với ví dụ tính tay. `packages/risk/tests/` là
  test suite quan trọng nhất repo.
- Tiếng Việt trong docstring và comment được, tên biến và tên hàm dùng tiếng Anh.

---

## Lỗi hay gặp

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| CVaR sau hedge **tăng** | Lẫn dấu loss/return, hoặc quên phần tiền mặt trong tỷ trọng |
| CVaR giảm bất thường | Chuyển quá nhiều sang tiền mặt, chưa trừ chi phí giao dịch |
| QAOA luôn trả bitstring vi phạm K | `penalty` P quá nhỏ so với λ₁, λ₂ |
| QAOA objective tốt, CVaR thật xấu | QUBO sai — chạy `verify/consistency.py` |
| Regime đảo nhãn giữa các lần chạy | Gán tên theo state id thay vì thống kê (quy tắc 7) |
| HMM không hội tụ | Quá nhiều feature. Giữ đúng 5, dùng `covariance_type: diag` |
| Kịch bản mất tương quan chéo | Bootstrap từng tài sản độc lập. Phải lấy nguyên vector 8 tài sản mỗi ngày |
| `ModuleNotFoundError: qshield_*` | Thiếu `src/<module>/__init__.py`, `uv_build` bắt buộc có |
| `conflicting Python requirements` | `requires-python` giữa root và member lệch nhau |
| Frontend lệch field | Quên `npm run types` sau khi backend đổi schema |

---

## Bối cảnh

Prototype dự thi, **không phải sản phẩm tư vấn đầu tư**. Hệ thống mô tả kịch bản rủi ro, không đưa
khuyến nghị mua bán. Mọi kết luận phải nằm trong phạm vi bằng chứng mà artifact hỗ trợ. Giới hạn
ghi tại `docs/limitations.md`, disclaimer tại `docs/product/disclaimer.md`.
