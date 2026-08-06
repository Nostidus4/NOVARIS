# Q-SHIELD

**Quantum-AI Market Stress Digital Twin for Cash-Based Tail-Risk Mitigation**

Hệ thống mô phỏng kịch bản stress thị trường và đề xuất hành động phòng vệ bằng tiền mặt,
tối ưu lựa chọn hành động bằng QUBO/QAOA.

```
Data → Regime → Scenarios → Risk → QUBO → Exact/QAOA → CVaR after hedge
```

> Prototype dự thi. **Không phải khuyến nghị đầu tư.** Xem `docs/product/disclaimer.md`.

---

## Profile: `demo_fast` vs `workflow_update`

**2026-08-06 — team đã thống nhất chốt `workflow_update` làm baseline sản phẩm chính thức.**
Repo có hai profile khai báo tường minh ở `configs/profiles/` — không được trộn số liệu của hai
profile trong cùng một báo cáo/so sánh.

| | `demo_fast` | `workflow_update` |
|---|---|---|
| Trạng thái | `NON_BASELINE_RUN` — chỉ để demo/debug | `BASELINE_TARGET` — baseline sản phẩm/UAT sau khi owner duyệt |
| Universe | 8 mã cố định | 30 mã VN30 snapshot |
| Risk candidate | Cả 8 mã đưa thẳng vào Quantum | Risk chọn **dynamic top 10** từ 30 mã |
| Hành động | 1 mức: giảm 20% | 4 mức: 0/10/20/30% |
| QUBO | 8 bit, chọn đúng K=3 | 20 bit (10 mã × 2 bit) |
| Rerank/polish sau QAOA | Không có trong phạm vi này | Bắt buộc (owner: Phúc) |

**Toàn bộ code hiện tại trong `packages/*` (kể cả phần đã hiện thực ở `packages/quantum` và
`packages/pipeline`) vẫn đang chạy theo scope `demo_fast`** — chưa bắt kịp baseline vừa chốt.
`workflow_update` giờ là đích chính thức (không còn là "thiết kế gốc gác lại"), nhưng code cho 30
mã/top-10/20-bit/4-mức-hành-động/rerank-polish **chưa được viết** — đây là phần việc còn lại của cả
5 package (`data`, `ai`, `risk`, `quantum`, `pipeline`), không phải chỉ đổi config.
Đừng lấy số chạy `--mock`/8-mã hiện tại để tuyên bố đã đạt `workflow_update`.

Chi tiết đầy đủ, governance, ai duyệt gì trước khi công bố: `configs/profiles/README.md`,
`configs/profiles/demo_fast.yaml`, `configs/profiles/workflow_update.yaml`. Bối cảnh lịch sử vì
sao có hai scope: `docs/limitations.md` §1.

---

## Vừa clone repo về? Làm theo đúng thứ tự này

### Bước 0 — Yêu cầu công cụ

| Công cụ | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.14 | `uv` tự tải nếu máy chưa có |
| uv | ≥ 0.11 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | ≥ 20 | cho frontend |

### Bước 1 — Cài đặt

```bash
git clone <repo-url> QSHIELD && cd QSHIELD

# Backend + toàn bộ package Python (1 lệnh, 1 venv chung cho cả 7 workspace member)
uv sync --all-packages

# Frontend
cd frontend && npm install && cd ..
```

Không ai tự tạo virtualenv riêng, không `cd` vào `packages/*` hay `backend/` để `uv sync` — luôn
chạy từ thư mục gốc.

### Bước 2 — Kiểm tra cài đặt thành công

```bash
uv run python -c "import qiskit, hmmlearn, pandas; print(qiskit.__version__)"
uv run qshield-pipeline --help
```

Lệnh thứ hai phải in ra help text của CLI (không lỗi `command not found`). Nếu lỗi, xem mục
"Sự cố thường gặp" bên dưới.

### Bước 3 — Chạy thử để thấy pipeline sống

```bash
uv run qshield-pipeline all --config configs/base.yaml --mock
```

`--mock` sinh dữ liệu giả đúng schema từ `qshield_contracts.mocks`, dùng khi module phía trên
trong pipeline chưa implement xong — cả 5 người phát triển song song được nhờ đường này, không
ai phải chờ ai. (Lưu ý: tại thời điểm này phần lớn `packages/*/src` còn là scaffold — lệnh này sẽ
chạy đến đúng chỗ chưa implement thì dừng với `NotImplementedError`, đó là kỳ vọng bình thường,
không phải bạn cài sai.)

### Bước 4 — Đọc 4 tài liệu này trước khi viết bất kỳ dòng code nào

| Tài liệu | Trả lời câu hỏi gì |
|---|---|
| `CLAUDE.md` | Quy tắc kỹ thuật bất biến — vi phạm làm **sai kết quả**, không chỉ xấu code |
| `docs/Structure.md` | Thư mục này để làm gì, ai phụ trách (mục 1.1 có bảng tổng quan nhanh) |
| `docs/limitations.md` | Giới hạn đã biết — để không tuyên bố vượt quá bằng chứng |
| `docs/product/disclaimer.md` | Nội dung bắt buộc phải hiển thị ở mọi kết quả/báo cáo |

