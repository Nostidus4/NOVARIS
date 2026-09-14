# Plan: QAOA-assisted Candidate Generation + Classical Polishing

Trạng thái: `DRAFT_RESEARCH_PROPOSAL` → mục tiêu `APPROVED_EXPERIMENT`. Nhãn kết quả: `EXPLORATORY_NON_BASELINE`
cho tới Gate H4.
Nguồn: `PHUONG_AN_QUANTUM_ASSISTED_CANDIDATE_GENERATION copy.md` + quyết định của Ngọc (13/09/2026).
Owner kỹ thuật: Tân (quantum/harness), Phúc (true objective/polish), Tú (instance/scenario), Minh Anh
(portfolio/data), Ngọc (scope/claim).

---

## 0. Tóm tắt quyết định

1. Vai trò Quantum đổi thành **bộ sinh ứng viên**: QAOA sinh phân phối bitstring → Risk chấm lại bằng true
   objective → cùng một classical polishing → nghiệm cuối. Classical-only vẫn là đường recommendation chính
   và fallback.
2. Câu hỏi nghiên cứu: *Trong cùng ngân sách ứng viên / ngân sách tính toán và cùng polishing, pool QAOA có
   cho nghiệm tài chính cuối (true CVaR sau chi phí) tốt hơn pool random/classical một cách ổn định không?*
3. Số 1,11% / 4,79% / 5,84% và 1,9% coverage là **exploratory, chưa xác minh** (không có artifact tái lập
   trong repo — `artifacts/dev/` hiện không có `optimization/`). Pha 0 phải dựng lại hoặc bác bỏ.
4. Lộ trình: 5 instance exploratory (16-bit, có ground truth) → sửa attribution/fairness → ≥30
   portfolio-date instance độc lập qua Normal/Volatile/Stress → nếu pass, thử Phương án B (QAOA giải
   neighborhood 8–16 bit trong bài 20-bit).
5. Pipeline sản phẩm `workflow_update` (top-10, 20-bit, rerank/polish) **không đổi hành vi** trong suốt
   plan này. Mọi thứ mới nằm ở track thí nghiệm riêng, bật bằng config riêng.

---

## 1. Hiện trạng code — những gì chặn attribution

Đã đọc code thật, không suy đoán:

| # | Vị trí | Vấn đề | Hệ quả với claim |
|---|---|---|---|
| C1 | `packages/quantum/src/qshield_quantum/workflow.py::_merge_candidate_pool` (dòng 402) | Pool khởi tạo bằng `exact.top_feasible_candidates` rồi mới thêm sample QAOA; sort theo energy và cắt `limit=20` | Pool đưa vào rerank/polish **bị nhiễm exact**. Không thể quy "QAOA + polish" cho QAOA |
| C2 | `solvers/qaoa.py::solve_qaoa_one_seed` (dòng 163–177) | `samples` chỉ giữ top-`candidate_pool_size` (mặc định 20) theo `fval` | Không tính được coverage/entropy/feasible mass từ artifact. 10 seed × 20 = tối đa 200 state = 0,3% của 2^16 → con số 1,9% **không thể** đến từ đường code hiện tại; phải tìm script gốc |
| C3 | `solvers/qaoa.py` | `feasibility_rate`, `success_prob` tính trên toàn distribution nhưng distribution bị vứt | Metric có nhưng không kiểm tra lại được |
| C4 | `workflow.py` dòng 249 | `reference_bitstring = exact.best_feasible_bitstring` truyền vào QAOA | Chỉ dùng tính `success_prob`, không ảnh hưởng tối ưu — nhưng phải ghi rõ và test không rò vào pool |
| C5 | `configs/workflow_update.yaml` `quantum.qaoa.warm_start: true` | Warm-start mặc định bật | Track "QAOA thuần" (T3) phải tắt; warm-start là track T5 riêng |
| C6 | `risk/rerank.py::polish_reductions` (dòng 181) | Không đếm số lần gọi `financial_objective`, không có budget, không có trace/stop reason | Không matched được evaluation budget giữa các track |
| C7 | `risk/rerank.py::polish_reductions` | Polish liên tục ±5pp, khóa zero-action, **không đổi active set** | Tốt cho attribution: active set của nghiệm cuối do bộ sinh quyết định. Giữ nguyên làm primary polish |
| C8 | `quantum/benchmark.py::coordinate_descent_classical` | Chạy trên **QUBO surrogate**, start gồm all-zeros/all-ones | Là baseline surrogate, không phải classical trên true objective. Cần thêm classical multistart trên true objective ở `risk` |
| C9 | `risk/true_benchmark.py::build_true_benchmark` | Chỉ chấm best-one-per-solver (`exact`/`qaoa`/`classical`) | Cần mở rộng lên pool-level |
| C10 | `contracts/enums.py::Stage` | Không có stage cho thí nghiệm hybrid | Cần `Stage.HYBRID` để `ArtifactPaths` sinh đường dẫn (quy tắc 8) |

