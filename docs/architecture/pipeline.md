# Kiến trúc pipeline

Tài liệu này mô tả pipeline **đã khóa** của Q-SHIELD (theo `CLAUDE.md` và `docs/Structure.md`) —
phạm vi kỹ thuật thực sự được implement trong 7 ngày, khác với pipeline 14 bước đầy đủ mô tả ở
`docs/product/product_requirements.md` §12.2 (xem `docs/limitations.md` §1 để biết bảng đối chiếu).

```
Data → Regime → Scenarios → Risk → QUBO → Exact/QAOA → CVaR after hedge
```

Pipeline **một chiều**: 8 mã, dữ liệu ngày, 500 kịch bản × 20 ngày, chọn đúng K=3 hành động (mỗi
hành động = giảm 20% vị thế một mã, chuyển phần vốn sang tiền mặt).

---

## 1. Nguyên tắc kiến trúc

**`packages/` chứa toàn bộ trí tuệ của hệ thống. `backend/` và `frontend/` chỉ là lớp trình bày.**
Nếu xóa cả hai lớp trình bày, pipeline vẫn phải chạy được bằng dòng lệnh
(`uv run qshield-pipeline all`).

### Chiều phụ thuộc một chiều

```
contracts ← data, ai, risk, quantum
risk      ← quantum      (exact solver cần true CVaR — import chéo DUY NHẤT được phép)
tất cả    ← pipeline ← backend ← frontend (qua HTTP)
```

Mọi mũi tên đi ngược chiều này là dấu hiệu hợp đồng dữ liệu (`packages/contracts`) đang thiếu gì đó
— phải sửa `contracts`, không import tắt giữa hai package cùng cấp.

`packages/risk` → `packages/quantum` là import chéo hợp lệ duy nhất: exact solver cần gọi
`qshield_risk.evaluate` để chấm true CVaR cho từng bitstring khi duyệt 2⁸ = 256 tổ hợp.

### Validate ở mọi ranh giới module

Mỗi module gọi `validate_or_raise()` (từ `packages/contracts`) cho cả input lẫn output. Fail fast
tại chỗ — không để dữ liệu sai trôi xuống các tầng sau.

---

## 2. Sáu chặng của pipeline

| # | Chặng | Package/module | Input chính | Output chính |
|---|---|---|---|---|
| 1 | Data | `qshield_data` (`packages/data/`) | Giá/khối lượng thô | `data/processed/returns.parquet`, `features.parquet` |
| 2 | Regime | `qshield_ai.regime` (`packages/ai/`) | Market features | `.../regime/regime_daily.parquet` (3 xác suất trạng thái) |
| 3 | Scenarios | `qshield_ai.scenarios` (`packages/ai/`) | State + asset returns | `.../scenarios/stress_scenarios.npz` (tensor 500×20×8) |
| 4 | Risk | `qshield_risk` (`packages/risk/`) | Portfolio + scenario tensor | `.../risk/action_effects.csv` (g, C, c) |
| 5 | QUBO / Solve | `qshield_quantum` (`packages/quantum/`) | g, C, c từ Risk Engine | `.../optimization/qaoa_result.json` (bitstring + metrics) |
| 6 | CVaR after hedge | `qshield_risk.evaluate` gọi lại từ solver | Bitstring thắng | True CVaR sau khi áp dụng hành động |

Orchestrator (`packages/pipeline/src/qshield_pipeline/stages.py`, `run.py`, `cli.py`) chạy tuần tự
sáu chặng này, validate schema giữa mỗi chặng, và fail fast nếu một chặng lỗi
(`packages/pipeline/src/qshield_pipeline/run_context.py` tạo `artifacts/runs/run_YYYYMMDD_HHMM/`).

Lệnh tương ứng từng chặng (xem `README.md`):

```bash
uv run qshield-data     build       # → data/processed/*.parquet
uv run qshield-ai       regime      # → artifacts/.../regime/
uv run qshield-ai       scenarios   # → artifacts/.../scenarios/
uv run qshield-risk     effects     # → artifacts/.../risk/
uv run qshield-quantum  solve       # → artifacts/.../optimization/
```

hoặc chạy toàn bộ bằng `uv run qshield-pipeline all --config configs/base.yaml [--mock]`.