### Bước 5 — Tìm đúng phần việc của bạn

Mọi file `.py`/`.yaml` còn là scaffold đều có một dòng comment đầu file dạng
`# Tên người - nhiệm vụ`. Tìm phần của mình bằng:

```bash
grep -rl "Tên bạn" packages/ backend/ configs/ --include="*.py" --include="*.yaml"
```

Muốn xem bức tranh tổng thể ai làm phần nào: `docs/Structure.md` §4 (phân công chi tiết) và §5
(bảng RACI).

### Bước 6 — Chạy test cho phần bạn phụ trách

```bash
uv run pytest packages/<tên-package>     # ví dụ: uv run pytest packages/risk
uv run ruff check . && uv run ruff format .
uv run mypy packages backend
```

Nếu bạn động vào bất kỳ thứ gì trong `packages/quantum/`, **cổng chặn bắt buộc** trước khi tin kết
quả QAOA:

```bash
uv run pytest packages/quantum/tests/test_consistency.py -v
```

### Bước 7 — Khi cần chạy cả app (backend + frontend)

```bash
uv run uvicorn qshield_api.main:app --reload --port 8000   # backend :8000
cd frontend && npm run dev                                  # frontend :3000
```

Sau khi backend chạy, và mỗi khi backend đổi schema response:

```bash
cd frontend && npm run types
```

`frontend/lib/types.ts` sinh tự động từ `/openapi.json`. **Không sửa tay, không commit sai lệch.**

### Bước 8 — Bật pre-commit (làm một lần)

```bash
uv run pre-commit install
```

Từ lúc này, mỗi lần `git commit` sẽ tự động chạy các hook khai báo trong `.pre-commit-config.yaml`:

| Hook | Làm gì |
|---|---|
| `ruff-check --fix` | Tự sửa lỗi lint sửa được |
| `ruff-format` | Tự format lại code theo `line-length 100` |
| `trailing-whitespace` | Xóa khoảng trắng cuối dòng |
| `end-of-file-fixer` | Đảm bảo file kết thúc bằng đúng 1 dòng trống |
| `check-yaml` / `check-toml` | Báo lỗi nếu `configs/*.yaml` hoặc `pyproject.toml` sai cú pháp |
| `check-added-large-files` | Chặn commit file > 5MB (thường là lỡ add dữ liệu/artifact) |
| `check-merge-conflict` | Chặn commit còn sót marker `<<<<<<<` |

**Lệnh sửa — điều hay gây bối rối:** nếu một hook như `ruff-format`/`ruff-check --fix` **tự sửa**
file của bạn, lần chạy đó sẽ báo **Failed** và commit **bị hủy**, dù bản chất là nó đã sửa xong rồi.
Đây không phải lỗi thật — chỉ cần add lại phần vừa được tự sửa rồi commit lại lần hai:

```bash
git add -A
git commit -m "..."   # lần 2 sẽ thấy toàn bộ hook "Passed" vì không còn gì để sửa nữa
```

Muốn chạy thử toàn bộ hook trên cả repo mà không cần commit (ví dụ sau khi mới cài `pre-commit`):

```bash
uv run pre-commit run --all-files
```

### CI — chạy tự động trên mỗi Pull Request vào `main`

`.github/workflows/ci.yml` có 2 job, cả hai đều dùng `uv sync --all-packages` trước khi chạy:

| Job | Lệnh | Ý nghĩa |
|---|---|---|
| `tests` | `uv run pytest -m "not slow"` | Toàn bộ test suite, trừ QAOA nhiều seed (chạy lâu) |
| `verify-qubo` | `uv run pytest packages/quantum/tests/test_consistency.py -v` | Cổng chặn QAOA — xem Bước 6 |

PR không merge được vào `main` nếu một trong hai job này fail.

---

## Cấu hình

Mọi tham số nằm trong `configs/*.yaml` — không có giá trị nào hard-code trong code. Giá trị đã
khóa đã được điền sẵn; giá trị chưa chốt để `null` kèm comment `TODO(Tên người)`.

| File | Nội dung |
|---|---|
| `base.yaml` | seed, chế độ artifact, log; gộp các file còn lại qua `includes` |
| `universe.yaml` | 8 mã, tỷ trọng danh mục mẫu (tên mã cụ thể: `TODO`) |
| `data.yaml` | nguồn, khoảng thời gian, train/val/test split (`TODO`) |
| `regime.yaml` | HMM: 3 trạng thái, 10 seed, `n_iter=500` — danh sách feature: `TODO` |
| `scenarios.yaml` | S=500, H=20, block=5 |
| `risk.yaml` | α=0.95 — phí, spread, liquidity penalty: `TODO` |
| `quantum.yaml` | K=3, p=1, shots=1024 — λ₁, λ₂, P: `TODO` |
| `profiles/` | Contract cấp cao `demo_fast.yaml`/`workflow_update.yaml` — xem mục "Profile" phía trên |