---

## 2. Định nghĩa bắt buộc (khóa trước khi code)

### 2.1. Ba loại "optimum" — luôn báo cả ba, không bao giờ gọi chung là "optimum"

| Ký hiệu | Định nghĩa | Tính thế nào | Khả thi |
|---|---|---|---|
| `E*_qubo` | min QUBO surrogate energy trên lưới 4 mức, feasible | `solve_quadratic_exact` | 16-bit và 20-bit |
| `J*_grid` | min **true financial objective** trên lưới 4 mức (0/10/20/30%), feasible | brute-force `financial_objective_from_growth` (cache growth paths) trên mọi state | 16-bit chắc chắn (65.536 eval); 20-bit (1.048.576 eval) chỉ khi đo được thời gian chấp nhận được, nếu không thì dùng `J_best_known` |
| `J*_polished` | best-known true objective **sau polish** | polish từ top-K state của `J*_grid` (K khóa trong config) | Chỉ là reference, **không bao giờ** vào pool track khác |
| `J_best_known` | min trên union mọi track + reference ở instance đó | tính sau khi chạy xong | Dùng khi không có exact true objective; gắn nhãn `BEST_KNOWN` |

Gap (bài toán minimization — không viết "optimum cao hơn"):

```text
abs_gap(x)      = J(x) - J_ref
rel_gap(x)      = abs_gap(x) / max(|J_ref|, eps)        # eps khóa trong config
qubo_gap(x)     = E(x) - E*_qubo                         # chỉ để chẩn đoán surrogate
```

`raw gap` so với `J*_grid`; `polished gap` so với `J*_polished`. Báo **absolute gap + per-instance rank**
vì relative gap nhạy với scale/offset của objective.

### 2.2. Coverage — định nghĩa có numerator tuyệt đối

```text
unique_measured          = |{bitstring đo được, gộp mọi seed, mọi shot}|
unique_feasible          = |{... feasible}|
unique_effective_actions = |{decode + rounding → vector action, feasible}|   # dedup ngữ nghĩa
total_states             = 2^n
total_feasible_states    = đếm từ enumeration exact với cùng predicate feasibility
coverage_all             = unique_measured / total_states
coverage_feasible        = unique_feasible / total_feasible_states
feasible_mass            = Σ probability các state feasible (theo seed, rồi trung bình)
duplicate_rate           = 1 - unique_measured / total_shots
```

Luôn ghi dạng `1245 / 65536 (1,90%)`, không chỉ phần trăm. Duplicate giữa seed/shot đếm **một lần**.

### 2.3. Budget

- **Candidate budget `B`**: số `unique_effective_actions` feasible được chấm true objective. Mỗi track
  nộp đúng `B` (nếu không sinh đủ, ghi `shortfall` — không được bù bằng nguồn khác).
- **Polish budget**: polish top-`k_polish` ứng viên theo true objective của từng pool, mỗi lần polish tối đa
  `E_polish` lần gọi objective. Như nhau cho mọi track.
- **Compute budget `W`**: tổng wall-clock (sinh + chấm + polish) và trần tổng evaluation `E_total`. Wall
  time của QAOA gồm cả simulate + optimize COBYLA. Classical được dùng hết `W` để sinh thêm ứng viên.
- Mọi budget nằm trong `configs/experiments/hybrid_v1.yaml`, khóa hash trước khi chạy.

### 2.4. Instance

`portfolio-date instance` = (1 portfolio đầu vào, 1 as-of date) + regime tại date đó (filtered posterior,
không smoothed) + scenario set + policy/constraints. Nhiều scenario seed trên cùng portfolio-date **không**
là nhiều quan sát độc lập; seed QAOA trong cùng instance được trung bình trước khi thống kê.

---

## 3. Kiến trúc đích

```text
Instance manifest (portfolio, as-of date, regime, scenario seed, policy)
        │
        ▼
Risk: candidate selection (8 mã → 16-bit research | 10 mã → 20-bit) + QUBO handoff
        │
        ▼
Quantum: fit surrogate → verify/consistency.py (bắt buộc, quy tắc 15)
        │
        ├── T0 exact_reference   (E*_qubo; J*_grid, J*_polished do Risk tính) ──► CHỈ reference
        │
        ├── T1 classical_multistart_true  ┐
        ├── T2 random_uniform/stratified  │
        ├── T2b boltzmann_energy_matched  │  mỗi generator ghi pool RIÊNG
        ├── T3 qaoa_pure (warm_start=off) │  (raw distribution + provenance)
        ├── T4 classical_extra_compute    │
        └── T5 qaoa_warm_start            ┘
                        │
                        ▼
      Dedup theo effective action TRONG từng pool (không dedup chéo nguồn)
                        │
                        ▼
      Risk: compliance filter + true objective scoring (cùng code path, đếm eval)
                        │
                        ▼
      Risk: polish top-k_polish, cùng E_polish (trace từng lần polish)
                        │
                        ▼
      Pipeline: paired per-instance table → summary → claim checklist
```