---

## 3. Chi tiết từng module

### `packages/contracts/` — hợp đồng dữ liệu dạng code

Package quan trọng nhất repo — lý do 5 người làm song song mà vẫn ráp được với nhau.

```
contracts/src/qshield_contracts/
├── enums.py     # RegimeName, Stage, SolverKind, ArtifactMode
├── config.py    # đọc & gộp configs/*.yaml — nơi DUY NHẤT mở file yaml
├── paths.py     # ArtifactPaths — nơi DUY NHẤT sinh đường dẫn artifact
├── runs.py      # RunContext: run_id, log, metrics.json, config.json
├── validate.py  # validate_or_raise() dùng ở mọi ranh giới module
├── schemas/     # định nghĩa hình dạng mọi artifact (xem docs/architecture/data_contracts.md)
└── mocks/       # sinh dữ liệu giả ĐÚNG SCHEMA — dùng để 5 người phát triển song song từ ngày 1
```

### `packages/data/` — thu thập, làm sạch, feature

```
data/src/qshield_data/
├── sources/registry.py, sources/loaders/   # nguồn, ngày lấy, quyền dùng, version
├── clean/normalize.py, validate_prices.py, corporate_actions.py
├── returns.py        # simple + log return — KHÔNG forward-fill
├── features.py        # vol20, drawdown, corr, illiquidity — chỉ dùng dữ liệu đến t
├── split.py           # TimeSeriesSplit; scaler fit CHỈ trên train
└── quality/checks.py, report.py, manifest.py
```

### `packages/ai/` — HMM regime + sinh kịch bản

```
ai/src/qshield_ai/
├── regime/feature_set.py, train.py, selection.py, labeling.py, evaluate.py
│     GaussianHMM 3 trạng thái, 10 seed, n_iter=500; nhãn gán THEO THỐNG KÊ, không theo state id
├── scenarios/bootstrap.py, validate.py
│     regime-conditioned moving-block bootstrap, block 5 → 20 ngày
├── scenarios/cvae/     # TÙY CHỌN — xóa được nếu hết giờ, không chặn champion
└── baseline/rule_based_regime.py   # dự phòng khi HMM không có ý nghĩa kinh tế
```

### `packages/risk/` — CVaR, chi phí, hệ số QUBO

```
risk/src/qshield_risk/
├── portfolio.py    # sum(w)=1, không âm
├── paths.py         # R_{p,s,t} → tích lũy H ngày → L_s = -R^(H)
├── metrics.py        # VaR_α, CVaR_α (Rockafellar–Uryasev), α=0.95
├── drawdown.py, costs.py, actions.py
├── effects.py         # g_i = CVaR_0 − CVaR_i ; C_ij = g_i + g_j − R_ij
├── normalize.py       # đưa g, C, c về cùng thang trước khi vào QUBO
└── evaluate.py         # ← API DUY NHẤT cho package khác: bitstring → true CVaR
```

`evaluate.py` là lối vào hợp lệ duy nhất từ `packages/quantum` (import chéo được phép trong §1).

### `packages/quantum/` — QUBO, exact solver, QAOA

```
quantum/src/qshield_quantum/
├── formulation/objective.py    # f(z) NumPy thuần — GROUND TRUTH
├── formulation/qubo.py, penalty.py, qiskit_program.py
├── verify/consistency.py        # ← cổng chặn: 3 cách tính objective phải khớp
├── solvers/exact.py             # duyệt 2⁸ = 256, ground truth chấm QAOA
├── solvers/qaoa.py               # p=1, 1024 shots, COBYLA, 10 seed
├── backends/simulator.py (StatevectorSampler), backends/hardware.py (trống có chủ đích)
├── decode.py                     # bitstring → action → ticker → tỷ trọng mới
└── benchmark.py                  # gap, feasibility, success prob, runtime, depth
```

**Chạy `verify/consistency.py` trước khi tin bất kỳ kết quả QAOA nào** — so ba cách tính objective
(hàm NumPy tự viết, `QuadraticProgram`, QUBO sau convert). Lệch nhau nghĩa là QUBO sai; đừng debug
QAOA khi QUBO còn sai.

### `packages/pipeline/` — orchestrator

