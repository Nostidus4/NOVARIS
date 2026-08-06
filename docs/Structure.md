# Cấu trúc thư mục & phân công

Tài liệu này trả lời hai câu hỏi: **file này để làm gì** và **ai chịu trách nhiệm**.

---

## 1. Nhìn tổng thể

```
QSHIELD/
├── pyproject.toml         # uv workspace root
├── uv.lock                # 1 lockfile cho cả repo
├── README.md              # cài đặt & chạy
├── CLAUDE.md              # quy tắc kỹ thuật bất biến
│
├── configs/               # toàn bộ tham số
├── packages/              # thư viện Python, không biết gì về web
│   ├── contracts/         # ← mọi thứ khác phụ thuộc vào đây
│   ├── data/
│   ├── ai/
│   ├── risk/
│   ├── quantum/
│   └── pipeline/
├── backend/               # FastAPI
├── frontend/              # Next.js 15 + Tailwind
│
├── data/                  # dữ liệu thô & đã xử lý (gitignore)
├── artifacts/             # output pipeline
├── reports/               # báo cáo cho người đọc
├── notebooks/             # thử nghiệm
├── docs/                  # scope, kiến trúc, runbook, cấu trúc thư mục (Structure.md — file này)
└── tests/                 # test tích hợp & E2E
```

Nguyên tắc: **`packages/` chứa toàn bộ trí tuệ của hệ thống. `backend/` và `frontend/` chỉ là lớp
trình bày.** Nếu xoá cả hai lớp trình bày đi, pipeline vẫn phải chạy được bằng dòng lệnh.

---

## 1.1. Tổng quan từng thư mục — có gì bên trong, nhiệm vụ là gì

Bảng dưới trả lời nhanh "thư mục này có gì, dùng để làm gì" cho **mọi thư mục cấp cao nhất** của
repo, trước khi đi vào chi tiết từng file ở §3. Cột "Có gì bên trong" phản ánh đúng tình trạng hiện
tại (phần lớn còn là scaffold — file `.py` rỗng chỉ có một dòng comment phân công, `configs/*.yaml`
đã điền phần tham số đã khóa, phần `data/`, `artifacts/`, `reports/`, `notebooks/` mới chỉ có
`.gitkeep` giữ chỗ, chưa có dữ liệu/output thật).