Chiều phụ thuộc giữ nguyên quy tắc 11:
- Generator trên **bitstring/surrogate** (random, boltzmann, QAOA, classical trên QUBO) → `packages/quantum`.
- Scoring, polish, classical multistart trên **true objective**, `J*_grid` → `packages/risk` (không import
  quantum; nhận pool dạng DataFrame/list dict).
- Ghép track, budget, thống kê, ghi artifact qua `RunContext` → `packages/pipeline`.
- Schema → `packages/contracts`.

---

## 4. Pha 0 — Xác minh 3 câu hỏi của kết quả exploratory (Tân, Phúc review)

Mục tiêu: trả lời bằng artifact, không bằng slide. Không sửa số cũ; kết quả chạy lại đặt nhãn
`EXPLORATORY_NON_BASELINE` và lưu song song.

### 0.1. Truy nguồn thí nghiệm 5 danh mục

- [ ] Tìm commit/branch/script/notebook đã sinh 1,11% / 4,79% / 5,84% (không nằm ở `workflow.py` hiện tại —
      xem C2). Ghi vào `docs/experiments/hybrid_exploratory_provenance.md`: commit, lệnh, config, 5 portfolio
      definition, date, scenario seed, QAOA seeds/shots/p/maxiter/warm-start.
- [ ] Trả lời: 5 danh mục là thật có consent / synthetic trên dữ liệu thật / biến thể cùng portfolio-date.
- [ ] Trả lời: 3 con số là mean / median / best-of-run; lấy lại bảng per-instance × per-seed.
- [ ] Nếu không tìm được nguồn: ghi `NOT_REPRODUCIBLE` và coi 3 con số là giả thuyết, chuyển thẳng sang 0.2
      với code mới.

### 0.2. Câu hỏi 1 — 1,9% coverage tính thế nào?

- [ ] Chạy lại 5 instance với `export_full_distribution=True` (Pha 1 task Q1; có thể làm bản vá tối thiểu
      trước).
- [ ] Báo toàn bộ bảng §2.2 cho từng instance: numerator/denominator tuyệt đối.
- [ ] Sanity check: `unique_measured ≤ seeds × shots` (10 × 1024 = 10.240 → trần 15,6% của 2^16);
      `1,9% × 65.536 ≈ 1.245` state — kiểm tra có khớp `unique_measured`, `unique_feasible` hay
      `unique_effective_actions` không, hay là tổng *probability mass* bị đọc nhầm thành coverage.
- [ ] Xác định pool 1,9% có tính cả state infeasible và có đếm duplicate nhiều lần không.

### 0.3. Câu hỏi 2 — optimum là QUBO hay true financial objective?

- [ ] Tính cả `E*_qubo`, `J*_grid`, `J*_polished` cho 5 instance (Pha 2 task R4).
- [ ] Kiểm tra `argmin E` có trùng `argmin J` không; báo `surrogate_true_rank_of_qubo_optimum` và Spearman
      giữa energy và true objective trên toàn bộ 65.536 state.
- [ ] Tính lại gap 1,11/4,79/5,84 theo **cả hai** reference; ghi rõ số gốc đã dùng cái nào.
- [ ] Nếu gap cũ tính theo QUBO → claim chỉ là "surrogate quality", chưa phải giá trị tài chính.

### 0.4. Câu hỏi 3 — 1,11% có phụ thuộc chủ yếu vào polishing không?

Ablation trên 5 instance, mỗi track báo **cùng lúc**:

| Cột | Ý nghĩa |
|---|---|
| `raw_best_gap` | best trong pool trước polish, so `J*_grid` |
| `polished_best_gap` | best sau polish, so `J*_polished` |
| `polish_gain` | `J(raw_best) - J(polished_best)` |
| `polishing_dependency` | `(J_raw - J_polished) / (J_zero_action - J_polished)` (đã có trong `PolishingResult`) |
| `active_set_of_winner_from` | nguồn nào sinh active set của nghiệm cuối |
| `polished_from_rank` | nghiệm cuối được polish từ ứng viên rank mấy trong pool |

Diễn giải khóa trước:
- QAOA raw gap ≈ random raw gap nhưng thắng sau polish → lợi thế đến từ **basin/active set**, không phải
  từ chất lượng raw — vẫn là đóng góp candidate, nhưng phải nói đúng như vậy.
- Mọi track hội tụ về cùng nghiệm sau polish → QAOA **không** tạo giá trị tăng thêm.
- `polishing_dependency` > 0,5 ở track QAOA → phần lớn cải thiện thuộc classical; báo trung thực.
- Kiểm tra chéo: polish từ `no_action`/`greedy` (có sẵn trong `build_financial_baselines`) cùng
  `E_polish` — nếu đạt gần 1,11% thì QAOA không cần thiết.

### 0.5. Kiểm tra contamination trên kết quả cũ

