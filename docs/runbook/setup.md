# Setup — cài đặt và chạy Q-SHIELD

Runbook này dành cho một thành viên (kể cả người không phải module owner) cài đặt và chạy được
Q-SHIELD từ máy sạch. Đây cũng là bằng chứng khả năng tái lập (`docs/Structure.md` §4, mục "Xong
khi" của Tân: *"repo cài được trên máy mới"*).

---

## 1. Yêu cầu

| Công cụ | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.14 | `uv` tự tải nếu máy chưa có |
| uv | ≥ 0.11 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | ≥ 20 | Cho frontend |

Phiên bản package Python đã kiểm chứng chạy thật trên Python 3.14.4, uv 0.11.7:

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

**Cảnh báo quan trọng:** qiskit ở đây là **2.x**, không phải 1.x. `qiskit.primitives.Sampler` đã bị
xóa khỏi 2.x — mọi ví dụ QAOA tìm thấy trên mạng viết cho 1.x sẽ chết ngay dòng import. Xem
`docs/runbook/troubleshooting.md` để biết cách import đúng.

---

## 2. Cài đặt

```bash
git clone <repo-url> QSHIELD && cd QSHIELD

# Backend + toàn bộ package Python (1 lệnh, 1 venv chung)
uv sync --all-packages

# Frontend
cd frontend && npm install && cd ..
```

`uv sync --all-packages` cài cả 7 workspace member (`packages/contracts`, `packages/data`,
`packages/ai`, `packages/risk`, `packages/quantum`, `packages/pipeline`, `backend`) vào **một
`.venv` duy nhất** ở thư mục gốc. Không ai tự tạo virtualenv riêng.

Kiểm tra cài đặt thành công:

```bash
uv run python -c "import qiskit, hmmlearn, pandas; print(qiskit.__version__)"
```

Nếu `uv sync` báo thiếu `pyproject.toml` ở một package, hoặc `ModuleNotFoundError: qshield_*`, xem
`docs/runbook/troubleshooting.md`.

---

## 3. Chạy pipeline

### Toàn bộ pipeline, một lệnh

```bash
uv run qshield-pipeline all --config configs/base.yaml           # dữ liệu thật
uv run qshield-pipeline all --config configs/base.yaml --mock    # dữ liệu giả
```

Chế độ `--mock` sinh dữ liệu giả đúng schema từ `qshield_contracts.mocks` — dùng khi một chặng phía
trên (data/regime/scenarios) chưa sẵn sàng, để không phải chờ nhau khi phát triển song song. Xem
`docs/architecture/pipeline.md` §5.

### Từng chặng riêng lẻ

```bash
uv run qshield-data     build       # → data/processed/*.parquet
uv run qshield-ai       regime      # → artifacts/.../regime/
uv run qshield-ai       scenarios   # → artifacts/.../scenarios/
uv run qshield-risk     effects     # → artifacts/.../risk/
uv run qshield-quantum  solve       # → artifacts/.../optimization/
```

### Chạy app (backend + frontend)

```bash
uv run uvicorn qshield_api.main:app --reload --port 8000   # backend: http://localhost:8000
cd frontend && npm run dev                                  # frontend: http://localhost:3000
```

Sau khi backend chạy và mỗi khi backend đổi schema response, sinh lại type cho frontend:

```bash
cd frontend && npm run types
```

`frontend/lib/types.ts` sinh tự động từ `/openapi.json`. **Không sửa tay, không commit sai lệch với
backend hiện tại.**

---

## 4. Cấu hình

Mọi tham số nằm trong `configs/*.yaml` — không có giá trị nào hard-code trong code. Xem bảng đầy đủ
tại `docs/architecture/data_contracts.md` §2.

Chọn artifact mode trong `configs/base.yaml`:

- `artifacts.mode: dev` → ghi vào `artifacts/dev/`, đường dẫn cố định, lặp nhanh khi đang phát triển.
- `artifacts.mode: runs` → ghi vào `artifacts/runs/run_YYYYMMDD_HHMM/`, có version — dùng bắt buộc
  khi cần số liệu tái lập được (demo, báo cáo, slide).

---

## 5. Kiểm thử

```bash
uv run pytest                    # toàn bộ test suite
uv run pytest -m "not slow"      # bỏ qua QAOA nhiều seed (chạy nhanh hơn khi lặp code)
uv run pytest packages/risk      # chỉ Risk Engine — test suite dày nhất repo
uv run ruff check . && uv run ruff format .
uv run mypy packages backend
```

**Cổng chặn bắt buộc trước khi tin bất kỳ kết quả QAOA nào:**

```bash
uv run pytest packages/quantum/tests/test_consistency.py -v
```

Test này so ba cách tính objective (hàm NumPy tự viết, `QuadraticProgram`, QUBO sau convert). Nếu
lệch nhau, QUBO đang sai — sửa `formulation/`, đừng debug QAOA.

---

## 6. Thêm dependency

```bash
uv add --package qshield-risk "scipy>=1.14"
```

Không `pip install`. Không tạo virtualenv riêng cho một package.

---

## 7. Xác nhận cài đặt thành công (definition of done cho setup)

Một thành viên khác (không phải module owner) coi như cài đặt thành công khi:

1. `uv sync --all-packages` chạy không lỗi trên máy sạch.
2. `uv run qshield-pipeline all --config configs/base.yaml --mock` chạy hết pipeline và tạo artifact
   trong `artifacts/dev/` (hoặc `artifacts/runs/...`).
3. `uv run pytest packages/quantum/tests/test_consistency.py -v` pass.
4. Backend chạy được ở `:8000`, frontend chạy được ở `:3000` và gọi được API.
5. Nếu deployment/backend lỗi trong lúc demo, `frontend/public/demo/` có snapshot JSON offline —
   xem `docs/runbook/demo_script.md` §5 và `docs/runbook/troubleshooting.md`.

Chi tiết cấu trúc thư mục và ai phụ trách phần nào: `docs/Structure.md`. Quy tắc kỹ thuật bất biến
không được vi phạm khi setup/chạy: `CLAUDE.md`.
