# Q-SHIELD

**Quantum-AI Market Stress Digital Twin for Cash-Based Tail-Risk Mitigation**

Q-SHIELD mô phỏng thị trường chứng khoán Việt Nam trong trạng thái căng thẳng, rồi tìm hành động phòng
vệ bằng tiền mặt (bán bớt 0/10/20/30% từng mã) để giảm rủi ro đuôi CVaR. Bài toán chọn hành động được
viết dưới dạng QUBO và giải bằng exact solver (thước đo chuẩn) và QAOA (thử nghiệm).

```text
Data 30 mã VN30 → Regime (HMM) → Scenarios (block bootstrap) → Risk (chọn top 10)
  → QUBO 20-bit → Exact / QAOA → Rerank + Polish (true CVaR) → Dashboard
```

> Prototype dự thi của nhóm 5 người — **không phải khuyến nghị đầu tư.** Xem
> [`docs/disclaimer.md`](docs/disclaimer.md). QAOA chạy trên simulator; dự án **không** tuyên bố
> quantum advantage.

|                  |                                                                    |
| ---------------- | ------------------------------------------------------------------ |
| SoT sản phẩm     | [`docs/workflow-v2.md`](docs/workflow-v2.md)                       |
| Quy tắc kỹ thuật | [`CLAUDE.md`](CLAUDE.md) — quy tắc bất biến và bẫy đã xác minh     |
| Profile          | `workflow_update` — `NON_BASELINE_RUN` đến khi đủ 3 gate (data, scenario, product) |

---

## Bắt đầu