- [ ] Nếu pool 1,11% được dựng bằng `_merge_candidate_pool` hoặc tương tự → đánh dấu
      `EXACT_CONTAMINATED`, liệt kê bitstring trong pool trùng `exact.top_feasible_candidates`, và coi số
      cũ là không hợp lệ cho attribution.

**Đầu ra Pha 0:** `hybrid_exploratory_reverify.json` + `hybrid_exploratory_per_instance.csv` + provenance md.
**Gate H0 (Reproducibility)** pass khi mọi mục trên có artifact kèm hash.

---

## 5. Pha 1 — Contracts, distribution lossless, pool tách nguồn (Tân)

### Contracts (`packages/contracts`)

- [ ] **K1** `enums.py`: thêm `Stage.HYBRID`; `paths.py::_STAGE_DIR[Stage.HYBRID] = "hybrid"`. Test path cho
      cả mode `dev` và `runs`.
- [ ] **K2** `schemas/hybrid.py` (mới), mỗi schema có `validate_or_raise()`:
  - `QaoaDistributionRow`: `experiment_id, instance_id, run_id, seed, bitstring, qubo_energy, probability,
    measured_count, feasible, shots, p, optimizer, maxiter, backend, warm_start, transpiled,
    candidate_order_hash, action_map_hash, qubo_hash`.
    Check: `Σ probability theo (instance, seed) ∈ [1 - tol, 1 + tol]` hoặc có `retained_probability_mass` và
    cờ `truncated=True`; độ dài bitstring = `2 × n_candidates`; hash đồng nhất trong một instance.
  - `CandidatePoolRow`: `experiment_id, instance_id, track, source_method, source_seed, source_rank,
    raw_probability, qubo_energy, bitstring, effective_action_hash, is_duplicate_after_decode,
    constraint_status, constraint_reasons, true_objective_before_polish, true_cvar_before_polish,
    transaction_cost, return_sacrifice, generation_wall_seconds` + 3 hash.
    Check: `track ≠ T0` ⇒ `source_method ≠ "exact"`; `(instance, track, effective_action_hash)` unique khi
    `is_duplicate_after_decode=False`.
  - `PolishTraceRow`: `source_method, start_candidate_hash, start_true_objective, final_candidate_hash,
    final_true_objective, objective_improvement, true_objective_evaluations, iterations, wall_seconds,
    active_set_changed, zero_action_lock_respected, max_adjustment_respected, stop_reason`
    (`converged | eval_budget | wall_budget`).
  - `HybridInstanceResult` + `HybridSummary` + `HybridManifest` (instance list, budgets, seeds, config hash,
    code commit, `uv.lock` hash, machine manifest).
- [ ] **K3** `hashing.py` (hoặc mở rộng module hash sẵn có): `portfolio_hash`, `scenario_hash`,
      `action_map_hash`, `effective_action_hash(levels, rounding)` — một chỗ duy nhất.
- [ ] **K4** `mocks/`: sinh mock đúng schema cho 3 artifact trên để Pha 2/3 làm song song.

### Quantum (`packages/quantum`)

- [ ] **Q1** `solvers/qaoa.py`: thêm tham số `export_full_distribution: bool = False`. Khi bật, thêm field
      `distribution: tuple[QaoaSample, ...]` vào `QaoaSeedResult` chứa **mọi** state đo được (≤ shots state;
      pickle qua subprocess vẫn nhỏ). Giữ `samples` top-20 như cũ để không vỡ `workflow_update`. Thêm
      `measured_count` = round(prob × shots).
- [ ] **Q2** `generators/` (mới) — mỗi generator là hàm thuần, nhận `model`, `feasibility`, `budget`, `seed`,
      trả `list[dict]` đúng `CandidatePoolRow` (chưa có true objective):
  - `qaoa_pool.py` — gọi `solve_qaoa_one_seed_fast(..., warm_start=cfg, export_full_distribution=True)`,
    **không** truyền exact vào pool; `reference_bitstring` chỉ để tính `success_prob` và không ghi vào pool.
    Chọn `B` ứng viên theo luật khóa trước: gộp distribution mọi seed → dedup effective action → xếp theo
    `measured_count` giảm dần (tie: energy, bitstring). Báo cả view "xếp theo energy" như phụ.
  - `random_pool.py` — uniform trên feasible domain (rejection sampling với cùng predicate) + stratified theo
    (số mã active, tổng %). Seed đăng ký trước.
  - `boltzmann_pool.py` — **control quan trọng**: lấy mẫu từ `p(x) ∝ exp(-β E(x))` trên state feasible, với β
    fit để phân phối energy khớp distribution QAOA (khớp median energy). Nếu QAOA ≈ Boltzmann thì QAOA chỉ
    đang "tập trung vào energy thấp", không có cấu trúc riêng. Ở 16-bit enumerate được; 20-bit dùng MCMC.
  - `classical_surrogate_pool.py` — bọc `coordinate_descent_classical`/simulated annealing trên QUBO, thu
    **tất cả** local minima khác nhau làm pool (không chỉ best).