| Thư mục | Có gì bên trong (hiện tại) | Nhiệm vụ |
|---|---|---|
| `configs/` | 7 file `.yaml` (`base`, `universe`, `data`, `regime`, `scenarios`, `risk`, `quantum`) + `uat/` (3 kịch bản) + `profiles/` (`demo_fast.yaml`, `workflow_update.yaml`, `README.md`). Tham số đã khóa đã điền sẵn; phần chưa chốt để `null` kèm `TODO(Tên người)`. | Nơi **duy nhất** chứa tham số của toàn hệ thống — không hard-code trong code. `profiles/` là contract cấp cao: `workflow_update` (2026-08-06, team chốt làm baseline chính thức — 30 mã/top-10/20-bit) vs `demo_fast` (8 mã, code hiện tại đang chạy scope này, chưa bắt kịp baseline) — xem `README.md` gốc mục "Profile" và `docs/limitations.md` §1. |
| `packages/` | 6 package Python độc lập (`contracts`, `data`, `ai`, `risk`, `quantum`, `pipeline`), mỗi package có `src/` + `tests/`. | Chứa **toàn bộ trí tuệ của hệ thống**: từ đọc dữ liệu thô đến giải QUBO. Không biết gì về web/HTTP. |
| ├─ `packages/contracts/` | `schemas/`, `mocks/`, `config.py`, `paths.py`, `runs.py`, `validate.py`, `enums.py` | Hợp đồng dữ liệu dạng code — mọi package khác phụ thuộc vào đây (xem `docs/architecture/data_contracts.md`). |
| ├─ `packages/data/` | `sources/`, `clean/`, `quality/`, `returns.py`, `features.py`, `split.py`, `manifest.py` | Thu thập, làm sạch, tạo feature và version hóa dữ liệu. |
| ├─ `packages/ai/` | `regime/` (HMM), `scenarios/` (bootstrap + `cvae/` tùy chọn), `baseline/` | Nhận diện trạng thái thị trường và sinh kịch bản stress. |
| ├─ `packages/risk/` | `metrics.py`, `costs.py`, `effects.py`, `evaluate.py`, `tests/` (6 file test) | Tính CVaR, chi phí, và hệ số `g`/`C`/`c` đưa vào QUBO. |
| ├─ `packages/quantum/` | `formulation/`, `verify/`, `solvers/`, `backends/`, `decode.py`, `benchmark.py` | Dựng QUBO, giải bằng exact/QAOA, benchmark. |
| └─ `packages/pipeline/` | `stages.py`, `run.py`, `run_context.py`, `cli.py` | Orchestrator chạy tuần tự 6 chặng, tạo `run_id`. |
| `backend/` | `routers/` (7 router), `jobs/` (job registry + worker nền), `main.py`, `deps.py` | Lớp API FastAPI — chỉ đọc artifact, **không** chứa công thức tài chính. |
| `frontend/` | `app/` (trang Portfolio Input đã có; 4 trang regime/scenarios/risk/quantum còn thiếu), `lib/api.ts`, `lib/types.ts` (sinh tự động), `public/demo/` | Next.js dashboard, 5 khu vực — chỉ hiển thị số backend trả về, không có logic tài chính riêng. |
| `data/` | `raw/`, `interim/`, `processed/`, `metadata/` — hiện chỉ có `.gitkeep`, chưa có dữ liệu thật | Dữ liệu giá/khối lượng qua từng giai đoạn xử lý (bị gitignore, trừ `metadata/`). |
| `artifacts/` | `dev/` (đường dẫn cố định), `runs/run_YYYYMMDD_HHMM/` (có version) — hiện rỗng | Output của pipeline: regime, scenarios, risk, optimization theo từng `run_id`. |
| `reports/` | `uat/` — hiện rỗng | Báo cáo cho người đọc: data quality report, benchmark, model card, UAT report. |
| `notebooks/` | `exploration/`, `validation/`, `benchmarks/` — hiện rỗng | Notebook thử nghiệm; theo `CLAUDE.md`, **không được** chứa core logic — chỉ gọi lại hàm trong `packages/`. |
| `docs/` | `Structure.md` (file này), `limitations.md`, `benchmark_plan.md`, `product/`, `architecture/`, `runbook/`, `perf/` (báo cáo hiện thực & đo đạc theo ngày), `handoffs/` (input còn chờ owner duyệt) | Toàn bộ tài liệu: phạm vi sản phẩm, kiến trúc, giới hạn, runbook vận hành, kế hoạch benchmark. |
| `tests/` | `contracts/`, `integration/`, `e2e/` | Test tích hợp & end-to-end xuyên nhiều package; unit test nằm trong từng `packages/*/tests/`. |
| File gốc | `pyproject.toml` (uv workspace root), `uv.lock` (1 lockfile chung), `README.md`, `CLAUDE.md`, `main.py`, `.python-version`, `.gitignore` | Cấu hình workspace và hai tài liệu bắt buộc đọc trước khi code. |

---

## 2. Đường găng và luồng bàn giao

```
Minh Anh        Tú                  Phúc              Tân
   │            │                    │                 │
 Data ────→ Regime ────→ Scenarios ────→ Risk ────→ QUBO ────→ QAOA ────→ Dashboard
                                                                              │
                                                                            Ngọc
                                                                    (nghiệm thu & trình bày)
```

Nhưng **không ai chờ tuần tự**. Từ ngày 1 cả 5 người chạy song song trên dữ liệu giả sinh từ
`packages/contracts/mocks/`. Khi dữ liệu thật xong thì chỉ đổi nguồn đầu vào, không đổi code.

---

## 3. Chi tiết từng thư mục

### `configs/` — toàn bộ tham số

Không có con số nào hard-code trong code. Ngọc là người duyệt mọi thay đổi ở đây.

