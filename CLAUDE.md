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

### Profile và config — đọc `configs/README.md` + `docs/workflow-v2.md`

SoT sản phẩm: **`docs/workflow-v2.md`**. Chỉ một profile vận hành:

- **`workflow_update`** (`configs/workflow_update.yaml`) — 30 mã VN30 → Risk **dynamic top 10**
  → Quantum **20-bit** (0/10/20/30%) → rerank/polish → dashboard/UAT.
  Status: `NON_BASELINE_RUN` đến khi đủ 3 gate (`data_gate`, `scenario_gate`, `product_gate`).
- **`base.yaml`** — tham số mặc định (universe/data/regime/scenarios/risk/quantum).

Load: `Config.load_profiled(Path("configs/base.yaml"), Path("configs/workflow_update.yaml"))`.

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
3. **Không forward-fill lợi suất.** Giá thiếu xử lý theo quy tắc trong `configs/base.yaml` và
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

> Scope SoT: `workflow_update` / `docs/workflow-v2.md` — 20-bit, top-10, 4 mức 0/10/20/30%
> (`quantum.mode: top10_four_level_actions`). Một số helper formulation nhị phân K-of-N vẫn còn
> trong `packages/quantum` cho verify/unit test; đường sản phẩm dùng four-level workflow.

14. **Formulation NumPy là ground truth cho QUBO đang chạy** — `QuadraticProgram`/QUBO convert
    phải khớp; four-level encoding theo `configs/workflow_update.yaml`.
15. **Chạy `verify/consistency.py` trước khi tin bất kỳ kết quả QAOA nào.** Ba cách tính lệch nhau
    ⇒ dừng, sửa formulation. Đừng debug QAOA khi QUBO còn sai.
16. **Exact solver là thước đo, không phải đối thủ.** Duyệt hết không gian (2^20 với 20-bit) là
    ground truth để chấm QAOA. Không bỏ để "tiết kiệm thời gian".
17. **Nghiệm QAOA phải chấm lại bằng true CVaR** qua `qshield_risk.evaluate` / rerank — không chọn
    chỉ theo QUBO energy. Rerank + local polishing (±5pp, zero-lock) là bắt buộc trên
    `workflow_update` (owner Phúc).
18. **Không tuyên bố quantum advantage.** QAOA thua exact hay classical thì báo cáo trung thực.

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

**Context chi tiết từng thư mục (cho agent):** `docs/folders/` — đọc file tương ứng trước khi sửa
code trong thư mục đó. Policy sản phẩm: `docs/workflow-v2.md`.

Trước khi sửa file trong `packages/X/`, đọc docstring đầu mỗi module — chúng mô tả trách nhiệm và
công thức cần hiện thực.

Baseline `workflow_update` thêm 2 chặng chưa có package tương ứng trong bảng trên: **rerank_polish**
(owner Phúc, hiện thực trong `packages/risk`) và **dashboard_uat** (owner Tân + Ngọc, trong
`backend/`+`frontend/`) — xem `configs/workflow_update.yaml` khóa `pipeline.stages` để biết
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
cd frontend && yarn dev
cd frontend && yarn types    # sinh lib/types.ts từ OpenAPI (nếu có script)
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
| `.../scenarios/stress_scenarios.npz` | `schemas/scenarios.py` | tensor `(S, H, N)` — `workflow_update`: `(2000\|5000, 20, 30)` |
| `.../risk/action_effects.csv` | `schemas/risk.py` | 1 dòng / action; có `candidate_top10.csv` trước bước này |

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

Baseline SoT: `docs/workflow-v2.md` + `configs/workflow_update.yaml` (30 → top-10 → 20-bit,
0/10/20/30%, rerank/polish). Vẫn `NON_BASELINE_RUN` đến khi đủ 3 approval gate.

**Vẫn không thêm** những thứ sau trừ khi người dùng yêu cầu rõ ràng:

- Chatbot
- Mô hình mới ngoài HMM + moving-block bootstrap
- CVAE (chỉ bật khi bootstrap đã pass toàn bộ check phân phối)
- Quantum hardware thật (`backends/hardware.py` cố ý để trống)
- Dữ liệu thời gian thực
- Biểu đồ ngoài 5 khu vực dashboard đã định
- Universe vượt quá 30 mã VN30 đã snapshot, hoặc action level ngoài 0/10/20/30%
- Profile / scope demo 8 mã song song (đã gỡ `demo_fast`)

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
| Frontend lệch field | Quên `yarn types` sau khi backend đổi schema |

---

## Bối cảnh

Prototype dự thi, **không phải sản phẩm tư vấn đầu tư**. Hệ thống mô tả kịch bản rủi ro, không đưa
khuyến nghị mua bán. Mọi kết luận phải nằm trong phạm vi bằng chứng mà artifact hỗ trợ. Giới hạn
ghi tại `docs/workflow-v2.md` §24, disclaimer tại `docs/disclaimer.md`.