Các file trên (`universe.yaml` → `quantum.yaml`) là config **module**, đang được code đọc trực
tiếp và **khớp scope `demo_fast`**. `configs/profiles/*.yaml` không phải config module — đó là
contract cấp cao để không lẫn lộn số liệu giữa hai hướng phát triển (xem mục "Profile" ở trên).

Đổi chế độ artifact trong `base.yaml`:

- `artifacts.mode: dev` → ghi vào `artifacts/dev/`, đường dẫn cố định, lặp nhanh
- `artifacts.mode: runs` → ghi vào `artifacts/runs/run_YYYYMMDD_HHMM/`, có version

Từ ngày 4 trở đi mọi số liệu lên slide phải truy được về một `run_id`.

---

## Cấu trúc

```
QSHIELD/
├── packages/          # thư viện Python, không biết gì về web
│   ├── contracts/     # schema + đường dẫn + mock — mọi thứ khác phụ thuộc
│   ├── data/          # thu thập, làm sạch, feature
│   ├── ai/            # HMM regime + sinh kịch bản
│   ├── risk/          # CVaR, chi phí, g/C/c
│   ├── quantum/       # QUBO, exact solver, QAOA
│   └── pipeline/      # orchestrator
├── backend/           # FastAPI — chỉ đọc artifact
├── frontend/          # Next.js + Tailwind
├── configs/           # toàn bộ tham số
│   └── profiles/      # contract demo_fast vs workflow_update — xem mục "Profile" ở trên
├── data/              # dữ liệu (gitignore, trừ metadata/)
├── artifacts/         # output pipeline
├── reports/           # báo cáo cho người đọc
├── docs/              # scope, kiến trúc, runbook, limitations, disclaimer
└── tests/             # test tích hợp (unit test nằm trong từng package)
```

Chi tiết từng thư mục, có gì bên trong, ai phụ trách: `docs/Structure.md` (đặc biệt mục 1.1).
Quy tắc kỹ thuật bất biến: `CLAUDE.md`. Kiến trúc pipeline & hợp đồng dữ liệu:
`docs/architecture/`.

---

## Phiên bản đã kiểm chứng

Chạy thật trên Python 3.14.4, uv 0.11.7:

| Gói | Version |
|---|---|
| qiskit | 2.5.1 |
| qiskit-aer | 0.17.2 |
| qiskit-algorithms | 0.4.0 |
| qiskit-optimization | 0.7.0 |
| hmmlearn | 0.3.3 |
| pandas | 2.3.3 |
| numpy | 2.2.6 |
| pandera | 0.32.1 |
| fastapi | 0.141.1 |

**Cảnh báo quan trọng:** qiskit ở đây là **2.x**, không phải 1.x. `qiskit.primitives.Sampler`
đã bị xóa. Mọi ví dụ QAOA tìm thấy trên mạng viết cho 1.x sẽ chết ngay dòng import.
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

Aer `SamplerV2` **không** chạy trực tiếp được QAOA ansatz (`AerError: unknown instruction: QAOA`)
vì cần transpile về ISA trước. Với 8 qubit thì `StatevectorSampler` là đủ.

---

## Git

```
main      → phiên bản ổn định
develop   → nhánh tích hợp
feature/* → nhánh của từng module
```

| Nhánh | Thư mục |
|---|---|
| `feature/contracts` | `packages/contracts/` |
| `feature/data-pipeline` | `packages/data/` |
| `feature/hmm-regime` | `packages/ai/regime/` |
| `feature/scenarios` | `packages/ai/scenarios/` |
| `feature/risk-engine` | `packages/risk/` |
| `feature/qubo-qaoa` | `packages/quantum/` |
| `feature/api` | `backend/` |
| `feature/dashboard` | `frontend/` |

Mỗi pull request cần: mô tả input/output, hướng dẫn chạy, kết quả test, artifact mẫu, người review.

---

## Sự cố thường gặp

**`uv sync` báo thiếu `pyproject.toml`** — một workspace member chưa có file khai báo.
Kiểm tra: `ls packages/*/pyproject.toml backend/pyproject.toml` phải ra đủ 7 dòng.

**`ModuleNotFoundError: qshield_contracts`** (hoặc `qshield_*` khác) — thiếu
`src/qshield_<tên>/__init__.py`. `uv_build` bắt buộc file này tồn tại, kể cả rỗng.

**`Found conflicting Python requirements`** — `requires-python` giữa root và member không khớp.
Tất cả phải là `>=3.14,<3.15`.

**`uv run qshield-<tên> --help` báo command not found** — package đó chưa nằm trong
`[tool.uv.workspace] members` của `pyproject.toml` gốc, hoặc chưa `uv sync` lại sau khi thêm
`[project.scripts]`.

**Frontend lệch field so với API** — quên chạy `npm run types` sau khi backend đổi schema.

**Streamlit/Next.js chết lúc demo** — dùng bản offline: `frontend/public/demo/` chứa snapshot JSON.

Danh sách đầy đủ, kèm lỗi tính toán/logic hay gặp: `docs/runbook/troubleshooting.md`.