| File | Nội dung |
|---|---|
| `base.yaml` | seed, chế độ artifact, log; gộp các file khác qua `includes` |
| `universe.yaml` | 8 mã, tỷ trọng danh mục mẫu |
| `data.yaml` | nguồn, khoảng thời gian, train/val/test split |
| `regime.yaml` | HMM: 3 trạng thái, 10 seed, danh sách feature |
| `scenarios.yaml` | S=500, H=20, block=5, bật/tắt CVAE |
| `risk.yaml` | α=0.95, phí, spread, liquidity penalty |
| `quantum.yaml` | K=3, λ₁, λ₂, P, p=1, shots=1024 |
| `uat/portfolio_*.yaml` | 3 kịch bản nghiệm thu của Ngọc |

---

### `packages/contracts/` — hợp đồng dữ liệu dạng code

**Đây là thư mục quan trọng nhất repo.** Nó là lý do 5 người làm song song mà vẫn ráp được với
nhau. Bảng mô tả cột trong file Word không chặn được ai gõ sai tên cột; schema chạy được thì có.

```
contracts/src/qshield_contracts/
├── enums.py           # RegimeName, Stage, SolverKind, ArtifactMode
├── config.py          # đọc & gộp configs/*.yaml — nơi DUY NHẤT mở file yaml
├── paths.py           # ArtifactPaths — nơi DUY NHẤT sinh đường dẫn artifact
├── runs.py            # RunContext: run_id, log, metrics.json, config.json
├── validate.py        # validate_or_raise() dùng ở mọi ranh giới module
├── schemas/           # định nghĩa hình dạng mọi artifact
│   ├── returns.py     ├── scenarios.py     (tensor 5000×20×8)
│   ├── features.py    ├── risk.py          (g, C, c, action_effects)
│   ├── regime.py      └── optimization.py  (qubo, exact, qaoa result)
└── mocks/             # sinh dữ liệu giả ĐÚNG SCHEMA cho ngày 1-3
```

`paths.py` cho phép đổi giữa hai chế độ chỉ bằng một dòng config:

- `artifacts.mode: dev` → `artifacts/dev/regime/regime_daily.parquet` (cố định, lặp nhanh)
- `artifacts.mode: runs` → `artifacts/runs/run_20260802_1430/outputs/regime/...` (có version)

---

### `packages/data/` — Nguyễn Đỗ Minh Anh

```
data/src/qshield_data/
├── sources/registry.py        # Data Source Register: nguồn, ngày lấy, quyền dùng, version
├── sources/loaders/           # vnstock.py, csv_local.py
├── clean/normalize.py         # chuẩn hoá ticker & ngày, bỏ trùng, đồng bộ lịch
├── clean/validate_prices.py   # giá âm/bằng 0, volume bất thường
├── clean/corporate_actions.py # sự kiện chia tách
├── returns.py                 # simple + log return — KHÔNG forward-fill
├── features.py                # vol20, drawdown, corr, illiquidity — chỉ dùng dữ liệu đến t
├── split.py                   # TimeSeriesSplit; scaler fit CHỈ trên train
├── quality/checks.py          # duplicate, missing, outlier, leakage, overlap
├── quality/report.py          # → reports/data_quality_report.html
└── manifest.py                # hash + version → data/metadata/data_manifest.json
```

---

### `packages/ai/` — Nguyễn Anh Tú

```
ai/src/qshield_ai/
├── regime/feature_set.py      # ĐÚNG 5 feature, không nhồi thêm
├── regime/train.py            # GaussianHMM 3 trạng thái, 10 seed, n_iter=500
├── regime/selection.py        # converged + val log-likelihood + BIC/AIC
├── regime/labeling.py         # state 0/1/2 → Normal/Volatile/Stress THEO THỐNG KÊ
├── regime/evaluate.py         # duration, transition matrix, ổn định qua seed
├── scenarios/bootstrap.py     # regime-conditioned moving-block, block 5 → 20 ngày
├── scenarios/validate.py      # mean, std, quantile, skew, kurtosis, corr, tail coverage
├── scenarios/cvae/            # TÙY CHỌN — xoá cả thư mục được nếu hết giờ
└── baseline/rule_based_regime.py   # dự phòng khi HMM không có ý nghĩa kinh tế
```