- [ ] **Q3** `hybrid/pools.py`: `dedup_by_effective_action(rows)` trong phạm vi một track; `build_source_pools`
      trả dict `{track: rows}`. `_merge_candidate_pool` giữ nguyên cho sản phẩm nhưng docstring ghi rõ "không
      dùng cho attribution".
- [ ] **Q4** `verify/hybrid_attribution.py`: hard-fail nếu bất kỳ bitstring nào trong T1–T5 có
      `source_method == "exact"`, hoặc hash lệch giữa pool và QUBO. Không kiểm tra "trùng exact optimum" như
      lỗi — QAOA được phép tìm ra nó — chỉ kiểm tra **provenance**.

### Test Pha 1

- `test_qaoa_distribution.py`: Σ prob ≈ 1 mỗi seed; mọi state có `measured_count ≥ 1`; endian khớp
  `decode_action_levels` (`'10'→10`, `'01'→20`); đường `export_full_distribution=False` cho kết quả y hệt cũ.
- `test_pools.py`: cùng bitstring từ 2 seed dedup còn 1; hai bitstring cùng effective action dedup còn 1;
  thêm sample trùng không tăng `unique_*`; đảo thứ tự input không đổi tập action.
- `test_hybrid_attribution.py`: inject exact vào T3 → raise; pool rỗng feasible → trả `shortfall`, không
  "success" giả.
- `test_generators_random.py`: cùng seed ⇒ cùng pool; mọi state feasible; stratified đủ strata.

**Gate H1 (Attribution)** pass khi Q1–Q4 + test xanh và exact chỉ xuất hiện ở `exact_reference.parquet`.

---

## 6. Pha 2 — Pool-level true objective, polish có budget (Phúc, Tân review)

- [ ] **R1** `rerank.py::polish_reductions`: thêm `max_evaluations: int | None = None`,
      `max_wall_seconds: float | None = None`; đếm mọi lần gọi `financial_objective`; trả thêm
      `evaluations, iterations, wall_seconds, stop_reason` trong `PolishingResult` (field mới có default —
      không đổi call site sản phẩm). Test: budget cắt đúng; `evaluations ≥ 0`; zero-lock/±5pp vẫn giữ.
- [ ] **R2** Chuyển polish và scoring sang `financial_objective_from_growth` với growth paths tính một lần
      mỗi instance (cùng kết quả, nhanh hơn). Test so khớp tuyệt đối với `financial_objective`.
- [ ] **R3** `hybrid_benchmark.py` (mới, trong `qshield_risk`):
  - `score_pool(rows, ...) -> DataFrame` — cùng code path với `rerank_candidates` (tái dùng, không copy công
    thức), giữ `track/source_*`, trả `true_objective, true_cvar (95%), cvar_975, cvar_99, transaction_cost,
    liquidity_penalty, turnover, cash_after, return_sacrifice, worst_drawdown, constraint_violations`.
  - `polish_pool(scored, k_polish, E_polish)` → `PolishTraceRow` list.
  - `instance_result(pools, reference)` → pre/post gap từng track, winner origin, `polishing_dependency`.
- [ ] **R4** `exact_true_reference.py`: brute-force `J*_grid` trên lưới 4 mức (vectorize theo batch state) +
      `J*_polished` từ top-K. Đo thời gian ở 16-bit trước; nếu 20-bit ước tính > ngưỡng config thì trả
      `J_best_known` với nhãn rõ.
- [ ] **R5** `classical_true_multistart.py`: coordinate descent 4 mức trên **true objective** (mở rộng
      `_coordinate_descent_minimize` để nhận start tùy ý + budget), start random có seed. Đây là T1/T4 mạnh —
      không được tune sơ sài.

### Test Pha 2 (test suite quan trọng nhất — quy tắc code)

- Ví dụ tay 3 mã × 5 scenario: `score_pool` khớp CVaR tính tay (Rockafellar–Uryasev, loss dương).
- `polish` từ cùng start cho cùng kết quả bất kể track nào gọi (fairness test).
- Pre/post reconcile: `J_raw - J_polished == objective_improvement`.
- Source tag sống sót qua scoring → polish → winner.
- `J*_grid ≤ J(x)` với mọi x feasible trên lưới (test 8-bit enumerate).

---

## 7. Pha 3 — Fair harness hai view (Tân, Phúc review)

- [ ] **P1** `configs/experiments/hybrid_v1.yaml` (extends base + workflow_update): tracks, `B` ∈ {64, 256,
      1024}, `k_polish`, `E_polish`, `W`, `E_total`, QAOA `{p, shots, maxiter, seeds}`, random seeds,
      β-matching rule, tie tolerance, materiality threshold, `eps`, instance manifest path. File này chính là
      preregistration; `config_hash` ghi vào manifest.
- [ ] **P2** `packages/pipeline/src/qshield_pipeline/hybrid.py`: orchestrator
      `run_hybrid_instance(instance, cfg, ctx)` và `run_hybrid_experiment(manifest, cfg, ctx)`; mỗi instance
      chạy trong try/except ghi `hybrid_attempts.jsonl` (crash/timeout **được giữ**, không lọc).
