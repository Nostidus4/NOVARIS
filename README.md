# Q-SHIELD

**Quantum-AI Market Stress Digital Twin for Cash-Based Tail-Risk Mitigation**

Mô phỏng stress thị trường và tối ưu hành động phòng vệ bằng tiền mặt (QUBO / QAOA).

```text
Data (30 mã) → Regime → Scenarios → Risk (top 10) → QUBO 20-bit → Exact/QAOA
  → Rerank/Polish → CVaR after hedge → Dashboard
```

> Prototype dự thi — **không phải khuyến nghị đầu tư.** Xem [`docs/disclaimer.md`](docs/disclaimer.md).

**SoT sản phẩm:** [`docs/workflow-v2.md`](docs/workflow-v2.md)
**Quy tắc kỹ thuật:** [`CLAUDE.md`](CLAUDE.md)
**Profile duy nhất:** `workflow_update` (`NON_BASELINE_RUN` đến khi đủ 3 gate)

| | `workflow_update` |
|---|---|
| Universe | 30 mã VN30 snapshot |
| Risk | Dynamic top 10 |
| Hành động | 0 / 10 / 20 / 30% |
| QUBO | 20 bit (10 mã × 2 bit) |
| Config | `configs/base.yaml` + `configs/workflow_update.yaml` |

---

## Yêu cầu