```
pipeline/src/qshield_pipeline/
├── stages.py        # data → regime → scenarios → risk → qubo → solve
├── run_context.py    # tạo artifacts/runs/run_YYYYMMDD_HHMM/
├── run.py             # chạy tuần tự, validate schema giữa mỗi chặng, fail fast
└── cli.py              # uv run qshield-pipeline all
```

### `backend/` — FastAPI, chỉ đọc artifact

```
backend/src/qshield_api/
├── routers/portfolio.py    # POST /portfolio/validate
├── routers/regime.py       # GET  /regime/current, /regime/timeline
├── routers/scenarios.py    # GET  /scenarios/summary
├── routers/risk.py         # POST /risk/cvar
├── routers/optimize.py     # POST /optimize/jobs → 202 + job_id ; GET .../{id}
├── routers/benchmark.py    # GET  /benchmark/quantum-vs-classical
├── routers/runs.py         # GET  /runs, /runs/{run_id}
└── jobs/store.py, jobs/worker.py   # `optimize` chạy nền: exact + QAOA 10 seed
```

`optimize` bất đồng bộ vì exact solver duyệt 256 bitstring, mỗi cái gọi lại Risk Engine trên tensor
(500, 20, 8), cộng QAOA 10 seed — chạy đồng bộ có thể treo request giữa lúc demo.

**Ranh giới không được vượt: backend không chứa công thức tài chính.** Một dòng tính CVaR trong
`routers/` là bug kể cả khi ra số đúng — backend chỉ gọi `qshield_risk`/`qshield_quantum` hoặc đọc
artifact.

### `frontend/` — Next.js 15 + Tailwind, 5 trang ứng với 5 khu vực dashboard

```
frontend/
├── app/page.tsx             # 1. Portfolio Input
├── app/regime/page.tsx      # 2. Market Regime
├── app/scenarios/page.tsx   # 3. Stress Laboratory
├── app/risk/page.tsx        # 4. Risk Before–After
├── app/quantum/page.tsx     # 5. Quantum–Classical Benchmark
├── lib/api.ts                # wrapper fetch duy nhất
├── lib/types.ts               # SINH TỰ ĐỘNG từ OpenAPI (`npm run types`) — không sửa tay
└── public/demo/                # snapshot JSON cho chế độ offline
```

Frontend không chứa logic tài chính — chỉ hiển thị số backend trả về.

---

## 4. Artifact modes

`configs/base.yaml` (`artifacts.mode`) quyết định nơi ghi output:

| Mode | Đường dẫn | Dùng khi |
|---|---|---|
| `dev` | `artifacts/dev/regime/regime_daily.parquet` (cố định) | Lặp nhanh ngày 1–3, không cần tái lập |
| `runs` | `artifacts/runs/run_YYYYMMDD_HHMM/outputs/{regime,scenarios,risk,optimization}/` | Có version — bắt buộc từ ngày 4, mọi số lên slide phải truy được về một `run_id` |

`RunContext` (`packages/contracts/src/qshield_contracts/runs.py`) là **module duy nhất** được ghi
`config.json`, `data_version.json`, `metrics.json`, `logs.txt` — các module tính toán chỉ trả về dữ
liệu, không tự ghi metadata.

`ArtifactPaths` (`packages/contracts/src/qshield_contracts/paths.py`) là **nơi duy nhất** sinh đường
dẫn artifact — không nối chuỗi path ở nơi khác trong repo.

---

## 5. Phát triển song song bằng mock

Từ ngày 1, cả 5 thành viên chạy song song trên **mock**, không ai chờ ai:

```bash
uv run qshield-pipeline all --config configs/base.yaml --mock
```

`--mock` sinh dữ liệu giả đúng schema từ `qshield_contracts.mocks`. Khi dữ liệu thật của một chặng
sẵn sàng, chỉ đổi nguồn đầu vào — không đổi code chặng phía sau, vì mọi chặng chỉ phụ thuộc vào
schema trong `contracts`, không phụ thuộc cách chặng trước tạo ra dữ liệu đó.

Xem `docs/architecture/data_contracts.md` để biết chi tiết schema từng artifact, và
`docs/runbook/setup.md` để biết cách cài đặt và chạy.