- [ ] **P3** CLI: `uv run qshield-pipeline hybrid --config configs/experiments/hybrid_v1.yaml --set exploratory`
      (và `--set confirmation`). Resume theo `instance_id` đã xong.
- [ ] **P4** Candidate-budget view: mọi track nộp đúng `B` unique feasible effective actions.
- [ ] **P5** Compute-budget view: đo wall-time T3 (sinh + chấm + polish); T4 dùng đúng `W` đó cho classical
      multistart trên true objective; T2 dùng đúng `W` cho random. Báo số ứng viên thực tạo được mỗi track.
- [ ] **P6** Forced-timeout test: QAOA timeout ⇒ T1/T2/T4 vẫn ra kết quả; `attempted_solver=qaoa`,
      `actual_solver` đúng; instance **không** bị loại khỏi thống kê (tính là thua của T3).
- [ ] **P7** Track T5 warm-start chạy riêng, báo riêng, không gộp với T3.

### Ma trận track

| Track | Nguồn | Polish | Vai trò |
|---|---|---|---|
| T0 | exact QUBO + `J*_grid` + `J*_polished` | reference only | Không seed track nào |
| T1 | classical multistart trên true objective, budget như T3 | same | Baseline trực tiếp |
| T2 | uniform + stratified random feasible | same | "Chỉ là nhiều điểm bắt đầu" |
| T2b | Boltzmann khớp energy với QAOA | same | "Chỉ là tập trung energy thấp" |
| T3 | QAOA thuần (`warm_start=false`) | same | Đối tượng thử nghiệm |
| T4 | classical dùng thêm compute bằng QAOA | same | "Chỉ là thêm ngân sách" |
| T5 | QAOA warm-start | same | Nhánh hybrid khác |
| T6 (ablation) | polish từ `no_action` / `greedy` | same | "Polish tự làm hết" |

### Artifact đầu ra (qua `ArtifactPaths.for_stage(Stage.HYBRID, ...)`)

```text
hybrid/
  hybrid_benchmark_manifest.json
  instances/{instance_id}/
    qaoa_distribution.parquet
    candidate_pools/exact_reference.parquet
    candidate_pools/{track}_raw.parquet
    candidate_pools/{track}_unique_feasible.parquet
    polishing_results.parquet
    instance_result.json
  hybrid_benchmark_per_instance.csv
  hybrid_benchmark_summary.json
  hybrid_attempts.jsonl
  hybrid_claim_checklist.json
```

Mọi file mang `portfolio_hash, scenario_hash, candidate_order_hash, action_map_hash, qubo_hash, code_commit,
lock_hash, machine_manifest`. Chỉ `RunContext` ghi `config.json/metrics.json/logs.txt` (quy tắc 13).

**Gate H2 (Fairness)** pass khi cả hai view chạy trên 5 instance exploratory, T1/T4 đạt ít nhất chất lượng
của `coordinate_descent_classical` hiện tại, và không có instance/seed nào bị loại khỏi `hybrid_attempts`.

---

## 8. Metric báo cáo

### 8.1. Trước polish (chất lượng bộ sinh)

`unique_feasible`, `coverage_all`, `coverage_feasible`, `feasible_mass`, `duplicate_rate`, Shannon entropy và
effective sample size `1/Σp²`, top-k probability mass, `raw_best_gap` (true + qubo), `near_optimal_rate(ε)`
với ε ∈ {0,5%, 1%, 2%}, recall true top-k (k ∈ {10, 50}) khi có `J*_grid`, Hamming/action diversity trung bình
cặp, novelty so với pool T1 (tỉ lệ action không có trong T1).

### 8.2. Sau polish (giá trị tăng thêm)

```text
hybrid_uplift_vs_X = J(best_final_X) - J(best_final_T3)     # > 0: T3 tốt hơn, X ∈ {T1, T2, T2b, T4}
```

`polished_best_gap`, `polish_gain`, `polishing_dependency`, win/tie/loss (tie khi |uplift| ≤ tie tolerance),
evaluations, wall time, peak RAM, error/timeout rate, winner source, ổn định qua QAOA seed (std gap).

### 8.3. Tài chính (Phúc chấm, primary không dùng energy)

CVaR 95% (primary), CVaR 97,5%/99%, return sacrifice, transaction cost + liquidity, turnover, cash after,
worst drawdown, hard-constraint violations, materiality `materiality_from_cvar` (đã có). Tổng tỷ trọng = 1.0
(quy tắc 6) được assert cho mọi nghiệm cuối.

---

## 9. Pha 4 — Mở rộng ≥30 portfolio-date và thống kê (Tú + Minh Anh + Tân)

### 9.1. Sinh instance (luật khóa trước, không chọn tay sau khi nhìn kết quả)