| Công cụ | Phiên bản |
|---|---|
| Python | 3.14 (`uv` tự tải nếu thiếu) |
| [uv](https://docs.astral.sh/uv/) | ≥ 0.11 |
| Node.js | ≥ 20 (CI Pages dùng 24) |
| Yarn | 1.x (Classic) |
| Docker | tùy chọn — chạy FE + BE |

---

## Cài đặt nhanh

```bash
git clone <repo-url> QSHIELD && cd QSHIELD

# Python — 1 venv chung cho cả workspace (luôn chạy từ root)
uv sync --all-packages

# Frontend — Yarn (không dùng npm install)
cd frontend && yarn install && cd ..

# Kiểm tra
uv run python -c "import qiskit, hmmlearn, pandas; print(qiskit.__version__)"
uv run qshield-pipeline --help
```

Không tạo `.venv` riêng; không `uv sync` trong từng `packages/*`.

---

## Chạy ứng dụng

### Local

```bash
# Terminal 1 — API
uv run uvicorn qshield_api.main:app --reload --port 8000

# Terminal 2 — Console
cd frontend && yarn dev
```

- UI: http://localhost:3000
- API: http://localhost:8000/health
- OpenAPI: http://localhost:8000/docs

Env frontend (xem `frontend/README.md`):

- `QSHIELD_API_URL` — fetch phía server (mặc định `http://127.0.0.1:8000`)
- `NEXT_PUBLIC_QSHIELD_API_URL` — fetch phía browser

### Docker (FE + BE)

```bash
docker compose up --build
```

Mount `artifacts/`, `configs/`, `data/` vào backend. Chi tiết: `Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`.

---

## Pipeline & test

```bash
# Mock (schema giả — phát triển song song)
uv run qshield-pipeline all --config configs/base.yaml --mock

# Dữ liệu thật (cần data đã sẵn)
uv run qshield-pipeline all --config configs/base.yaml

# Test
uv run pytest
uv run pytest -m "not slow"          # bỏ QAOA nhiều seed
uv run pytest packages/risk          # theo package
uv run ruff check . && uv run ruff format .
uv run mypy packages backend

# Cổng bắt buộc trước khi tin kết quả QAOA
uv run pytest packages/quantum/tests/test_consistency.py -v
```

Pre-commit (một lần):

```bash
uv run pre-commit install
uv run pre-commit run --all-files   # chạy thử toàn repo
```

CI (`.github/workflows/ci.yml`): `pytest -m "not slow"` + consistency QUBO trên mỗi PR vào `main`.

---

## Cấu hình

Tất cả tham số trong `configs/` — không hard-code ticker / seed / ngưỡng trong code.

| File | Vai trò |
|---|---|
| `configs/base.yaml` | Universe, data, regime, scenarios, risk, quantum |
| `configs/workflow_update.yaml` | Profile vận hành 30 → top10 → 20-bit |

```python
from pathlib import Path
from qshield_contracts.config import Config

cfg = Config.load_profiled(
    Path("configs/base.yaml"),
    Path("configs/workflow_update.yaml"),
)
```

Artifact:

- `artifacts.mode: dev` → `artifacts/dev/` (lặp nhanh)
- `artifacts.mode: runs` → `artifacts/runs/<run_id>/` (có version)

Số liệu lên slide / UAT phải truy về một `run_id`. Chi tiết: [`configs/README.md`](configs/README.md).

---

## Cấu trúc repo

```text
QSHIELD/
├── packages/
│   ├── contracts/   # schema, paths, config, mock
│   ├── data/        # thu thập, làm sạch, feature
│   ├── ai/          # HMM regime + stress scenarios
│   ├── risk/        # CVaR, cost, top-N, rerank
│   ├── quantum/     # QUBO, exact, QAOA
│   └── pipeline/    # orchestrator
├── backend/         # FastAPI — đọc artifact, không công thức tài chính
├── frontend/        # Next.js + Tailwind (Yarn)
├── configs/         # base.yaml + workflow_update.yaml
├── data/            # dữ liệu thị trường
├── artifacts/       # output pipeline
├── docs/            # workflow-v2, disclaimer, folders/
├── notebooks/       # exploration — không chứa core logic
├── Dockerfile       # backend image
├── frontend/Dockerfile
└── docker-compose.yml
```

Context từng thư mục (cho agent / implement): [`docs/folders/`](docs/folders/README.md).

| Owner | Khu vực |
|---|---|
| Tân | contracts, quantum, pipeline, backend |
| Minh Anh | data |
| Tú | ai (regime / scenarios) |
| Phúc | risk (+ rerank/polish) |
| Ngọc | configs duyệt, frontend (+ Tân) |

---

## Tài liệu

| File | Nội dung |
|---|---|
| [`docs/workflow-v2.md`](docs/workflow-v2.md) | SoT sản phẩm / policy |
| [`docs/disclaimer.md`](docs/disclaimer.md) | Disclaimer bắt buộc |
| [`docs/folders/`](docs/folders/README.md) | Context theo thư mục |
| [`CLAUDE.md`](CLAUDE.md) | Quy tắc bất biến + bẫy kỹ thuật |
| [`frontend/README.md`](frontend/README.md) | Console pages & env |

Hợp đồng dữ liệu = schema trong `packages/contracts/src/qshield_contracts/schemas/` — không suy từ tên file.

---

## Stack đã kiểm chứng

Python **3.14** · qiskit **2.x** · FastAPI · Next.js 15/16 + Tailwind 4 · uv workspace.

qiskit 2.x **không** còn `qiskit.primitives.Sampler` (V1). Dùng:

```python
from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer
```

Chi tiết bẫy qiskit / pandas / StrEnum: mục tương ứng trong `CLAUDE.md`.

---

## Sự cố thường gặp

| Triệu chứng | Việc cần làm |
|---|---|
| `ModuleNotFoundError: qshield_*` | Thiếu `src/qshield_*/__init__.py` hoặc chưa `uv sync --all-packages` từ root |
| `conflicting Python requirements` | Tất cả `requires-python` phải `>=3.14,<3.15` |
| `qshield-*` command not found | Package chưa trong workspace members / chưa sync lại sau `[project.scripts]` |
| Frontend không gọi được API | Kiểm tra CORS + `QSHIELD_API_URL` / `NEXT_PUBLIC_QSHIELD_API_URL` |
| Docker backend build chậm / fail aer | Image cần compile `qiskit-aer` (đã có deps trong `Dockerfile`) — lần đầu lâu là bình thường |

Lỗi tài chính / quantum hay gặp: `CLAUDE.md` → **Lỗi hay gặp**. Checklist trước Quantum: `docs/workflow-v2.md` §15–17, §21.
