# Hiện thực downstream `workflow_update` (đường provisional 16-bit) — 2026-08-06

Phiên này hiện thực **toàn bộ chặng downstream của baseline `workflow_update`** (Risk top-N →
QUBO/Quantum → rerank/polishing) theo hướng contract-first, trong lúc chặng Data 30 mã **chưa**
xong. Mọi run sinh ra ở đây gắn `profile_id=workflow_update_downstream`,
`profile_status=NON_BASELINE_RUN` và **không được dùng làm bằng chứng UAT/baseline**.

**Kết luận ngắn:** code đã generic theo `M = min(N_eligible, 10)` — với 8 mã hiện có chạy 16 bit /
137 structured samples / 65.536 trạng thái exact; khi có đủ 10 ứng viên thì **tự** thành 20 bit /
211 samples / 1.048.576 trạng thái, không phải sửa code, chỉ đổi config. Chặng Risk đã chạy thật
ra artifact trên đĩa; chặng Quantum + rerank mới verify bằng test, **chưa** hoàn tất một lần chạy
đầu-cuối thật (xem §6).

---

## 1. Vì sao có `workflow_update_downstream` thay vì chờ dữ liệu

`configs/profiles/workflow_update.yaml` là `BASELINE_TARGET` và cần 3 approval gate. Chặng Data
(30 mã VN30, adjusted-close evidence, eligibility) chưa có sign-off, nên không thể tạo run hợp lệ
theo profile đó. Thay vì chờ, phiên này tách một profile **con, có công bố**:

`configs/provisional/workflow_update_downstream.yaml` — `parent_profile_id: workflow_update`,
`status: NON_BASELINE_RUN`, `allowed_for: [downstream_contract_development,
integration_smoke_test]`, `not_allowed_for: [final_uat_baseline, product_claim_full_workflow,
quantum_advantage_claim]`.

File này cũng là **nơi duy nhất** chứa các giá trị tài chính tạm (transaction cost, trọng số/scale
của objective, cash target, score weights, QAOA seeds). Không có số nào bị nhúng trong code, và
`configs/risk.yaml`/`configs/quantum.yaml` gốc vẫn giữ `null` đúng trạng thái TBD.

Danh sách đầy đủ giá trị tạm + owner cần duyệt + ảnh hưởng khi đổi:
`docs/handoffs/workflow_update_open_inputs.md`.

## 2. `packages/contracts` — profile-aware config và schema downstream

| File | Nội dung |
|---|---|
| `config.py` | `Config.load_profiled(base, profile, override)` — deep-merge 3 tầng, override chỉ ghi đè khóa nó khai báo; `Config.workflow_runtime()` → `WorkflowRuntime` (candidate_count, bits_per_candidate, total_decision_bits, structured_sample_count, action_levels) và **tự validate** quan hệ `total_decision_bits = candidate_count × bits_per_candidate`, `structured_sample_count ≥ 1 + d + d(d−1)/2` |
| `schemas/downstream.py` | Contract cho 7 artifact mới: `candidate_top10`, `candidate_order`, `risk_summary`, `objective_samples`, `qubo_model`, solver result, `reranked_candidates`, `final_recommendation` |

Điểm quan trọng: schema **không hard-code 10 hay 20** — nhận `expected_candidates`/
`expected_bit_count` từ runtime, nên cùng một contract dùng được cho cả 8/16 (hôm nay) và 10/20
(baseline). `validate_final_recommendation` cưỡng chế các quy tắc tài chính đã khóa trong profile:
mapping `00/10/01/11 → 0/10/20/30%`, zero-action lock, biên polishing ±5pp, tổng tỷ trọng + tiền mặt
= 1.0 trước và sau hành động.

Mọi artifact bắt buộc mang provenance: `run_id`, `profile_id`, `profile_status`, `config_version`,
`config_hash`; từ QUBO trở đi thêm `candidate_order_hash`, từ solver trở đi thêm `qubo_hash`.

## 3. `packages/risk` — objective chuẩn, chọn ứng viên động, rerank, polishing

| File | Nội dung |
|---|---|
| `objective.py` | Hàm mục tiêu tài chính **duy nhất** cho cả sampling/rerank/polishing. 6 thành phần (CVaR, return sacrifice, transaction cost, turnover, liquidity penalty, cash-budget deviation), mỗi thành phần trả `raw`/`scaled`/`weight`/`contribution` để audit được. Thiếu weight/scale ⇒ raise, không tự đoán |
| `candidates.py` | `select_four_level_candidates()` — chấm marginal CVaR reduction **thật** ở cả 3 mức 10/20/30% cho từng mã, xếp hạng theo `net_risk_score`, chọn đúng `min(N_eligible, output_candidates)`; mã không đủ điều kiện hoặc weight = 0 vẫn nằm trong bảng kèm `reason`. `candidate_order()` khóa thứ tự giải mã bit |
| `sampling.py` | `structured_bit_vectors()` sinh intercept + toàn bộ main effect + toàn bộ pairwise → 137 mẫu ở M=8, 211 mẫu ở M=10; `decode_four_level_bits()` là codec `00/10/01/11 → 0/10/20/30%` |
| `rerank.py` | `rerank_candidates()` khử trùng lặp bitstring, chấm lại bằng true objective, xếp hạng và ghi `ranking_disagreement` so với thứ hạng theo QUBO energy. `polish_reductions()` — coordinate polishing ±5pp, **khóa cứng** mọi mã Quantum chọn 0% ở 0%, báo `polishing_dependency` (phần cải thiện đến từ polishing) |
| `cli.py` | Hai lệnh mới: `qshield-risk prepare-workflow` và `qshield-risk rerank-polish` |