**Cần:** [uv](https://docs.astral.sh/uv/) ≥ 0.11 (tự tải Python 3.14), Node.js ≥ 20 + Yarn 1.x,
Docker (tuỳ chọn).

```bash
git clone <repo-url> QSHIELD && cd QSHIELD
uv sync --all-packages                    # 1 venv chung cho cả workspace, chạy từ root
cd frontend && yarn install && cd ..
```

Không `pip install`, không tạo venv riêng, không `uv sync` trong từng `packages/*`.

### Dữ liệu

Giá 30 mã lấy từ file export **FiinPro** `data/raw/Full_Prices.xlsx`. Đây là dữ liệu thương mại nên
**không có trong repo** (repo public) — xin file từ Data owner rồi đặt đúng đường dẫn đó. VN-Index tải
qua vnstock nên cần internet.

```bash
uv run qshield-data build     # tách giá → làm sạch → returns/features → eligibility → split → DQ gate
```

Kết quả nằm ở `data/processed/*.parquet` (gitignored) và `reports/data_quality_report.csv`.
Không có file FiinPro thì vẫn phát triển được bằng mock: `uv run qshield-pipeline all --mock`.

Lưu ý khi dùng dữ liệu: `adjusted_close` của FiinPro **đã điều chỉnh sẵn** mọi corporate action và neo
theo ngày export — không back-adjust thêm, không dùng làm giá hiện tại (dùng `close`). Chi tiết:
[`docs/data/2026-09-17-chuyen-nguon-gia-fiinpro.md`](docs/data/2026-09-17-chuyen-nguon-gia-fiinpro.md).

---

## Chạy pipeline

```bash
# Toàn bộ workflow_update trên dữ liệu đã build (quantum mặc định = exact)
uv run qshield-pipeline workflow-update --profile configs/workflow_update.yaml
uv run qshield-pipeline workflow-update --profile configs/workflow_update.yaml --quantum-mode qaoa

# Từng chặng (debug)
uv run qshield-ai regime    --profile configs/workflow_update.yaml
uv run qshield-ai scenarios --profile configs/workflow_update.yaml
uv run qshield-risk --help
uv run qshield-quantum --help
```

Mặc định ghi vào `artifacts/dev/` (lặp nhanh). Đặt `artifacts.mode: runs` để ghi
`artifacts/runs/<run_id>/` có version — mọi số lên slide/UAT phải truy về một `run_id`.

Scenario gate FAIL thì cube **không** được ghi. `--force` chỉ dùng khi owner đã quyết định có chủ ý.

### Thí nghiệm hybrid (QAOA-assisted candidate generation)

Track nghiên cứu tách khỏi pipeline sản phẩm: QAOA sinh ứng viên, Risk chấm lại bằng true CVaR, so với
các baseline classical/random. Mỗi thay đổi protocol hoặc dữ liệu là một `experiment_id` mới trong
`configs/experiments/hybrid_v*.yaml`; manifest được khoá bằng hash trước khi chạy.

```bash
# Thứ tự bắt buộc; thay hybrid_v4.yaml bằng experiment đang chạy
uv run qshield-pipeline hybrid-manifest --experiment configs/experiments/hybrid_v4.yaml --set exploratory
uv run qshield-pipeline hybrid-manifest --experiment configs/experiments/hybrid_v4.yaml --set confirmation
uv run qshield-pipeline hybrid-run      --experiment configs/experiments/hybrid_v4.yaml --set exploratory --full-only
uv run qshield-pipeline hybrid-transfer --experiment configs/experiments/hybrid_v4.yaml
uv run qshield-pipeline hybrid-run      --experiment configs/experiments/hybrid_v4.yaml --set exploratory --no-resume
uv run qshield-pipeline hybrid-report   --experiment configs/experiments/hybrid_v4.yaml --set exploratory
uv run qshield-pipeline hybrid-run      --experiment configs/experiments/hybrid_v4.yaml --set confirmation
uv run qshield-pipeline hybrid-report   --experiment configs/experiments/hybrid_v4.yaml --set confirmation
```

Kế hoạch và gate H1–H6: [`docs/hybrid/2026-09-13-plan-qaoa-assisted.md`](docs/hybrid/2026-09-13-plan-qaoa-assisted.md).

---

## Chạy ứng dụng

```bash
uv run uvicorn qshield_api.main:app --reload --port 8000   # API — http://localhost:8000/docs
cd frontend && yarn dev                                     # Console — http://localhost:3000
```

Frontend đọc `QSHIELD_API_URL` (phía server, mặc định `http://127.0.0.1:8000`) và
`NEXT_PUBLIC_QSHIELD_API_URL` (phía browser) — xem [`frontend/README.md`](frontend/README.md).

Docker: `docker compose up --build` (mount `artifacts/`, `configs/`, `data/` vào backend).

---

## Test và chất lượng code

```bash
uv run pytest -m "not slow"          # bỏ QAOA nhiều seed
uv run pytest packages/risk          # theo package — risk là test suite quan trọng nhất
uv run pytest packages/quantum/tests/test_verify_consistency.py -v   # bắt buộc trước khi tin QAOA
uv run ruff check . && uv run ruff format .
uv run mypy packages backend
uv run pre-commit install            # một lần
```

CI (`.github/workflows/ci.yml`) chạy `pytest -m "not slow"` và consistency QUBO trên mỗi PR vào `main`.

---

## Cấu trúc repo

```text
QSHIELD/
├── packages/            # uv workspace — chiều phụ thuộc một chiều, xem CLAUDE.md quy tắc 11
│   ├── contracts/       # schema, ArtifactPaths, Config, RunContext, mock
│   ├── data/            # FiinPro + VN-Index → returns, features, eligibility, DQ gate
│   ├── ai/              # HMM regime + moving-block bootstrap scenarios
│   ├── risk/            # CVaR, chi phí, chọn top 10, rerank/polish
│   ├── quantum/         # QUBO, exact solver, QAOA, verify consistency
│   └── pipeline/        # orchestrator end-to-end + thí nghiệm hybrid
├── backend/             # FastAPI — chỉ đọc artifact, không chứa công thức tài chính
├── frontend/            # Next.js + Tailwind console — chỉ hiển thị số backend trả về
├── configs/             # base.yaml, workflow_update.yaml, experiments/hybrid_v*.yaml
├── data/                # raw (FiinPro, gitignored) · processed (gitignored) · metadata
├── artifacts/           # dev/ · runs/<run_id>/ · jobs/
├── reports/             # DQ report, evidence, UAT
└── docs/                # workflow-v2, disclaimer, folders/, decisions/, reviews/, data/, hybrid/
```

Mọi tham số (ticker, seed, ngày, ngưỡng, đường dẫn) nằm trong `configs/` — không hard-code trong code.
Hợp đồng dữ liệu là schema trong `packages/contracts/src/qshield_contracts/schemas/`.
Context từng thư mục cho người/agent sửa code: [`docs/folders/`](docs/folders/README.md).

| Owner    | Khu vực                                   |
| -------- | ----------------------------------------- |
| Tân      | contracts, quantum, pipeline, backend     |
| Minh Anh | data (Mạnh hỗ trợ nguồn FiinPro)          |
| Tú       | ai (regime, scenarios)                    |
| Phúc     | risk, rerank/polish                       |
| Ngọc     | duyệt configs, frontend (cùng Tân)        |

---

## Tài liệu

| File | Nội dung |
| --- | --- |
| [`docs/workflow-v2.md`](docs/workflow-v2.md) | SoT sản phẩm, policy, giới hạn (§24) |
| [`CLAUDE.md`](CLAUDE.md) | Quy tắc bất biến, bẫy qiskit 2.x / pandas / FiinPro, lỗi hay gặp |
| [`configs/README.md`](configs/README.md) | Cách load profile và override |
| [`docs/README.md`](docs/README.md) | Mục lục toàn bộ tài liệu: decisions, reviews, data, hybrid |
| [`docs/disclaimer.md`](docs/disclaimer.md) | Disclaimer bắt buộc |

---

## Sự cố thường gặp

| Triệu chứng | Việc cần làm |
| --- | --- |
| `Không thấy file FiinPro data/raw/Full_Prices.xlsx` | Xin file từ Data owner; hoặc chạy `--mock` |
| `VN-Index thiếu N phiên` khi `qshield-data fetch` | Mạng/API vnstock lỗi — chạy lại; không bỏ qua (sẽ xoá nhầm giá thật) |
| `ModuleNotFoundError: qshield_*` | `uv sync --all-packages` từ root; kiểm tra `src/qshield_*/__init__.py` |
| `conflicting Python requirements` | Mọi `requires-python` phải là `>=3.14,<3.15` |
| `ImportError: Sampler` | qiskit 2.x đã bỏ V1 — dùng `StatevectorSampler` (xem CLAUDE.md) |
| Scenario gate FAIL | Xem `artifacts/dev/scenarios/scenario_validation.csv`; ngưỡng do Phúc quyết |
| Frontend không gọi được API | Kiểm tra CORS và `QSHIELD_API_URL` / `NEXT_PUBLIC_QSHIELD_API_URL` |

Lỗi tài chính/quantum (CVaR tăng sau hedge, QAOA vi phạm ràng buộc…): `CLAUDE.md` → **Lỗi hay gặp**.