`cvae/` và `baseline/` tách riêng có chủ đích: một cái để cắt không đau, một cái để có sẵn khi
cần chứ không phải viết vội lúc HMM hỏng.

---

### `packages/risk/` — Liêu Hoài Phúc

```
risk/src/qshield_risk/
├── portfolio.py    # sum(w)=1, không âm, ticker có trong scenario set
├── paths.py        # R_{p,s,t} → tích luỹ H ngày → L_s = -R^(H)
├── metrics.py      # VaR_α, CVaR_α (Rockafellar–Uryasev), α=0.95
├── drawdown.py     # wealth path & maximum drawdown
├── costs.py        # TC_i = |Δw_i| × (fee + spread + liquidity_penalty)
├── actions.py      # hành động i: giảm 20% vị thế → chuyển sang tiền mặt
├── effects.py      # g_i = CVaR_0 − CVaR_i ; C_ij = g_i + g_j − R_ij
├── normalize.py    # đưa g, C, c về cùng thang trước khi vào QUBO
└── evaluate.py     # ← API cho quantum: bitstring → true CVaR
```

`evaluate.py` là **lối vào hợp lệ duy nhất** từ package khác. Exact solver bên `quantum` gọi nó để
chấm từng bitstring — đây là import chéo duy nhất được phép trong repo.

`risk/tests/` là test suite dày nhất: mỗi công thức cần một test so với ví dụ tính tay.

---

### `packages/quantum/` — Đỗ Ngọc Tân

```
quantum/src/qshield_quantum/
├── formulation/objective.py       # f(z) NumPy thuần — ĐÂY LÀ GROUND TRUTH
├── formulation/qubo.py            # dựng ma trận Q
├── formulation/penalty.py         # P·(Σz − K)²
├── formulation/qiskit_program.py  # QuadraticProgram → QuadraticProgramToQubo
├── verify/consistency.py          # ← 3 cách tính objective phải khớp
├── solvers/exact.py               # duyệt 2^8 = 256, ground truth chấm QAOA
├── solvers/qaoa.py                # p=1, 1024 shots, COBYLA, 10 seed
├── solvers/warm_start.py          # tuỳ chọn
├── backends/simulator.py          # StatevectorSampler
├── backends/hardware.py           # để trống có chủ đích — sau cuộc thi
├── decode.py                      # bitstring → action → ticker → tỷ trọng mới
└── benchmark.py                   # gap, feasibility, success prob, runtime, depth
```

`verify/consistency.py` là cổng chặn: chạy nó trước khi tin bất kỳ kết quả QAOA nào.

---

### `packages/pipeline/` — Đỗ Ngọc Tân

```
pipeline/src/qshield_pipeline/
├── stages.py        # data → regime → scenarios → risk → qubo → solve
├── run_context.py   # tạo artifacts/runs/run_YYYYMMDD_HHMM/
├── run.py           # chạy tuần tự, validate schema giữa mỗi chặng, fail fast
└── cli.py           # uv run qshield-pipeline all
```

Hiện thực của yêu cầu "một lệnh chạy toàn pipeline".

---

### `backend/` — Đỗ Ngọc Tân

```
backend/src/qshield_api/
├── main.py, config.py, deps.py
├── routers/portfolio.py    # POST /portfolio/validate
├── routers/regime.py       # GET  /regime/current, /regime/timeline
├── routers/scenarios.py    # GET  /scenarios/summary
├── routers/risk.py         # POST /risk/cvar
├── routers/optimize.py     # POST /optimize/jobs → 202 + job_id ; GET .../{id}
├── routers/benchmark.py    # GET  /benchmark/quantum-vs-classical
├── routers/runs.py         # GET  /runs, /runs/{run_id}
├── jobs/store.py           # job registry
└── jobs/worker.py          # chạy exact + QAOA 10 seed ở nền
```