`actions.py` thêm `apply_reductions()` (giảm theo tỷ lệ từng mã, không còn cố định 20%) và
`portfolio.py` bỏ mặc định 8 tài sản. API `demo_fast` cũ giữ nguyên, không phá.

`prepare-workflow` sinh `candidate_top10.csv`, `candidate_order.json`,
`qubo_objective_samples.parquet`, `risk_summary.json` và **tự validate** bằng contract trước khi
ghi. `rerank-polish` đọc candidate pool của solver, sinh `reranked_candidates.csv` và
`final_recommendation.json`.

## 4. `packages/quantum` — generic `2M` bit thay cho 8-bit K=3

| File | Nội dung |
|---|---|
| `formulation/four_level.py` | Codec 4 mức + tên biến theo ứng viên |
| `formulation/surrogate.py` | Fit surrogate bậc hai `z'Qz + linear'z + const` từ objective samples bằng least squares; **raise khi thiết kế thiếu rank** thay vì fit bừa |
| `verify/consistency.py` | `verify_quadratic_consistency()` — đối chiếu NumPy / `QuadraticProgram` / QUBO, chunked để chạy được ở 16–20 bit (CLAUDE.md quy tắc 15) |
| `solvers/exact.py` | `solve_quadratic_exact()` duyệt hết `2^d` trạng thái theo lô, giữ top-N ứng viên khả thi, **không** giữ dict toàn bộ energy (đủ RAM ở 2^20) |
| `solvers/qaoa.py` + `warm_start.py` | QAOA p=1 generic, warm-start từ nghiệm exact, ≥10 seed, giữ sample distribution mỗi seed |
| `benchmark.py` | `coordinate_descent_classical()` + `build_generic_benchmark()` — so exact/QAOA/classical trên cùng model |
| `workflow.py` | Ghép handoff Risk → surrogate → verify → exact → QAOA → benchmark → candidate pool |
| `cli.py` | `qshield-quantum workflow` — đọc handoff, **validate lại** bằng contract, kiểm tra `profile_id` khớp, sinh `qubo_model.json`/`exact_solution.json`/`qaoa_results.json`/`workflow_benchmark.json` kèm `qubo_hash` |

Nhánh `demo_fast` (8-bit, K=3) giữ nguyên hoàn toàn — vẫn dùng cho debug nhanh.

## 5. `packages/pipeline` — lệnh `downstream`

`qshield-pipeline downstream` chạy 3 chặng, mỗi chặng trong một **tiến trình con riêng** (bắt buộc
vì bug qiskit + pyarrow đã verify ở `docs/perf/2026-08-06-quantum-pipeline-implementation.md` §3.1):

```
qshield-risk prepare-workflow  →  qshield-quantum workflow  →  qshield-risk rerank-polish
```

Lệnh từ chối chạy nếu profile đã resolve không phải `NON_BASELINE_RUN`, để không ai vô tình tạo
"baseline" từ đường provisional. Fail-fast đúng chặng như `run_all`.

## 6. Trạng thái verify — cái gì đã chạy thật, cái gì chưa

**Đã chạy thật, có artifact trên đĩa** (`artifacts/dev/risk/`):

```
uv run qshield-risk prepare-workflow --mock
# [risk/workflow] candidates=8, bits=16, samples=137 -> artifacts/dev/risk
```

→ `candidate_top10.csv`, `candidate_order.json`, `qubo_objective_samples.parquet` (137 dòng),
`risk_summary.json`, đều pass contract validation.

**Chưa chạy trọn vẹn:** `qshield-quantum workflow` không hoàn tất trong ~12 phút và bị dừng tay.
Exact 65.536 trạng thái không phải nút thắt; nghi phần lớn thời gian nằm ở 10 seed QAOA 16 qubit
statevector với COBYLA `maxiter=200`. **Chưa đo, chưa kết luận** — đây là việc đầu tiên của kế
hoạch benchmark (`docs/benchmark_plan.md` §3.1). Vì vậy `qubo_model.json`, `exact_solution.json`,
`qaoa_results.json`, `workflow_benchmark.json`, `reranked_candidates.csv`,
`final_recommendation.json` **chưa có số thật nào**.

Cell chạy đầu-cuối có stream log trực tiếp nằm ở cuối
`notebooks/exploration/04_quantum_benchmark_workflow.ipynb` (gọi CLI qua subprocess — không import
`qshield_quantum` vào kernel, tránh cả segfault pyarrow lẫn `os._exit()` giết kernel).