- [ ] **I1** Minh Anh: 6 archetype portfolio synthetic trên dữ liệu thật — diversified, banking-concentrated,
      high-volatility, high-cash, do-not-sell, liquidity-constrained. Gắn nhãn `SYNTHETIC_ON_REAL_DATA`.
- [ ] **I2** Tú: chọn as-of date theo luật từ `regime_daily.parquet` (filtered posterior, không smoothed):
      trong mỗi regime, lấy date có xác suất regime ≥ ngưỡng config, cách nhau ≥ `min_gap_days` (≥ horizon 20
      ngày) để giảm phụ thuộc. Mục tiêu ≥ 5 date × regime, ghép archetype theo vòng tròn khóa bằng seed →
      **≥ 30 instance**, cân bằng Normal/Volatile/Stress.
- [ ] **I3** Regime nào chưa qua Scenario Gate → instance đó chạy nhưng gắn `SCENARIO_GATE_NOT_PASSED`, báo
      riêng, không gộp vào kết luận confirmation. Nếu còn < 30 instance hợp lệ → kết luận `INCONCLUSIVE`,
      không hạ gate.
- [ ] **I4** Tách tập: 5 instance cũ = `EXPLORATORY_SET` (được tune); ≥30 mới = `CONFIRMATION_SET` (không
      tune). Hash danh sách confirmation **commit trước khi chạy**.

### 9.2. Thống kê (khóa trong `hybrid_v1.yaml`)

- Đơn vị quan sát = instance. Trong instance: trung bình qua QAOA seed / random seed trước.
- Primary: median paired `hybrid_uplift_vs_T1` trên true objective sau polish, candidate-budget view.
- Test: Wilcoxon signed-rank **hai phía**; 95% CI bằng paired bootstrap trên instance (≥ 10.000 resample, seed
  cố định). Sign test báo phụ.
- So sánh phụ T3 vs T2, T2b, T4: Holm correction.
- Báo theo regime (descriptive, không test riêng nếu mỗi nhóm < 10).
- Không dùng số scenario (hàng nghìn) làm n.

**Gate H3 (Distribution signal)** — exploratory: T3 raw gap/recall tốt hơn T2 **và** T2b trên exploratory set.
**Gate H4 (Confirmation)** — trên confirmation set: median uplift vs T1 > 0 và ≥ materiality, 95% CI không
chứa 0, T3 không thua T2b, không tăng constraint violation, và compute-budget view không thua nghiêm trọng
(ngưỡng khóa trong config).
**Gate H5 (Product value)** — cải thiện true CVaR sau chi phí so với T1/T4 với latency/failure trong policy.
**Gate H6** — dù pass, chỉ gọi là "QAOA-assisted hybrid contribution trên simulator". Không "quantum advantage".

---

## 10. Pha 5 — Phương án B: QAOA giải neighborhood 8–16 bit trong bài 20-bit (chỉ khi H2 pass)

```text
Classical master x⁰ (T1 winner trên 20-bit, true objective)
→ chọn subset S gồm m mã (m ∈ {4, 6, 8} → 8/12/16 bit) theo luật đăng ký
→ cố định biến ngoài S, dựng QUBO con (surrogate đã fit, chỉ condition — không fit lại)
→ generator sinh ứng viên trên 2m bit
→ nhúng lại vào 20-bit → true objective → polish (cùng budget)
→ lặp tối đa R vòng hoặc hết budget
```

- [ ] **N1** `quantum/formulation/neighborhood.py`: `condition_qubo(model, fixed_bits, free_idx)` → QUBO con;
      test: energy con + hằng số = energy full trên mọi state 8-bit (enumerate).
- [ ] **N2** Luật chọn S (khóa trước, không dùng thông tin exact/winner tương lai): (a) m mã có marginal
      CVaR contribution cao nhất tại x⁰; (b) m mã ngẫu nhiên có seed; (c) m mã có |gradient surrogate| lớn
      nhất. Báo cả ba.
- [ ] **N3** Tracks: NB-QAOA, NB-random, NB-Boltzmann, NB-exact-sub (exact 16-bit con rẻ — là control mạnh),
      NB-classical. Cùng decomposition, cùng R, cùng polish.
- [ ] **N4** Báo full 20-bit objective + **toàn bộ** compute (master + mọi vòng), không báo energy con.
- [ ] **N5** Diễn giải: nếu NB-exact-sub ≥ NB-QAOA → giá trị nằm ở decomposition, không ở QAOA.

---

## 11. Pha 6 — Tích hợp sản phẩm có kiểm soát (chỉ khi H4 + H5 pass)

- Classical-only luôn là recommendation chính; QAOA chạy async có timeout (`performance_budget` đã có).
- Candidate QAOA chỉ vào pool sản phẩm khi hash/gate hợp lệ; pool sản phẩm vẫn qua rerank + polish (quy tắc 17).
- Backend chỉ đọc artifact hybrid; frontend hiện `candidate source`, `classical polished`, `simulator`,
  `status/fallback` trong 5 khu vực dashboard có sẵn — không thêm chart mới (đóng băng phạm vi).