`optimize` bất đồng bộ vì exact solver duyệt 256 bitstring, mỗi cái gọi lại Risk Engine trên
tensor (500, 20, 8), cộng QAOA 10 seed. Nếu chạy đồng bộ thì request HTTP có thể treo giữa lúc demo.

**Ranh giới không được vượt:** backend không chứa công thức tài chính. Một dòng tính CVaR trong
`routers/` là bug, kể cả khi ra số đúng.

---

### `frontend/` — Nguyễn Thị Ánh Ngọc + Đỗ Ngọc Tân

```
frontend/
├── app/page.tsx             # 1. Portfolio Input
├── app/regime/page.tsx      # 2. Market Regime
├── app/scenarios/page.tsx   # 3. Stress Laboratory
├── app/risk/page.tsx        # 4. Risk Before–After
├── app/quantum/page.tsx     # 5. Quantum–Classical Benchmark
├── components/{portfolio,regime,scenarios,risk,quantum,ui}/
├── lib/api.ts               # wrapper fetch duy nhất
├── lib/types.ts             # ← SINH TỰ ĐỘNG từ OpenAPI, không sửa tay, không commit
├── lib/polling.ts           # hook poll /optimize/jobs/{id}
└── public/demo/             # snapshot JSON cho chế độ offline
```

Năm route ứng đúng năm khu vực dashboard. `npm run types` sinh lại `types.ts` mỗi khi backend đổi
schema — đây là cách kéo hợp đồng dữ liệu qua ranh giới Python/TypeScript.

---

### `data/`, `artifacts/`, `reports/`

```
data/
├── raw/          interim/       processed/     metadata/
                                 ├── returns.parquet
                                 └── features.parquet

artifacts/
├── dev/                      # scratch ngày 1-3, không cần tái lập
└── runs/run_20260802_1430/
    ├── config.json  data_version.json  metrics.json  logs.txt
    └── outputs/{regime,scenarios,risk,optimization}/

reports/
├── data_quality_report.html      scenario_validation.csv
├── quantum_classical_benchmark.csv
├── model_card.md                 uat/
```

Từ ngày 4, mọi số lên slide phải truy được về một `run_id`.

---

### `notebooks/` — nơi chạy thử, không phải nơi sống của logic

```
notebooks/
├── exploration/   # tò mò dữ liệu, thử ý tưởng trước khi viết thành hàm chính thức
├── validation/     # chạy một hàm trong packages/ với input mẫu, xem output có hợp lý không
└── benchmarks/      # so sánh QAOA vs exact vs classical, vẽ biểu đồ cho báo cáo/pitch
```

Cả ba thư mục hiện chỉ có `.gitkeep` — chưa có notebook nào. `jupyterlab` và `ipykernel` đã nằm sẵn
trong `dev` dependency-group của `pyproject.toml` gốc, nên chỉ cần `uv run jupyter lab` là dùng
được ngay, không cần cài thêm.

**Dùng khi nào**

| Thư mục | Câu hỏi nó trả lời | Ví dụ |
|---|---|---|
| `exploration/` | "Dữ liệu này trông như thế nào?" | Vẽ phân phối return của 8 mã, xem thử outlier |
| `validation/` | "Hàm tôi vừa viết trong `packages/` chạy đúng không?" | Gọi `qshield_risk.metrics.cvar(...)` với vài mảng loss mẫu, so sánh bằng mắt với tính tay |
| `benchmarks/` | "QAOA so với exact/classical thế nào?" | Đọc `qaoa_result.json` của nhiều run, vẽ optimality gap theo seed |

**Ranh giới bắt buộc — không được vi phạm**

`docs/product/product_requirements.md` (PR-NFR-MNT-004, PR-NFR-MNT-005) quy định rõ:

> *"Core logic KHÔNG ĐƯỢC chỉ tồn tại trong notebook."* Notebook chỉ được **gọi lại hàm đã có sẵn
> trong `packages/`** để xem/vẽ kết quả — không viết công thức tính CVaR, HMM, QUBO... mới trực
> tiếp trong cell rồi để mãi ở đó. Nếu một phép tính trong notebook chứng minh là đúng và hữu ích,
> nó phải được "tốt nghiệp" thành một hàm thật trong `packages/<tên>/`, có test đi kèm, rồi notebook
> quay lại **import và gọi** hàm đó — không giữ hai bản logic song song (một trong notebook, một
> trong package) vì chúng sẽ lệch nhau theo thời gian.