**Test và kiểm tra tĩnh:**

| Lệnh | Kết quả |
|---|---|
| `uv run pytest packages/contracts -q` | 53 passed |
| `uv run pytest packages/risk -q` | 46 passed |
| `uv run pytest packages/quantum -m "not slow" -q` | 34 passed, 4 deselected |
| `uv run pytest packages/pipeline -q` | 12 passed |
| `uv run ruff check .` | pass |
| `uv run mypy --ignore-missing-imports packages/*/src` | pass (58 file) |

## 7. Sửa kèm: `uv run pytest` toàn repo

Doc 2026-08-06 §3.2 từng fix lỗi collect bằng `--import-mode=importlib`, nhưng vẫn còn
`packages/*/tests/__init__.py` khiến pytest đăng ký trùng plugin `tests.conftest` giữa các member
(`ValueError: Plugin already registered under a different name`) và mypy báo `Duplicate module named
"tests"`. Đã **xóa 6 file `tests/__init__.py`** (chúng chỉ là marker rỗng) — `importlib` không cần
chúng.

Sau khi xóa, `uv run pytest` toàn repo collect được, nhưng vẫn segfault ở
`packages/ai/tests/test_cli_regime.py` vì đúng bug qiskit + pyarrow cũ: chạy toàn repo trong **một**
tiến trình thì `qshield_quantum` và `to_parquet` gặp nhau. Chạy từng package riêng thì sạch. Đây là
hạn chế đã biết, chưa sửa trong phiên này.

## 8. Việc còn lại

1. Chạy trọn `qshield-pipeline downstream --mock` để có bộ artifact Quantum + final recommendation
   đầu tiên; đo và xử lý runtime QAOA.
2. Hoàn thiện Benchmark theo `docs/benchmark_plan.md` (GATE-08 + PR-SLV-012…015).
3. Bỏ `--mock`, đấu vào scenario cube thật khi Scenario Gate xong.
4. Thay giá trị provisional bằng số owner duyệt (`docs/handoffs/workflow_update_open_inputs.md`),
   tăng `config_version`, chạy lại toàn bộ downstream.
5. Cập nhật `docs/limitations.md` §1: bảng so sánh ở đó vẫn mô tả "code hiện tại = `demo_fast`",
   nay đã có thêm đường downstream provisional cần ghi rõ.

## 9. Cập nhật đo 20-bit — 2026-08-07

Handoff Risk hiện đã đủ **10 candidates / 20-bit / 211 samples** trên cube `(5000, 20, 30)`.

| Chặng | Kết quả đo |
|---|---:|
| Fit surrogate | 0.00s |
| Consistency sampled NON_FINAL (4.098 / 1.048.576 states) | 2.24s |
| Exact exhaustive 20-bit (1.048.576 states) | 37.94s |
| Classical benchmark | 0.49s |
| Risk rerank + local polish | 6s |

QAOA 20-bit chưa hoàn tất:

- 3 seeds / shots 256 / maxiter 50 / warm-start: không xong sau hơn 15 phút.
- 1 seed / shots 128 / maxiter 10 / không warm-start: vẫn không xong sau hơn 13 phút.
- Cả hai tiến trình đã bị dừng; không ghi nhận kết quả QAOA giả hay cherry-pick.

Đường vận hành hiện tại dùng `--exact-only` và ghi trung thực
`requested_solver=qaoa`, `actual_solver=exact`, `NON_FINAL_CONFIG=true`. Exact fallback đã tạo đủ
`qubo_model.json`, `exact_solution.json`, `qaoa_results.json` (pool từ exact),
`workflow_benchmark.json`; Risk sau đó tạo `final_recommendation.json`.

## 10. Full pipeline exact-only — 2026-08-07 15:49 (UTC+7)

Lệnh:

```bash
/usr/bin/time -p uv run qshield-pipeline workflow-update \
  --config configs/base.yaml \
  --profile configs/profiles/workflow_update.yaml \
  --override configs/provisional/workflow_update_downstream.yaml \
  --quantum-mode exact
```

Kết quả: **6/6 chặng PASS**, `NON_BASELINE_RUN`, wall-clock chính xác **101,27 giây**
(1 phút 41,27 giây). Quantum workflow nội bộ mất **42,531 giây**:

- fit surrogate: `0,004s`
- consistency sampled: `2,444s` (`4.098` trạng thái kiểm tra; đây là counter, không phải giây)
- exact exhaustive 20-bit: `39,583s` (`1.048.576` trạng thái)
- QAOA: `0s` (exact-only fallback)
- classical benchmark: `0,500s`

Backend `/workflow/summary` đọc tươi toàn bộ artifact sau run: Data/Regime/Scenarios/Risk/QUBO/
Exact/Benchmark/Rerank/True-benchmark đều `READY` hoặc `PASS`; `actual_solver=exact`,
true CVaR `0,074239 → 0,061405`. Không tuyên bố quantum advantage.