- Nếu H4/H5 không pass: không tăng latency flow người dùng; ghi kết luận "Quantum được tích hợp và đánh giá
  nghiêm túc nhưng chưa tạo incremental decision value ở scope hiện tại".

---

## 12. Lịch và phân công (ước tính person-day; đo lại sau Pha 0)

| Pha | Việc | Owner | Reviewer | Ước tính | Phụ thuộc |
|---|---|---|---|---|---|
| 0 | Truy nguồn + reverify 3 câu hỏi | Tân | Phúc | 1,5 | bản vá Q1 tối thiểu, R4 16-bit |
| 1 | K1–K4, Q1–Q4 + test | Tân | Phúc | 2,5 | — (dùng mock) |
| 2 | R1–R5 + test | Phúc | Tân, Ngọc | 2,5 | K2 (mock đủ) |
| 3 | P1–P7, chạy 5 instance hai view | Tân | Phúc | 2 | Pha 1, 2 |
| 4a | I1–I4 manifest confirmation | Minh Anh, Tú | Phúc, Ngọc | 1,5 | song song Pha 1–3 |
| 4b | Chạy + thống kê confirmation | Tân | Phúc, Ngọc | 1 + compute | Pha 3, 4a |
| 5 | Phương án B | Tân | Phúc | 3 | H2 pass |
| 6 | Tích hợp sản phẩm | Tân, Ngọc | Ngọc | 2 | H4, H5 pass |

Ước tính compute cần đo ở Pha 0 và ghi vào manifest: thời gian 1 seed QAOA 16-bit / 20-bit (p=1, 1024 shots),
thời gian 1 lần `financial_objective_from_growth` với cube `(5000, 20, 30)`, thời gian `J*_grid` 16-bit.
Nếu ≥30 instance × 7 track × 10 seed vượt ngân sách máy, giảm `B`/số seed **trước** khi chạy confirmation
(đổi config = experiment version mới), không cắt instance.

---

## 13. Checklist trả lời Ngọc (điền bằng đường dẫn artifact)

- [ ] Artifact + lệnh chạy lại 5 instance (hoặc `NOT_REPRODUCIBLE`)
- [ ] Optimum gốc là QUBO hay true objective; gap tính lại theo cả hai
- [ ] Numerator/denominator tuyệt đối của 1,9% (all / feasible / effective action)
- [ ] Xác nhận pool 1,11% có/không chứa exact candidate
- [ ] Bảng per-instance raw → polished cho T1, T2, T2b, T3 (+T6 ablation)
- [ ] `polishing_dependency` và nguồn active set của winner mỗi instance
- [ ] Candidate count, evaluations, polish iterations, wall time, RAM từng track
- [ ] Cả candidate-budget và compute-budget view
- [ ] Confirmation manifest ≥30 instance đã hash và commit trước khi chạy
- [ ] Ghi rõ backend `StatevectorSampler` (simulator), không claim quantum advantage

---

## 14. Rủi ro và cách xử lý

| Rủi ro | Dấu hiệu | Xử lý |
|---|---|---|
| Surrogate lệch true objective | Spearman(E, J) thấp; argmin E ≠ argmin J | Báo trước; QAOA tối ưu surrogate sai thì không kỳ vọng uplift — sửa surrogate ở Risk handoff, không tune QAOA |
| Polish san bằng mọi track | `polished_best_gap` như nhau | Kết luận "không có giá trị tăng thêm", báo trung thực |
| QAOA ≈ Boltzmann | T3 ≈ T2b ở mọi metric | Claim chỉ còn "sampler energy-biased", không phải cấu trúc lượng tử |
| 20-bit QAOA quá chậm/timeout | `hybrid_attempts` nhiều timeout | Giữ timeout vào thống kê; chuyển trọng tâm sang Phương án B |
| Không đủ 30 instance hợp lệ (Stress chưa qua gate) | I3 | `INCONCLUSIVE`, báo n thật |
| Tune lén trên confirmation | config hash đổi sau khi chạy | Manifest hash hard-fail; đổi = version mới |
| Qiskit crash flaky ở subprocess | exit code ≠ 0 | Đã có retry trong `solve_qaoa_one_seed_fast`; ghi số retry vào attempt log |

---

## 15. Không làm trong plan này

- Không đổi hành vi `workflow_update` sản phẩm, không đổi action level 0/10/20/30%, không vượt 30 mã VN30.
- Không chạy hardware thật (`backends/hardware.py` giữ trống).
- Không xóa/ghi đè benchmark cũ ("QAOA không thắng classical trực tiếp" vẫn là kết quả hợp lệ).
- Không dùng kiểm định một phía, không chọn seed/portfolio sau khi nhìn kết quả.
- Không viết "Quantum tìm optimum cao hơn", "QAOA thắng classical" (khi thắng sau polish không attribution),
  "5 danh mục thật" (nếu synthetic), "quantum advantage/speedup".