**Notebook khác `pytest` chỗ nào**

| | `notebooks/` | `packages/*/tests/`, `tests/` |
|---|---|---|
| Ai đọc kết quả | Người, tự mắt xem có hợp lý không | Máy, tự động qua `assert` |
| Chạy khi nào | Thủ công, lúc đang code/khám phá | Mỗi lần trước khi commit/mở PR (`uv run pytest`) |
| Có được commit không | Có, nhưng chỉ nên commit bản đã dọn (không chạy dở, không output rác) | Bắt buộc — là bằng chứng nghiệm thu |
| Thay thế được test không | Không | — |

Hai thứ bổ sung cho nhau: notebook giúp bạn *tìm ra* logic đúng nhanh hơn; test giữ cho logic đó
*không bị hỏng* về sau. Xem thêm quy ước code chung ở `CLAUDE.md`.

---

## 4. Phân công chi tiết

### Nguyễn Thị Ánh Ngọc — Product Owner / Project Lead / Finance Integration

Không phát triển một mô hình đơn lẻ, mà bảo đảm **toàn bộ mô hình đang giải đúng bài toán tài
chính**.

| Việc | Đầu ra |
|---|---|
| Khoá phạm vi nghiệp vụ | `docs/product/mvp_scope.md`, `product_requirements.md` |
| Khoá danh mục & hành động | `configs/universe.yaml`, `configs/risk.yaml` |
| Xây acceptance criteria | `docs/product/acceptance_criteria.md` |
| Quản lý traceability matrix | `docs/product/rtm.md` |
| Chủ trì UAT (3 kịch bản) | `reports/uat/` |
| Tài liệu & pitch | Báo cáo kỹ thuật, pitch deck, demo script, disclaimer |

Ngọc kiểm tra **ý nghĩa**, không chỉ kiểm tra dashboard có hiện số: trạng thái Stress có hợp lý
không, CVaR giảm có phải chỉ vì chuyển quá nhiều sang tiền mặt không, chi phí có bị bỏ sót không,
kết luận có vượt quá bằng chứng không.

**Xong khi:** scope không mâu thuẫn; mỗi yêu cầu có người phụ trách và test; số trên slide khớp
artifact; giải thích được toàn bộ pipeline mà không cần mở code; không có tuyên bố quantum
advantage thiếu bằng chứng.

---

### Nguyễn Đỗ Minh Anh — Data Engineer / Data Quality Owner

Tạo **bộ dữ liệu chính thức duy nhất**. Không thành viên nào tự tải bộ khác dùng riêng.

Bàn giao cho Tú và Phúc: `returns.parquet`, `features.parquet`, data dictionary, manifest,
quality report, hash/version.

**Xong khi:** pipeline chạy lại được; không chỉnh dữ liệu thủ công không log; mọi cột có định
nghĩa; mọi file có version; Tú huấn luyện HMM được mà không phải xử lý lại; Phúc tính portfolio
loss trực tiếp được.

---

### Nguyễn Anh Tú — AI/ML Engineer

Chuyển dữ liệu thị trường thành: trạng thái thị trường, xác suất trạng thái, bộ kịch bản stress.

Bàn giao cho Phúc: `regime_daily.parquet`, `regime_summary.json`, `stress_scenarios.npz` (tensor
500×20×8), `scenario_validation.csv`.

**Xong khi:** HMM tạo 3 trạng thái có ý nghĩa; không dùng dữ liệu test để fit; có probability chứ
không chỉ hard label; đủ 500 kịch bản đúng shape; tương quan giữa tài sản không bị phá huỷ;
artifact có seed & config; Phúc tính loss được mà không phải chỉnh lại kịch bản.

---

### Liêu Hoài Phúc — Quantitative Risk Analyst / QA Lead

Biến kịch bản stress thành chỉ tiêu tài chính và hệ số đầu vào cho QUBO.

Bàn giao cho Tân: `baseline_risk.json`, `action_effects.csv`, `pairwise_effects.csv` → tức là
vector **g**, ma trận **C**, vector chi phí **c**.

**Xong khi:** CVaR khớp ví dụ tính tay; quy ước loss/return nhất quán; mọi hành động tạo danh mục
hợp lệ; g, C, c có nguồn gốc rõ ràng; nghiệm QAOA được đánh giá lại bằng CVaR thật; test report có
bằng chứng pass/fail.

---

### Đỗ Ngọc Tân — Technical Lead / Quantum Engineer / Integration Owner

Biến đầu ra Risk Engine thành QUBO, chạy QAOA, tích hợp dashboard, bảo đảm cả repo hoạt động.

Cũng là người sở hữu `contracts/` và `pipeline/` — hai thứ phải xong sớm nhất vì mọi người chờ.

**Xong khi:** một lệnh chạy toàn pipeline; exact objective và QUBO objective khớp; QAOA chạy được
trên ít nhất 10 seed; dashboard không chứa logic tài chính trùng lặp; repo cài được trên máy mới;
có bản demo offline nếu deployment thất bại.

---

## 5. Bảng RACI rút gọn

`A` = chịu trách nhiệm cuối cùng · `R` = trực tiếp làm · `C` = được hỏi ý kiến · `I` = được báo

| Hạng mục | Ngọc | Minh Anh | Phúc | Tú | Tân |
|---|:--:|:--:|:--:|:--:|:--:|
| Scope & yêu cầu | A/R | C | C | C | C |
| Data pipeline | I | A/R | C | C | C |
| Data quality | C | A/R | C | C | I |
| HMM regime | C | C | I | A/R | C |
| Stress scenarios | C | C | C | A/R | I |
| Risk Engine | C | C | A/R | C | C |
| QUBO specification | C | I | R | C | A/R |
| QAOA | I | I | C | C | A/R |
| Testing | A | C | R | C | R |
| Dashboard | A | C | C | C | R |
| Deployment | I | I | C | C | A/R |
| Báo cáo & pitch | A/R | C | C | C | C |

---

## 6. Nhịp làm việc

**Hằng ngày**

- Đầu ngày — 15 phút: tiến độ & blocker
- Giữa ngày — 15 phút: kiểm tra interface giữa các module
- Cuối ngày — 30 phút: demo artifact & nghiệm thu

**Nhánh git** — mỗi nhánh chạm đúng một thư mục, gần như không xung đột merge:

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

Hai nơi cần review nghiêm vì ai cũng đụng: `configs/` và `packages/contracts/`.

---

## 7. Cổng nghiệm thu cuối ngày 4

Hệ thống phải chạy được xuyên suốt:

```
Portfolio → Regime → Scenarios → CVaR → QUBO → Exact/QAOA → CVaR after hedge
```

Nếu chưa đạt thì **dừng vô điều kiện**: không CVAE, không thêm biểu đồ, không chatbot, không mở
rộng VN30, không mô hình mới. Toàn đội tập trung vào tích hợp.

---

## 8. Phương án dự phòng

| Rủi ro | Xử lý |
|---|---|
| Dữ liệu thiếu | Giảm số tài sản, giữ nguyên schema |
| HMM không hội tụ | Giảm feature, `covariance_type: diag`, chạy nhiều seed |
| 3 regime không có ý nghĩa | Dùng `baseline/rule_based_regime.py`, báo cáo giới hạn |
| CVAE không đạt | Dùng moving-block bootstrap |
| QUBO sai | So từng bitstring với `formulation/objective.py` |
| QAOA không ổn định | Giảm qubit, giữ p=1, cache benchmark |
| QAOA kém classical | **Báo cáo trung thực**, không điều chỉnh kết quả |
| Deploy lỗi | Chạy local + `frontend/public/demo/` + video dự phòng |
| Không đủ thời gian | Cắt CVAE, cắt biểu đồ phụ, giữ đường găng |
