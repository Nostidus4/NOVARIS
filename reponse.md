# Q-SHIELD / NOVARIS — Technical Review

**Reviewer roles:** Senior System Architect · Quantitative Risk Reviewer · Quantum Optimization Reviewer
**Ngày review:** 2026-09-03 · **Branch:** `staging-tan-dev` · **HEAD:** `380974a`
**Cơ sở review:** source code + artifact thực tế trong repo. Không suy đoán chức năng không có trong code.
**Đã chạy để lấy bằng chứng:** `pytest` từng package, đọc trực tiếp `artifacts/dev/**`, `artifacts/runs/**`, `artifacts_bench/**`.

---

> **CẬP NHẬT 2026-09-04.** Tài liệu này gồm review gốc (§1–§10) và các phụ lục ghi theo trình tự
> thời gian (D–J). **Bảy kết luận trong §1–§10 đã được đính chính** bằng số đo mới — xem bảng
> J.5. Muốn nắm nhanh "đã làm gì, số liệu nào": đọc **Phụ lục J** trước, nó gộp toàn bộ.
>
> Chốt trạng thái: **486 test pass, 0 fail** · ruff sạch · không tham số tài chính nào bị đổi.
>
> Phụ lục K bổ sung benchmark có **đối chứng null** — kết quả có lợi cho nhánh quantum hơn mọi
> phụ lục trước, và nó lật lại một dự đoán của chính reviewer.

## 0. Tóm tắt điều hành (đọc trước nếu chỉ có 3 phút)

1. **Kiến trúc rất tốt.** Tách stage, contracts-first, provenance/hash, exact-as-ground-truth, rerank bằng true CVaR, fallback trung thực `requested_solver` vs `actual_solver` — đây là mức kỷ luật hiếm thấy ở prototype 7 ngày.
2. **Nhưng bài toán tối ưu hiện tại là degenerate.** Trên 711 mẫu train thật (`artifacts/dev/risk/qubo_objective_samples.parquet`), tương quan giữa `objective` và tổng mức bán `reduction_sum` là **−0,9993**. Hàm mục tiêu gần như **tuyến tính đơn điệu** theo tổng lượng bán ⇒ nghiệm tối ưu luôn là **all-ones** (bán 30% cả 10 mã). Exact, classical local-search và QAOA đều ra cùng một đáp án. Không có cấu trúc tổ hợp để giải.
3. **Nguyên nhân gốc đã định vị được chính xác:** thành phần `cash_budget_deviation` (weight 0.35 / scale 0.1) có biên độ **0,303** trên toàn tập mẫu, trong khi CVaR chỉ **0,112**. Target cash `0.1` đúng bằng lượng tiền tối đa có thể tạo ra từ 10 mã × 3,33% weight × 30%. Nghĩa là **chỉ có duy nhất một nghiệm** đưa deviation về ~0: all-ones.
4. **Trên đường sản phẩm, QAOA hiện không chạy.** `pipeline/run.py:212` mặc định `quantum_mode="exact"`; backend `subprocess_optimize_runner.py:88` hard-code `--exact-only`; profile `configs/workflow_update.yaml:330-336` bật `dev_mode` (1 seed, 128 shots, maxiter 10). Mọi artifact 20-bit trong repo đều có `actual_solver: "exact"`, `qaoa_seed_count: 0`.
5. **Có 4 gate được ghi PASS trong khi bằng chứng bên dưới là FAIL/thiếu** — đây là rủi ro trung thực lớn nhất, chi tiết ở P0-1..P0-4.
6. Chính team đã tự phát hiện vấn đề (2) trong `tools/qaoa_stress_bakeoff.py:6-8): *"the real cash-hedge QUBO is nearly linear (corner optimum all-1s), so exact == classical and solvers cannot be distinguished"*. Review này xác nhận nhận định đó bằng số và mở rộng nguyên nhân.

---

## 1. Tóm tắt hệ thống hiện tại — data flow thực tế

### 1.1 Sơ đồ đường đi thật (không phải sơ đồ trong plan)

```
[1] Data ingestion            packages/data/src/qshield_data/loader.py, returns.py
      ↓
[2] Point-in-time eligibility packages/data/src/qshield_data/eligibility.py:22-60
      ↓
[3] Feature engineering       packages/data/src/qshield_data/features.py
                              packages/ai/src/qshield_ai/regime/feature_set.py
      ↓
[4] Regime (HMM 3-state)      packages/ai/src/qshield_ai/regime/train.py:153-165
      label theo thống kê     packages/ai/src/qshield_ai/regime/labeling.py:1-30
      ↓
[5] Scenario (moving-block)   packages/ai/src/qshield_ai/scenarios/bootstrap.py
      validate 10 metric      packages/ai/src/qshield_ai/scenarios/validate.py:341-348
      ↓
[6] Baseline risk / CVaR      packages/risk/src/qshield_risk/metrics.py, paths.py
      ↓
[7] Candidate selection 30→10 packages/risk/src/qshield_risk/candidates.py
      + candidate gate        packages/risk/src/qshield_risk/candidate_gate.py:76-202
      ↓
[8] Objective sampling        packages/risk/src/qshield_risk/sampling.py:277-424
      (211 structured + 500 random train | 500 val | 1000 holdout)
      ↓
[9] Quadratic surrogate       packages/quantum/.../formulation/surrogate.py:154-195
      ↓
[10] QuadraticProgram/QUBO    packages/quantum/.../formulation/qiskit_program.py:23-53
      + verify 3 đường tính   packages/quantum/.../verify/consistency.py:46-115
      ↓
[11] Solvers
      exact  (2^20 duyệt hết) packages/quantum/.../solvers/exact.py:100-159
      classical (multi-start) packages/quantum/.../benchmark.py:122-172
      QAOA   (StatevectorSim) packages/quantum/.../solvers/qaoa.py:90-178
      ↓
[12] True financial rerank    packages/risk/src/qshield_risk/rerank.py:46-165
[13] Local polishing ±5pp     packages/risk/src/qshield_risk/rerank.py:181-304
      ↓
[14] final_recommendation     packages/risk/src/qshield_risk/cli.py:1213-1265
[15] true_benchmark.json      packages/risk/src/qshield_risk/true_benchmark.py
      ↓
[16] Backend (read-only)      backend/src/qshield_api/application/console/assemble.py
      ↓
[17] Frontend Next.js         frontend/app/(console)/*
```

### 1.2 Trạng thái từng component

| # | Component | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1 | Data ingestion | **IMPLEMENTED** | `packages/data/` 62/62 test pass; `data/processed/*.parquet` tồn tại |
| 2 | PIT eligibility | **IMPLEMENTED** | `eligibility.py:22-60`; `data/processed/eligibility_daily.parquet`; reason_code đầy đủ |
| 3 | Feature engineering | **IMPLEMENTED** | `features.py`; `market_features.parquet` |
| 4 | Regime HMM | **IMPLEMENTED** | `train.py:153-165` dùng `filtered` (nhân quả); `labeling.py` xếp hạng thống kê đúng quy tắc 7; `artifacts/dev/regime/regime_daily.parquet` |
| 5 | Scenario generation | **PARTIAL** | Cube 5000×20×30 tồn tại, nhưng regime **stress bị skip vì pool rỗng** (`scenario_manifest.json: skipped_regimes.stress`), 5000 kịch bản chỉ từ **71 block độc nhất** (`reuse_rate: 0.99645`) |
| 6 | Baseline risk / CVaR | **IMPLEMENTED** | `metrics.py`; test tay `packages/risk/tests/test_cvar_by_hand.py` |
| 7 | Candidate selection + gate | **IMPLEMENTED (gate FAIL)** | `candidate_gate.json: status=FAIL, coverage=0.599 < 0.70, STABILITY_NOT_EVALUATED` |
| 8 | Objective sampling | **IMPLEMENTED** | 711 dòng train trong parquet, split hash + no-overlap check `sampling.py:389-391` |
| 9 | Surrogate fit | **IMPLEMENTED nhưng UNVALIDATED** | `surrogate.py:154-195` fit OK, rank-deficiency check tốt — **nhưng không có code nào chấm surrogate trên validation/holdout** |
| 10 | QUBO + verify | **IMPLEMENTED** | `verify/consistency.py`; artifact ghi `verify_checked_states: 4098` (sampled, không phải full 2^20) |
| 11a | Exact solver | **IMPLEMENTED** | `exact_evaluated_states: 1048576`, runtime ~38s |
| 11b | Classical baseline | **PARTIAL / không matched budget** | `coordinate_descent_classical` 64 restarts, chạy 0,56s vs QAOA budget 600s/seed |
| 11c | QAOA 20-bit | **UNVERIFIED trên đường sản phẩm** | Mọi artifact 20-bit: `qaoa_seed_count: 0`, `actual_solver: "exact"`. QAOA 10-bit có chạy thật trong `artifacts_bench/` |
| 12 | True rerank | **IMPLEMENTED** | `rerank.py:46-165`; `reranked_candidates.csv` (đã bị xoá trong working tree, có trong `artifacts_bench/`) |
| 13 | Local polishing | **IMPLEMENTED** | `rerank.py:181-304`, zero-lock + bound assertion runtime |
| 14 | final_recommendation | **IMPLEMENTED** | `cli.py:1213-1265` |
| 15 | true_benchmark | **IMPLEMENTED** | `artifacts_bench/*/true_benchmark.json` đầy đủ 3 solver |
| 16 | Backend | **PARTIAL** | Đọc artifact đúng, nhưng `weights` client gửi lên **không được dùng** |
| 17 | Frontend | **IMPLEMENTED** | 7 trang console + landing |
| — | Surrogate validation gate | **PLANNED** | Config có ngưỡng (`workflow_update.yaml:618-629`) + `gates.surrogate_validation_required_before_solver: true` (`:655`) — **không có dòng code nào** |
| — | Walk-forward / UAT | **PLANNED** | Không có harness trong repo |
| — | Backend personalization | **CONTRADICTED** | Xem §2 và P0-5 |

---

## 2. Đối chiếu plan.md ↔ source code

### 2.1 Bảng trạng thái theo từng quyết định

| plan.md | Nội dung | Trạng thái | Bằng chứng (file:line) |
|---|---|---|---|
| **§1** | Evidence chỉ là ANALYSIS_ONLY / chưa nghiệm thu | **IMPLEMENTED** | `configs/workflow_update.yaml:7` `status: NON_BASELINE_RUN`; `risk/cli.py:783` `handoff_status: "ANALYSIS_ONLY_NON_BASELINE_RUN"`; `run.py:224-228` chặn nếu status ≠ NON_BASELINE_RUN |
| **§1** | Quantum là nhánh tạo ứng viên, không bắt buộc | **IMPLEMENTED** | `workflow.py:296-299` fallback exact; `benchmark.py:250-300` payload fallback đầy đủ |
| **R01** | Đối chiếu raw→clean→returns từng dòng | **PLANNED** | `reports/adjusted_close_evidence_report.csv` có, nhưng không có code phân loại 5 disposition (`confirmed_vendor` / `transform` / `corporate_action` / …) |
| **R02** | TCB 11/06 — giữ raw, mở điều tra corporate action | **PARTIAL** | `packages/data/tests/test_corporate_actions.py` có; không có registry disposition per-ticker |
| **R03** | Xuất `fit_start/end`, `validation_*`, `test_*`, scaler-fit range | **PARTIAL** | `configs/workflow_update.yaml:82-87` khai báo range; `train.py:4-8` xác nhận dùng `filtered` (đúng), nhưng `regime_summary.json` không xuất scaler-fit range tường minh |
| **R03** | Audit filtered vs smoothed/Viterbi | **IMPLEMENTED** | `regime/output.py:97-108` ghi cả `prob_*`, `prob_*_smoothed`, `viterbi_*` — đúng như plan yêu cầu |
| **R04** | Stress skip ⇒ gate phải `INCOMPLETE/BLOCKED`, không PASS | **CONTRADICTED** ⚠️ | `ai/cli.py:616-618` chỉ gate trên `target_regime`; `skipped_regimes` (`:666`) **không hạ trạng thái**. Artifact: `gate_status: "PASS"` + `skipped_regimes.stress: "pool rỗng"` |
| **R05** | Coverage PASS ≠ Candidate Gate PASS | **IMPLEMENTED** | `candidate_gate.py:162-176` tách `COVERAGE_BELOW_THRESHOLD` / `STABILITY_NOT_EVALUATED`; artifact báo FAIL đúng |
| **R06** | Chứng minh không-overlap bằng hash, không bằng seed khác | **IMPLEMENTED** | `sampling.py:389-391` assert set-intersection rỗng; `manifest.split_hashes` |
| **R07** | Reproducer + versions + trace cho bug QAOA | **PARTIAL** | `solvers/qaoa.py:35-49` mô tả rất kỹ; `_qaoa_worker.py` + retry subprocess đã implement. Nhưng không có minimal reproducer / attempt log dạng artifact |
| **R08** | Không so 8/10-bit full-settings với 20-bit dev-settings | **CONTRADICTED một phần** | `artifacts_bench/warm_start_run` (10-bit, 1024 shots, maxiter 200, 10 seed) vs `artifacts/runs/*` (20-bit, 128 shots, maxiter 10, 1 seed) — hai chế độ hoàn toàn khác nhau, và `artifacts_bench/README.md` không cảnh báo điểm này |
| **R09** | Không tăng N để tạo câu chuyện quantum | **IMPLEMENTED** | `configs/workflow_update.yaml:290` `direct_30_asset_quantum_allowed: false`; `:22` `not_allowed_for: quantum_direct_30_assets` |
| **R10** | Thay % cảm tính bằng checklist deliverable | **PLANNED** | Không có evidence ledger trong repo |
| **R11** | Ghi "chạy QAOA trên simulator", không gọi QPU | **IMPLEMENTED** | `benchmark.py:362-365` caveat; `backends/hardware.py` để trống; landing `page.tsx:135-137` nói rõ simulator |

### 2.2 Nhóm quyết định A–H

| ID | Trạng thái | Bằng chứng |
|---|---|---|
| A1 persona/không đặt lệnh | **IMPLEMENTED** | Không có order routing ở đâu; `report/page.tsx:125` disclaimer |
| A2 horizon 20 phiên cố định, S=2000/5000 | **IMPLEMENTED** | `workflow_update.yaml:133,490,498`; snapshot vào manifest |
| A3 `configs/policies/risk_appetite.yaml` | **PLANNED** | Thư mục `configs/` chỉ có `base.yaml` + `workflow_update.yaml` + `README.md`. `risk_policy_artifact: null` (`:503`) |
| A4 `configs/policies/claim_policy.yaml` | **PLANNED** | Không tồn tại |
| A5 `decision_registry.yaml` | **PLANNED** | Không tồn tại |
| CR-WF2-001 eligibility trạng thái rõ | **PARTIAL** | `eligibility.py` có 6 reason_code; chưa tách model-eligibility vs trade-eligibility |
| CR-WF2-002 bỏ target cash cứng 10%, dùng band | **CONTRADICTED** ⚠️ | `RiskPolicy` có `cash_min/cash_max` (`policy.py:44-45`) nhưng `risk_policy: null` trong run thật ⇒ `objective.py:185-186` rơi về `target_cash_increment = 0.1` **cứng**. Đây chính là nguyên nhân all-ones (§6) |
| CR-WF2-003 cash có yield | **PLANNED** | Không có `cash_yield` ở đâu; cash = 0% ngầm định |
| CR-WF2-004 universe PIT | **PARTIAL** | Snapshot `universe_30_asof_20260803.csv` có; historical PIT membership chưa |
| CR-WF2-005 dynamic N 10→12→15 | **PARTIAL** | `candidate_gate.py:177-184` có `sensitivity_coverage` cho 12/15 (đo được 0,675 / 0,783), nhưng **không có logic tự động chọn N nhỏ nhất đạt cả coverage lẫn stability** |
| C1–C5 (AI) | **PARTIAL** | Feature list đúng contract v0.2; challenger/ablation không có artifact |
| D1 posterior→cash band convex mixture | **PLANNED** | `policy.py:52-53` có field `p_stress`/`regime_posterior` nhưng không có mapping code |
| D2 cash instrument | **PLANNED** | — |
| D3 cost engine tách thành phần | **IMPLEMENTED** | `costs.py`; `objective.py:235-237` tách `transaction_cost` (fee+spread) khỏi `liquidity_penalty`; `downstream.py:615-640` validate TL-008 |
| D4 CVaR95 primary, 97.5/99 robustness | **IMPLEMENTED** | `workflow_update.yaml:173-176`; `metrics.py`; test tay có |
| D5 lexicographic / no-action mặc định | **CONTRADICTED** | `objective.py:240-251` là **weighted-sum thuần**, không lexicographic. `priority: cvar_first` (`:252`) là nhãn chết, không có code đọc |
| D6 không chọn cứng Top-15, đo lại stability | **PARTIAL** | Gate có chỗ nhận `ranking_variants`, nhưng `stability_rankings_path: null` (`:568`) ⇒ `_ranking_variants` trả `None` (`risk/cli.py:534-538`) ⇒ stability **không bao giờ được đánh giá** |
| D7 cap 30%/mã, K = số mã đổi thật | **IMPLEMENTED** | `maximum_reduction: 0.3`; `policy.py:186-187` `PER_ASSET_CAP`; `rerank.py:228-240` áp cap khi polish |
| D8 `p(q)=1+q+q(q−1)/2`, holdout bắt buộc | **PARTIAL → P0** | `surrogate.py:63-66` đúng công thức (211 tại d=20); holdout **được sinh nhưng không bao giờ được dùng** (`risk/cli.py:837-849` chỉ ghi ra parquet) |
| E1 adaptive cap / fixed grid | **IMPLEMENTED (fixed grid)** | `four_level.py:15`; challenger adaptive chưa có |
| E2 binary reference, Gray là challenger | **IMPLEMENTED** | Chỉ có binary; `four_level.py:1-7` ghi rõ bit order |
| E3 hard wall-time/memory budget | **PARTIAL** | `workflow.py:176-180, 234-284` có timeout theo seed/total. **Không có memory budget, không có kill process tree**; `peak_memory_mb` luôn `None` |
| E4 ablation classical-only vs classical+QAOA cùng budget | **PLANNED** | Không có script ablation; `artifacts_bench/warm_start_run` vs `no_warm_start_run` là ablation warm-start, không phải ablation quantum-contribution |
| E5 futures P2 | **IMPLEMENTED (không có futures)** | — |
| F1 nhận quantity+cash+NAV, server reprice, không nhận weights-only | **CONTRADICTED** ⚠️ | `application/optimize/dto.py:7-11` **chỉ nhận `weights` + `cash_weight`**, và docstring tự thừa nhận *"Weights hiện chưa re-price risk theo danh mục request"* |
| F2 tolerance NAV | **PLANNED** | Không có reconcile |
| F3 quantity nguyên, round-lot | **PLANNED** | Không có |
| G1 đăng ký ngày trước run | **PLANNED** | — |
| G2 16 ca synthetic UAT | **PLANNED** | — |
| G3 chưa ký final PASS | **IMPLEMENTED** | Không có approval nào trong config |
| H1 profile experimental riêng, artifact theo run_id | **PARTIAL** | `artifacts/runs/job_*` tách đúng theo run; **nhưng `artifacts/dev/` vẫn bị ghi đè nhiều lần chạy** — git status cho thấy 20+ artifact bị modify/delete |
| H2 policy có status/owner/version/approved_by | **PARTIAL** | `profile.status/owner` có (`:5-8`), `approved_by`/`approved_at`/`effective_scope` **không có** |

---

## 3. Review phần Quantum (chi tiết)

### 3.1 Mã hoá 2 bit / asset

`packages/quantum/src/qshield_quantum/formulation/four_level.py:19-60`

```python
bits[:, 0] = (rounded % 20 == 10)   # bit A: 10%
bits[:, 1] = (rounded >= 20)        # bit B: 20%
...
return 10 * pairs[:, 0] + 20 * pairs[:, 1]
```

Mapping: **00→0%, 10→10%, 01→20%, 11→30%**. Đây **không phải** little-endian nhị phân thông thường — docstring `four_level.py:1-7` nói rõ điều này, và `workflow.py:75-77` validate mapping phải khớp đúng config. Cách encode này là **unary-ish additive**: level = 10·b₀ + 20·b₁. Ưu điểm: tuyến tính theo bit ⇒ dễ đưa vào QUBO. Nhược điểm: 4 mức được biểu diễn bởi tổ hợp cộng, nên hai bit **không độc lập về ý nghĩa kinh tế** (b₁ "đắt" gấp đôi b₀), làm coefficient scale lệch nhau 2×.

Cùng codec được cài lại độc lập ở phía Risk: `packages/risk/src/qshield_risk/sampling.py:31-40` (`0.10*b₀ + 0.20*b₁`). **Hai bản cài đặt song song, không share code** — hiện khớp nhau nhưng là điểm dễ vỡ khi đổi grid (P1).

### 3.2 Vì sao 10 candidates = 20 bit = 4¹⁰ portfolio

- 10 candidate × 2 bit = **20 biến nhị phân** (`workflow.py:69-74` assert `total_decision_bits == 2 * input_candidates`).
- Không gian bitstring = 2²⁰ = **1.048.576** (`workflow_update.yaml:306` `exact_reference_states: 1048576`; artifact xác nhận `exact_evaluated_states: 1048576`).
- Vì mỗi cặp bit là song ánh với 4 mức, 2²⁰ = 4¹⁰ — **không có bitstring vô nghĩa, không cần ancilla, không cần penalty cardinality**. Đây là điểm thiết kế tốt: encoding *surjective và injective*, khác hẳn đường legacy K-of-N.

### 3.3 Objective → quadratic surrogate

`surrogate.py:63-83, 154-195`

- Design: `[1, z_i, z_i·z_j (i<j)]` ⇒ `p(d) = 1 + d + d(d−1)/2 = 211` tại d=20. Đúng công thức plan D8.
- Fit bằng `np.linalg.lstsq`, **fail-fast nếu rank < 211** (`:172-176`) — rất tốt, chặn được surrogate under-determined.
- Off-diagonal chia đôi để về dạng đối xứng `z'Qz` (`:184`).
- **Vấn đề:** đây là fit *nội suy đúng* trên 211 mẫu structured (211 mẫu / 211 hệ số ⇒ residual gần 0 theo cấu trúc). 500 mẫu random thêm vào làm bài toán over-determined, nhưng **không có ai đo residual đó có nghĩa gì**. `residual_sum_squares` được ghi vào `qubo_model.json` nhưng không có ngưỡng, không có so sánh với holdout.

**Tính đúng đắn toán học của giả thiết bậc 2:** true objective chứa CVaR — một hàm **không phải bậc 2** của reductions (là expected shortfall của một hàm phi tuyến của weights). Surrogate bậc 2 chỉ là xấp xỉ. Đây là lý do plan bắt buộc holdout validation — và đó là thứ đang thiếu.

### 3.4 Surrogate → QUBO → QuadraticProgram

`formulation/qiskit_program.py:23-44`

```python
linear_with_diag[i] += Q[i, i]          # z_i² = z_i
coeff = Q[i, j] + Q[j, i]               # qiskit đếm 1 lần, z'Qz đếm 2 lần
```

Xử lý quy ước hệ số đúng và có comment cảnh báo (`:5-9`). `to_qubo` (`:47-53`) chạy qua `QuadraticProgramToQubo` thật (không đi tắt) nên verify kiểm được đường convert thực của qiskit.

**Verify gate** — `verify/consistency.py:46-115`: so 3 cách tính (NumPy / QuadraticProgram / QUBO sau convert). Thiết kế chuẩn.
⚠️ **Nhưng ở run 20-bit, verify chạy ở chế độ sampled**: `quantum/cli.py:410` truyền `verify_sample_size=4096 if non_final and runtime_bits >= 16`. Artifact xác nhận: `verify_checked_states: 4098` / `total_states: 1048576` — tức **0,39%** không gian. Với `NON_FINAL_CONFIG` thì hợp lệ theo chính docstring, nhưng **không được coi là verify đầy đủ cho baseline**.

### 3.5 Penalty và feasibility constraints

Đây là điểm cần phân biệt rõ **hai đường code**:

**(a) Đường legacy 8-bit** (`formulation/objective.py`, `qubo.py`, `penalty.py`):
`f(z) = −g'z + λ₁z'Cz + λ₂c'z + P(Σz − K)²`, có penalty cardinality thật, `suggest_penalty` (`penalty.py:29-48`) tính chặn trên đúng. Đường này **không nằm trên workflow sản phẩm** — `run_four_level_workflow` không gọi tới nó.

**(b) Đường sản phẩm 20-bit four-level:**
- **Không có penalty nào trong QUBO.** QUBO = đúng surrogate `z'Qz + linear'z + const`, không cộng thêm term ràng buộc.
- Feasibility là **một predicate Python bên ngoài QUBO**: `workflow.py:107-137` `make_four_level_feasibility(constraints)`.
- Nguồn constraints: `risk_summary["quantum_constraints"]` (`workflow.py:206`).
- **Giá trị thực tế: `{}`** — `configs/workflow_update.yaml:597` `quantum_constraints: {}`, và `artifacts/dev/risk/risk_summary.json:188` cũng `{}`.

⇒ **Predicate luôn trả `True`.** Không có ràng buộc nào tồn tại trong bài toán quantum hiện tại: không cash band, không turnover cap, không do-not-sell, không CVaR budget. Toàn bộ hard constraints trong `policy.py:146-205` **chỉ được kiểm ở tầng Risk sau khi đã giải xong** — chúng không nằm trong QUBO và không nằm trong feasibility predicate của solver.

Hệ quả trực tiếp:
- `feasible_states == evaluated_states == 1048576`
- `mean_feasibility_rate` mất ý nghĩa (luôn 1.0 hoặc `null`)
- QAOA không bao giờ có thể "vi phạm ràng buộc" ⇒ metric `feasible_rate` trên UI là số trang trí

**Đây là P0.** Không có feasibility constraint thì bài toán không phải constrained combinatorial optimization — nó là unconstrained quadratic minimization trên hypercube.

### 3.6 Exact solver làm ground truth

`solvers/exact.py:100-159` — duyệt đủ 2^20 theo chunk 65.536, giữ heap top-20, không allocate toàn bộ. Cài đặt tốt, memory-bounded, deterministic. Runtime đo thật: **37,9s** (`workflow_benchmark.json: runtime_seconds.exact`).

Vai trò ground truth **đúng chuẩn** — nhưng lưu ý: exact solver đang là ground truth **của surrogate**, không phải của true financial objective. Ground truth tài chính là `rerank.py` + `true_benchmark.py`. Đây là hai khái niệm khác nhau và code phân biệt đúng (`true_benchmark.json` có `financial_ranking` riêng vs `qubo_rank`).

### 3.7 Classical benchmark có công bằng không?

`benchmark.py:122-172` — multi-start coordinate descent (1-bit flip), 64 restarts, seed cố định, khởi tạo gồm all-zeros + all-ones + 62 random.

**Không công bằng theo cả hai chiều:**

| | QAOA | Classical |
|---|---|---|
| Budget khai báo | 600s/seed × 10 seed = 6000s | không giới hạn |
| Runtime thực đo (10-bit) | **40,4s** (warm) / **337,2s** (no-warm) | **0,14s** |
| Runtime thực đo (20-bit) | 0s (skip) | **0,56s** |
| Số lần đánh giá objective | ~1024 shots × ~200 iter | 64 restarts × ~20 flip × 20 bit |

Classical đang chạy nhanh hơn QAOA **~600–2400×** mà cho nghiệm bằng hoặc tốt hơn. Đây không phải "matched budget". Muốn so công bằng phải cấp cho classical đúng ngân sách wall-time của QAOA (ví dụ 40s tabu/simulated annealing với hàng triệu đánh giá) — lúc đó classical sẽ càng thắng đậm, nhưng con số mới trung thực.

Thêm nữa: **`all-ones` nằm ngay trong danh sách khởi tạo của classical** (`benchmark.py:136`). Với landscape hiện tại (nghiệm tối ưu = all-ones), classical "thắng" ngay ở restart thứ 2 mà không cần search. Benchmark hiện tại không đo được năng lực tìm kiếm của bất kỳ solver nào.

### 3.8 QAOA: simulator hay hardware?

**Simulator, 100%.** `backends/simulator.py:11-12` → `StatevectorSampler`. `backends/hardware.py` chỉ có 1 dòng comment, cố ý để trống. Không có `qiskit-ibm-runtime` trong dependency. Caveat được ghi vào artifact (`benchmark.py:362-365`) và hiển thị trên UI.

**Đánh giá:** đây là điểm trung thực **tốt**, và đúng yêu cầu R11 của plan.

### 3.9 Warm-start có thực sự được dùng không?

Có — nhưng cần hiểu chính xác nó là gì.

`solvers/warm_start.py:20-25`:
```python
WarmStartQAOAOptimizer(
    pre_solver=SlsqpOptimizer(),      # ← solver cổ điển liên tục
    relax_for_pre_solver=True,        # ← giải relaxation liên tục trước
    qaoa=qaoa, epsilon=0.25, num_initial_solutions=1)
```

Tức là: **một solver cổ điển (SLSQP) giải continuous relaxation trước, rồi kết quả đó khởi tạo initial state của QAOA.**

Bằng chứng ảnh hưởng — so hai run 10-bit cùng QUBO hash (`2e50ce07…`):

| | warm_start_run | no_warm_start_run |
|---|---|---|
| bitstring | `1111111111` (= exact) | `1101111111` |
| optimality_gap | **0.0** | 0.0203 |
| success_prob | 0,0076 | **0,0** |
| runtime/seed | 4,0s | **337,2s** |
| actual_solver | qaoa | **exact** (timeout 300s) |

Warm-start làm QAOA **ra đúng nghiệm exact**, nhưng `success_prob = 0,0076` nghĩa là xác suất đo được nghiệm đó từ phân phối lượng tử chỉ **0,76%**. Nghiệm đúng đến từ đâu? Từ việc `MinimumEigenOptimizer` chọn sample có `fval` thấp nhất trong 1024 shot — và initial state đã được SLSQP đẩy về gần góc đó.

⚠️ **Đây chính là rủi ro plan E4 cảnh báo**: *"Không inject exact answer vào QAOA rồi gọi tự tìm."* Code **không** inject nghiệm exact (`reference_bitstring` ở `qaoa.py:156-163` chỉ dùng để **đo** `success_prob`, không nạp vào mạch — điểm này code làm đúng). Nhưng warm-start bằng SLSQP là một dạng classical priming, và kết quả `warm_start_run` **không được phép mô tả là "QAOA tự tìm ra nghiệm tối ưu"**.

### 3.10 Multi-seed / shots / p / optimizer / timeout

| Tham số | Config baseline (`workflow_update.yaml:310-328`) | `dev_mode` thực chạy (`:330-336`) | Artifact 20-bit thực tế |
|---|---|---|---|
| seeds | 10 seed (101…1001) | **[101]** | `registered_seeds: [101]` |
| shots | 1024 | **128** | `shots: 128` |
| maxiter | 200 | **10** | `maxiter: 10` |
| p (reps) | 1 | 1 | `reps: 1` |
| warm_start | true | **disabled** | `warm_start: false` |
| seed_status | — | — | `{"101": "timeout"}` |

`dev_mode.enabled: true` **là mặc định trong profile sản phẩm**. Nghĩa là bất kỳ ai chạy `qshield-quantum workflow` với config mặc định sẽ chạy 1 seed / 128 shots / 10 iteration — cấu hình này **không thể coi là một lần chạy QAOA có ý nghĩa thống kê**.

Timeout: `workflow.py:234-284` xử lý đúng (kiểm tra trước và sau mỗi seed, ghi `fallback_reason` cụ thể có số liệu). Nhưng:
- ⚠️ Timeout được kiểm **sau khi seed đã chạy xong** (`:262-274`) — không có cơ chế hủy giữa chừng. Một seed 337s vẫn chạy hết dù budget 300s (chính xác điều đã xảy ra trong `no_warm_start_run`).
- ⚠️ Không có memory budget; `peak_memory_mb` luôn `None` trong mọi artifact.
- ⚠️ Không kill process tree (plan E3 yêu cầu).

**Vấn đề runtime cốt lõi:** `qaoa.py:49-59` — `_TRANSPILE_SAFE_MAX_QUBITS = 8`. Với 20 qubit, `_make_transpiler` trả `None` ⇒ QAOA đi đường `PauliEvolutionGate.to_matrix()` với `scipy.sparse.linalg.expm` trên ma trận 2²⁰×2²⁰. Đó là lý do 20-bit QAOA **không bao giờ hoàn thành**. Đã có giải pháp (`solve_qaoa_one_seed_fast` + `_qaoa_worker.py` subprocess+retry, commit `380974a`) — **nhưng `run_four_level_workflow` gọi `solve_qaoa_one_seed` thường ở `workflow.py:243`, không gọi bản `_fast`.** Lý do đã ghi trong docstring `qaoa.py:219-222`: `_fast` không pickle được closure `make_four_level_feasibility()`. Vì `quantum_constraints` đang rỗng, có thể dùng `_always_feasible` (đã là hàm cấp module, pickle được) — **cơ hội sửa rẻ, tác động lớn** (xem P1-1).

### 3.11 QAOA output được chấm bằng gì?

**Hai lớp, cả hai đều tồn tại trong code:**

1. **Surrogate energy** — `benchmark.py:304` chọn winning seed theo `result.energy` (= QUBO energy).
2. **True financial objective** — `true_benchmark.py:209-240` chấm lại từng solver bằng `financial_objective` thật, có `financial_ranking` và `ranking_disagreement`.

Bằng chứng lớp 2 hoạt động: `artifacts_bench/no_warm_start_run/true_benchmark.json`:
```
"notes": ["QAOA loses to exact on true CVaR (no quantum advantage claim).",
          "QAOA loses to classical on true CVaR."]
```

**Đây là điểm mạnh thật sự** và tuân thủ đúng CLAUDE.md quy tắc 17.

Nhưng lưu ý: `workflow_benchmark.json` (artifact được backend/UI đọc) **chỉ có surrogate energy**. `qaoa_beats_classical` (`benchmark.py:348`) so **QUBO energy**, không so true CVaR. UI hiển thị chính field này (`frontend/app/(console)/quantum/page.tsx:142-143`). Đó là một so sánh trên đại lượng sai (P1).

### 3.12 Rerank/polish làm thay đổi ý nghĩa của kết quả quantum thế nào?

`rerank.py:181-304` polish ±5pp với zero-lock. Ý nghĩa: solver quantum quyết định **tập mã nào được chạm vào** (zero vs non-zero), còn **mức chính xác thì do coordinate descent cổ điển quyết định** trong biên ±5pp.

`PolishingResult.polishing_dependency` (`rerank.py:280-284`) đo đúng chỉ số này:
```
dependency = (objective_quantum − objective_polished) / (objective_zero − objective_polished)
```
Đây là **một thiết kế đo lường xuất sắc** — nó định lượng được "bao nhiêu phần cải thiện đến từ polish cổ điển thay vì từ solver". Rất tiếc chỉ số này **không được hiển thị ở đâu trên UI** và không có ngưỡng gate.

Rủi ro diễn giải: nếu `polishing_dependency` cao, nói "quantum tìm ra phương án" là sai — quantum chỉ chọn support set, phần còn lại là classical.

### 3.13 Tái lập kết quả: `qubo_hash`, candidate order, seed

`quantum/cli.py:430-441`:
```python
model_hash_payload = json.dumps({k: v for k, v in model_payload.items() if k != "run_id"}, sort_keys=True, ...)
model_payload["qubo_hash"] = hashlib.sha256(...).hexdigest()
```
Loại `run_id` khỏi hash để hash định danh **model**, không định danh run. Comment giải thích lý do rất rõ. Hai run độc lập (`job_086a4f16…` và `job_eae747c8…`) cho **cùng `qubo_hash: c34782af…`** ⇒ **reproducibility đã được chứng minh bằng thực nghiệm**. Đây là điểm rất tốt.

`candidate_order_hash` được truyền xuyên suốt từ Risk (`risk/cli.py:794-797`) đến Quantum đến true_benchmark. `benchmark.py:228-231` từ chối nếu `qubo_hash` lệch giữa các solver.

**Còn thiếu để tái lập hoàn toàn:**
- Không có hash của scenario cube (`stress_scenarios.npz`) trong `qubo_hash` chain — chỉ có `parent_hashes.scenario_manifest`.
- `reference_hardware.cpu/ram_gb/os` = `null` trong mọi artifact ⇒ runtime không so sánh được giữa máy.
- `peak_memory_mb` = `null`.
- `artifacts/dev/` bị ghi đè giữa các lần chạy (git status: 20+ file modified/deleted).

### 3.14 Phân loại claim

| Loại | Nội dung | Đánh giá |
|---|---|---|
| **Quantum formulation thật có trong code** | Encoding 2-bit/asset → 4 mức; surrogate bậc 2 211 hệ số; `QuadraticProgram` + `QuadraticProgramToQubo`; QAOA p=1 COBYLA trên `StatevectorSampler`; verify 3-đường | ✅ Có thật, cài đặt đúng kỹ thuật |
| **Simulator behavior** | Toàn bộ QAOA. `StatevectorSampler` = mô phỏng statevector chính xác, không noise model, không QPU | ⚠️ Phải nói rõ mọi nơi |
| **Classical fallback** | `actual_solver = "exact"` trong 100% artifact 20-bit; `--exact-only` mặc định ở backend và pipeline | ⚠️ Đường sản phẩm hiện tại **không có quantum** |
| **Classical priming được gọi là quantum** | `warm_start_run`: SLSQP giải relaxation → QAOA khởi tạo từ đó → ra nghiệm exact với success_prob 0,76% | ⚠️ Không được mô tả là "QAOA tìm ra" |
| **Claim HỢP LỆ** | "Bài toán hedge four-level đã được formulate thành QUBO 20 biến và verify khớp trên 3 đường tính"; "Exact 2²⁰ đã chạy đủ, làm ground truth"; "QAOA đã chạy được ở quy mô 10-bit trên simulator và cho nghiệm trong khoảng 0–2% gap so với exact"; "Kết quả solver được chấm lại bằng true CVaR" | ✅ |
| **Claim CHƯA ĐƯỢC PHÉP** | "QAOA giải bài toán 20-bit"; "quantum advantage"; "chạy trên máy tính lượng tử"; "quantum tìm ra chiến lược phòng vệ"; "quantum nhanh hơn classical"; "giảm X% CVaR nhờ quantum" | ❌ Chưa có bằng chứng nào hỗ trợ |

---

## 4. Điểm mạnh

### 4.1 Ý tưởng sản phẩm
Hedging tail-risk bằng cash cho nhà đầu tư cá nhân đang giữ cổ phiếu là **một bài toán thật, có nhu cầu thật, và đủ nhỏ để làm đúng**. Việc giới hạn action space ở 4 mức bán (0/10/20/30%) thay vì tối ưu weights liên tục là một quyết định thiết kế **rất khôn ngoan**: nó làm bài toán trở thành tổ hợp (hợp với QUBO), đồng thời khớp với cách nhà đầu tư thật ra quyết định ("bán một phần ba", không phải "giảm weight xuống 0,0847").

### 4.2 Risk-aware decision support đúng chuẩn
- CVaR đúng định nghĩa Rockafellar–Uryasev (trung bình đuôi, không phải quantile) — có test tay `test_cvar_by_hand.py`.
- Quy ước dấu nhất quán `loss_sign_convention: "positive_is_loss"` ghi thẳng vào artifact.
- Robustness ở 3 mức α (0.95/0.975/0.99) chứ không chỉ một.
- `tail_uncertainty` bootstrap CI cho CVaR (`workflow_update.yaml:491-497`) — hiếm gặp ở prototype.
- **Materiality gate** (`rerank.py:19-43`): chỉ cho phép claim cải thiện khi CVaR giảm ≥1% tương đối sau chi phí. Đây là bảo vệ chống over-claim rất đúng đắn.

### 4.3 Governance / không tự đặt lệnh
Không có dòng code nào chạm order routing. `NON_BASELINE_RUN` được enforce ở tầng code chứ không chỉ ở tài liệu (`run.py:224-228` raise nếu status khác). `not_allowed_for` liệt kê tường minh 6 use case bị cấm (`workflow_update.yaml:16-22`). Disclaimer xuất hiện ở landing, console, report.

### 4.4 Tách AI / Risk / Quantum thành stage độc lập
`pipeline/run.py:50-66` chạy **mỗi stage trong subprocess riêng**. Lý do được ghi rõ: mỗi tiến trình con chỉ import đúng một package nặng. Đây vừa là kỹ thuật (tránh qiskit + pyarrow + hmmlearn cùng process), vừa là kiến trúc (buộc giao tiếp qua artifact, không qua object in-memory ⇒ mọi ranh giới đều audit được).

### 4.5 Khả năng audit / replay
- `RunContext` là nơi duy nhất ghi metadata (đúng CLAUDE.md quy tắc 13).
- Provenance 5 trường (`run_id`, `profile_id`, `profile_status`, `config_version`, `config_hash`) đi kèm **mọi** artifact.
- `parent_hashes` liên kết ngược lên upstream.
- `qubo_hash` ổn định giữa các run — **đã chứng minh bằng 2 job khác nhau ra cùng hash**.
- `split_hashes` cho train/validation/holdout.
- `artifacts/runs/job_<id>/` cô lập từng job.

### 4.6 Candidate reduction
30 → 10 với score có cả benefit và cost (`workflow_update.yaml:200-210`), có coverage metric, có sensitivity ở N=12/15. Quan trọng nhất: **risk vẫn tính trên toàn bộ 30 mã**, candidate chỉ giới hạn nơi được thay đổi hành động (`risk_summary.ticker_order` có đủ 30). Đúng plan §4.2.

### 4.7 True objective rerank
`rerank.py:151-164` sort theo `[feasible, true_objective, true_cvar, transaction_cost, bitstring]` — tie-break deterministic đầy đủ. `ranking_disagreement = surrogate_rank − true_rank` **đo trực tiếp mức độ surrogate đánh lừa**. Rất tốt.

### 4.8 Exact ground truth
Duyệt đủ 2²⁰ không bỏ sót, memory-bounded bằng chunk + heap. Không có shortcut "chỉ duyệt vùng khả dĩ".

### 4.9 Fallback khi QAOA lỗi
`requested_solver` vs `actual_solver` + `fallback_reason` bắt buộc phi rỗng khi hai giá trị lệch (`downstream.py:598-603` raise). `seed_status` per-seed (`completed`/`failed`/`timeout`). `benchmark.py:250-300` payload fallback set `qaoa_optimality_gap = None` chứ không giả 0. **Đây là mức trung thực kỹ thuật cao.**

### 4.10 Frontend transparency
`ReadOnlyNote` trên trang quantum: *"Exact solver là thước đo chuẩn, QAOA là bên thách thức — kết quả ở đây không chứng minh quantum advantage"* (`quantum/page.tsx:45-48`). Landing có mục "Không tuyên bố quantum advantage" (`landing/page.tsx:105-108`) và "không hardware lượng tử thật" (`:135-137`). Hiển thị `actual_solver` ngay trên card chính.

### 4.11 Testability
416 test, chạy được: contracts 55✅, data 62✅, risk 70✅, quantum 40✅, pipeline 13✅, backend 4✅, ai 169✅/3❌. Test suite risk có `test_cvar_by_hand.py`, `test_weight_sum.py`, `test_cvar_before_after.py` — đúng tinh thần "mỗi công thức tài chính cần một test so với ví dụ tính tay".

### 4.12 Tự phê bình kỹ thuật
`tools/qaoa_stress_bakeoff.py:6-8` tự nhận bài toán thật là gần tuyến tính và dựng instance khó hơn để so solver, kèm disclaimer "NOT the production cash-hedge QUBO". Comment trong `qaoa.py:40-48` mô tả bug qiskit flaky rất chi tiết và không giấu phần chưa giải quyết. **Văn hoá kỹ thuật này đáng giá hơn nhiều tính năng.**

---

## 5. Điểm yếu và rủi ro

### P0 — Phải xử lý trước khi gọi là baseline

---

#### **P0-1 · Objective degenerate: bài toán không có cấu trúc tổ hợp**

**Vấn đề.** Hàm mục tiêu gần như tuyến tính đơn điệu theo tổng lượng bán. Đo trên 711 mẫu train thật:

```
corr(objective, reduction_sum) = -0.9993

Biên độ từng thành phần (contribution, trên toàn tập mẫu):
  cash_budget_deviation   span = 0.30257   ← chi phối
  cvar                    span = 0.11157
  turnover                span = 0.02167
  transaction_cost        span = 0.00542
  return_sacrifice        span = 0.00297
  liquidity_penalty       span = 0.00108
```

**Nguồn.**
- `configs/workflow_update.yaml:506` `target_cash_increment: 0.1`
- `configs/workflow_update.yaml:542-544` `cash_budget_deviation: weight 0.35 / scale 0.1` ⇒ hệ số hiệu dụng **3.5**
- `packages/risk/src/qshield_risk/objective.py:210-214` tính `cash_deviation = |cash_increment − 0.1|`
- `artifacts/dev/risk/candidate_top10.csv` — 10 candidate, mỗi mã `current_weight = 0.0333333`
- Số học: `10 × 0.0333333 × 0.30 = 0.10` ← **đúng bằng target**

⇒ Chỉ tồn tại **một** bitstring đưa `cash_budget_deviation` về ~0: `11111111111111111111`.

**Tác động.**
- Correctness: nghiệm "tối ưu" không phản ánh đánh đổi rủi ro–chi phí, nó phản ánh việc chạm target cash.
- Risk: hệ thống luôn khuyên bán 30% mọi mã, bất kể regime — đây là hành vi nguy hiểm cho một sản phẩm risk advisory.
- Quantum credibility: **triệt tiêu hoàn toàn** lý do dùng QUBO/QAOA. Một dòng `z = ones(20)` giải xong bài toán.
- Product trust: nếu demo cho reviewer tài chính, họ sẽ hỏi "tại sao lúc nào cũng bán hết mức?" và không có câu trả lời.

**Cách sửa.**
1. Thay `target_cash_increment` cứng bằng **cash band** (`cash_min`/`cash_max`) như CR-WF2-002 — code `RiskPolicy` đã sẵn sàng (`policy.py:44-45, 137-143`), chỉ cần cung cấp `risk_policy_artifact` thay vì `null` (`workflow_update.yaml:503`).
2. Hạ trọng số `cash_budget_deviation` xuống mức so được với CVaR (đề xuất khởi điểm: weight ≤ 0.05, hoặc chuyển thành hard constraint thay vì soft term).
3. Đặt target cash **thấp hơn** tổng khả năng bán (ví dụ target 5% khi max là 10%) để tồn tại nhiều nghiệm đạt band ⇒ tie-break rơi về CVaR/cost, tạo ra bài toán tổ hợp thật.
4. Bỏ portfolio equal-weight 1/30 trong evidence run; dùng danh mục có phân bố weight không đều để marginal benefit khác nhau giữa các mã.

**Acceptance criteria.**
- `|corr(objective, reduction_sum)| < 0.85` trên tập train.
- Nghiệm exact **không phải** all-ones và **không phải** all-zeros trên ít nhất 3/5 danh mục test.
- `cash_budget_deviation` span < span của `cvar` trên cùng tập mẫu.
- Số local minima của landscape (đo bằng 1-flip) > 20.

---

#### **P0-2 · Không có surrogate validation gate trên holdout**

**Vấn đề.** Config khai báo gate bắt buộc; code không có gì.

**Nguồn.**
- `configs/workflow_update.yaml:655` `gates.surrogate_validation_required_before_solver: true`
- `configs/workflow_update.yaml:618-629` đủ 7 ngưỡng: `mae_max 0.02`, `rmse_max 0.03`, `spearman_min 0.7`, `top_k_recall_min 0.6`, `feasible_rate_min 0.05`, `seed_stability_min 0.5`
- `grep -rn "surrogate_validation" packages backend` → **0 kết quả trong code**
- `packages/risk/src/qshield_risk/cli.py:837-849`: holdout được sinh, ghi vào `true_objective_samples.parquet`, **rồi thôi**
- Chỉ `train` được ghi vào `qubo_objective_samples.parquet` (`:846`) — file duy nhất Quantum đọc (`quantum/cli.py:313, 323`)

**Tác động.** Surrogate bậc 2 đang xấp xỉ một hàm CVaR phi tuyến. Không ai biết sai số. Toàn bộ chuỗi exact→QAOA→rerank đang giải một mô hình chưa được kiểm định. Nếu surrogate sai, exact solver duyệt đủ 2²⁰ cũng chỉ cho ra "nghiệm tối ưu của một mô hình sai".

**Cách sửa.** Thêm stage `surrogate-validate` giữa `risk_workflow` và `quantum_workflow`:
```
1. Fit surrogate trên train (211 structured + 500 random)
2. Predict trên validation (500) và holdout (1000)
3. Tính MAE, RMSE, Spearman ρ, top-20 recall
4. Ghi surrogate_validation.json
5. Nếu holdout không đạt ngưỡng → hard stop khi profile là baseline;
   ANALYSIS_ONLY + warning khi NON_BASELINE
```
Chọn encoding/hyperparameter bằng **validation**, holdout chỉ để xác nhận một lần (plan D8/E2).

**Acceptance criteria.**
- `artifacts/dev/optimization/surrogate_validation.json` tồn tại với đủ 4 metric trên cả validation lẫn holdout.
- Pipeline **fail** khi holdout Spearman < 0.7.
- Có test chứng minh gate fail đúng khi inject surrogate xấu.

---

#### **P0-3 · Hard constraints không được encode vào QUBO — và thực tế đang rỗng hoàn toàn**

**Vấn đề.** Feasibility predicate luôn `True`.

**Nguồn.**
- `packages/quantum/src/qshield_quantum/workflow.py:206` đọc `risk_summary["quantum_constraints"]`
- `configs/workflow_update.yaml:597` `quantum_constraints: {}`
- `artifacts/dev/risk/risk_summary.json:188` `"quantum_constraints": {}`
- `workflow.py:123-135` — với `{}`: `min_active=0`, `max_active=None`, `min_total=0`, `max_total=None` ⇒ luôn `True`
- `packages/risk/src/qshield_risk/policy.py:146-205` có đủ 8 loại constraint (`CASH_BELOW_MIN`, `TURNOVER_LIMIT`, `DO_NOT_SELL`, `PER_ASSET_CAP`, `PER_ASSET_LIQUIDITY_CAP`, `MINIMUM_TRADE_VALUE`, `CVAR_BUDGET`, `WEIGHT_SUM`) — **nhưng chỉ được kiểm sau khi đã giải xong**, ở tầng Risk

**Tác động.**
- Solver có thể trả nghiệm vi phạm policy, chỉ bị phát hiện ở bước rerank.
- Mọi metric feasibility trên artifact và UI vô nghĩa (`mean_feasibility_rate`, `feasible_rate`, `n_seeds_feasible`, `constraints_passed`).
- Về mặt bài toán: đây **không phải** constrained optimization. Không thể nói "QAOA xử lý ràng buộc" hay "penalty đảm bảo feasibility".

**Cách sửa.**
1. Risk phải xuất `quantum_constraints` thật từ `RiskPolicy` (cash band → `min/max_total_action_pct`; do-not-sell → khoá bit; per-asset cap → giới hạn level).
2. Với ràng buộc tuyến tính trên bit (cash band, turnover cap), encode thành **penalty term trong QUBO** — dùng lại pattern `penalty.py:15-26`, và `suggest_penalty` (`:29-48`) để chọn P đủ lớn.
3. Với ràng buộc không tuyến tính (CVaR budget), giữ ở predicate + rerank, và **ghi rõ trong artifact** ràng buộc nào ở trong QUBO, ràng buộc nào ở ngoài.
4. Nếu `quantum_constraints` rỗng, artifact phải ghi `feasible_rate: null` kèm `"constraints": "NONE_ENCODED"` thay vì báo số.

**Acceptance criteria.**
- `risk_summary.quantum_constraints` phi rỗng trong evidence run.
- `exact.feasible_states < exact.evaluated_states` (chứng minh predicate thật sự lọc).
- Tồn tại ít nhất một seed QAOA có `feasible: false` trong benchmark (chứng minh metric có tín hiệu).
- Có test: bitstring vi phạm cash band bị predicate loại.

---

#### **P0-4 · Nhiều gate ghi PASS trong khi bằng chứng bên dưới là FAIL/thiếu**

**4a. Scenario gate PASS dù regime Stress rỗng.**
- `packages/ai/src/qshield_ai/cli.py:616-618`:
  ```python
  distribution_gate = gate_status(report.loc[report["target_regime"] == target_regime])
  status = SCENARIO_GATE_FAIL if structural else distribution_gate
  ```
  Chỉ gate trên `target_regime` (= `volatile`). `skipped_regimes` được ghi vào manifest (`:666`) nhưng **không tác động tới `status`**.
- Artifact: `gate_status: "PASS"` + `skipped_regimes.stress: "pool rỗng, lý do loại: {'incomplete_panel': 259}"`.
- Đây **chính xác** là điều plan R04 cấm: *"Gate cho full stress capability phải INCOMPLETE/BLOCKED"*.
- Hệ quả dây chuyền: `risk/cli.py:167-169` và `quantum/cli.py:233-235` đều chỉ kiểm `gate_status == "PASS"` ⇒ toàn bộ downstream chạy tiếp như thể scenario đầy đủ.

**4b. Quantum stage luôn ghi `gate_status: "PASS"` bất kể chuyện gì xảy ra.**
- `packages/quantum/src/qshield_quantum/cli.py:514` (và `:777`): hằng số `"PASS"` hard-code trong `write_metrics`.
- Chạy với `--exact-only`, QAOA skip hoàn toàn, `qaoa_seed_count: 0` → vẫn `gate_status: PASS`.

**4c. Rerank stage ghi PASS chỉ dựa trên constraint violations.**
- `risk/cli.py:1272-1276`: `"PASS" if not polished.polished_objective.constraint_violations else "FAIL"`. Vì `risk_policy = null` ⇒ `constraint_details = ()` (`objective.py:226-228`) ⇒ **luôn PASS**.

**4d. Chất lượng scenario cực thấp nhưng không có gate.**
- `reuse_rate: 0.99645`, `unique_blocks_used: 71` — 5000 kịch bản × 4 block/path = 20.000 lần rút, từ **71 block độc nhất**. Thông tin độc lập thực tế ≈ 71 cửa sổ 5 ngày, không phải 5000 kịch bản.
- `rejected_blocks.incomplete_panel: 575` (volatile) / `259` (stress) — panel không đầy đủ là nguyên nhân chính làm stress pool rỗng.
- Không có ngưỡng nào cho `reuse_rate` hay `unique_blocks_used`.

**Tác động chung.** Đây là rủi ro **product trust** nghiêm trọng nhất. Một reviewer chỉ nhìn `gate_status` sẽ kết luận hệ thống đã qua kiểm định, trong khi thực tế: không có kịch bản stress, không có ràng buộc, không có QAOA.

**Cách sửa.**
1. `ai/cli.py`: nếu `skipped_regimes` phi rỗng → `status = "INCOMPLETE"` (trạng thái mới, không phải PASS/WARN/FAIL), và downstream phải từ chối `INCOMPLETE` cho baseline.
2. `quantum/cli.py:514,777`: `gate_status` phải suy từ thực tế — `"PASS"` chỉ khi `actual_solver == requested_solver` và verify full và seed đủ.
3. `risk/cli.py:1272`: PASS chỉ khi có policy thật để kiểm; `risk_policy is None` → `"NOT_EVALUATED"`.
4. Thêm gate `unique_blocks_used >= N_min` và `reuse_rate <= threshold` cho scenario.

**Acceptance criteria.**
- Chạy lại pipeline với stress pool rỗng ⇒ `scenario_manifest.gate_status == "INCOMPLETE"` và stage risk từ chối chạy ở chế độ baseline.
- Chạy `--exact-only` ⇒ `metrics.json.gate_status != "PASS"`.
- Không tồn tại `gate_status: "PASS"` nào trong repo mà bên dưới có `skipped_*` phi rỗng hoặc `qaoa_seed_count == 0` với `requested_solver == "qaoa"`.

---

#### **P0-5 · Backend nhận portfolio weights nhưng không dùng**

**Vấn đề.**
- `backend/src/qshield_api/application/optimize/dto.py:7-11`:
  ```python
  class OptimizeJobRequestDTO(BaseModel):
      """Weights hiện chưa re-price risk theo danh mục request — job dùng handoff packages trên đĩa."""
      weights: dict[str, float]
      cash_weight: float = 0.0
  ```
- `infrastructure/runner/subprocess_optimize_runner.py:115-130` `_snapshot_inputs` **copy nguyên handoff Risk từ đĩa**, không dùng `weights` từ request.
- Kết quả trả về là kết quả của danh mục 1/30 equal-weight đã tính sẵn.

**Tác động.**
- **Product trust nghiêm trọng**: người dùng nhập danh mục của mình, nhận về khuyến nghị của một danh mục khác. Không có cảnh báo nào ở API response hay UI.
- Vi phạm plan F1 (server phải reprice, không nhận weights-only).

**Cách sửa (theo thứ tự ưu tiên).**
1. **Ngay lập tức:** hoặc bỏ field `weights` khỏi DTO, hoặc trả `HTTP 501` khi `weights` khác weights của handoff, hoặc thêm field bắt buộc `personalization: "NOT_APPLIED"` vào response và hiển thị banner trên UI.
2. **Đúng theo plan F1:** đổi schema sang `quantity` + `cash` + `nav_declared` + `as_of` + `restrictions`; server reprice từ market data; báo `nav_computed` và delta.
3. Chạy lại `qshield-risk prepare-workflow` với danh mục người dùng thay vì copy handoff.

**Acceptance criteria.**
- Gửi hai request với `weights` khác nhau ⇒ nhận hai `qubo_hash` khác nhau (hoặc nhận lỗi rõ ràng).
- Không có đường nào để UI hiển thị số của danh mục A dưới nhãn danh mục B.

---

#### **P0-6 · Kết quả exact bị đặt dưới nhãn "quantum" ở tầng UI**

**Vấn đề.** Không phải bug logic — là bug ngữ nghĩa của label.
- Cột hiển thị tên là `quantum_reduction` (`frontend/components/quantum/ActionTable.tsx:22-25`), nguồn từ `final_recommendation.actions[].quantum_reduction` (`risk/cli.py:1170`), giá trị thực là **nghiệm exact solver** khi `actual_solver == "exact"` (100% artifact 20-bit hiện tại).
- Trang có tiêu đề "Quantum Optimizer", tab tên "Quantum", `card-title` "Raw quantum/exact vs polished final action".
- Có `actual_solver` hiển thị đúng (`quantum/page.tsx:88-91`) — nhưng nó là một badge nhỏ bên cạnh, còn nhãn cột thì nói "quantum".

**Tác động.** Người xem demo sẽ đọc "quantum_reduction = 30%" và kết luận QAOA đưa ra con số đó. Thực tế là brute-force cổ điển.

**Cách sửa.** Đổi tên field/cột theo `actual_solver`: `solver_reduction` + một cột `source_solver`. Khi `actual_solver != "qaoa"`, hiển thị banner: *"Run này không có kết quả QAOA — số hiển thị từ exact solver (fallback: {fallback_reason})."*

**Acceptance criteria.** Không có chuỗi "quantum" nào trên UI gắn với giá trị mà `actual_solver != "qaoa"`.

---

### P1 — Nên xử lý để nâng chất lượng kỹ thuật

---

#### **P1-1 · QAOA 20-bit không chạy được vì không transpile — trong khi giải pháp đã có sẵn**

- `qaoa.py:49` `_TRANSPILE_SAFE_MAX_QUBITS = 8` ⇒ n=20 → `_make_transpiler` trả `None` (`:55-56`) ⇒ đi đường `expm` trên ma trận 2²⁰×2²⁰.
- `solve_qaoa_one_seed_fast` (`:190-295`) + `_qaoa_worker.py` đã giải quyết đúng vấn đề này (transpile cưỡng bức trong subprocess + retry). Nhanh hơn **~14–100×** theo chính comment ở `:207`.
- **Nhưng `workflow.py:243` gọi `solve_qaoa_one_seed` thường.** Lý do: `_fast` không nhận `feasibility` callable tuỳ ý (không pickle được closure).
- **Nhưng `quantum_constraints` đang rỗng** ⇒ có thể dùng `always_feasible=True` (`qaoa.py:184-187` `_always_feasible` là hàm cấp module, pickle được).

**Cách sửa.** Trong `run_four_level_workflow`: nếu `constraints` rỗng → gọi `solve_qaoa_one_seed_fast(..., always_feasible=True)`. Nếu phi rỗng → serialize constraints thành dict (đã là dict thuần) và dựng lại predicate bên trong worker thay vì pickle closure.

**Acceptance criteria.** Ít nhất một artifact 20-bit với `actual_solver: "qaoa"`, `qaoa_seed_count >= 10`, `shots: 1024`, `maxiter: 200`.

---

#### **P1-2 · `dev_mode` bật mặc định trong profile sản phẩm**

`configs/workflow_update.yaml:330-336` — `enabled: true`, 1 seed / 128 shots / maxiter 10 / warm-start tắt. Bất kỳ ai chạy config mặc định đều nhận cấu hình không có ý nghĩa thống kê. `min_seeds: 10` ở `:315` bị `dev_mode` vô hiệu hoá (`quantum/cli.py:341`).

**Sửa:** `dev_mode.enabled: false` mặc định; bật qua `--override` khi cần chạy nhanh. Artifact phải mang cờ `DEV_MODE_REDUCED_SETTINGS` rõ ràng.

**AC:** Config mặc định ⇒ `solver_manifest.registered_seeds` có ≥10 phần tử.

---

#### **P1-3 · Classical benchmark không matched budget và đo sai đại lượng**

- Budget: classical 0,14–0,56s vs QAOA budget 600s/seed (`benchmark.py:233-238`, `workflow_update.yaml:365`).
- `qaoa_beats_classical` (`benchmark.py:348`) so **QUBO energy** chứ không so **true CVaR** — trong khi CLAUDE.md quy tắc 17 và plan D5 đều bắt buộc chấm bằng true objective.
- Classical khởi tạo sẵn all-ones (`:136`) — với landscape hiện tại nó thắng ở bước 0.

**Sửa:**
1. Thêm `classical_budget_seconds` khớp tổng runtime QAOA; dùng tabu/SA chạy đủ budget.
2. Đổi `qaoa_beats_classical` thành so sánh trên `true_objective` (đã có sẵn trong `true_benchmark.py`), hoặc đổi tên thành `qaoa_beats_classical_on_surrogate_energy`.
3. Ghi `objective_evaluations` cho mỗi solver để so công bằng theo số lần đánh giá.

**AC:** `workflow_benchmark.runtime_seconds.classical` nằm trong ±20% của `.qaoa`; UI hiển thị so sánh trên true CVaR.

---

#### **P1-4 · Verify chỉ chạy sampled ở 20-bit**

`quantum/cli.py:410` `verify_sample_size=4096` khi `NON_FINAL_CONFIG and bits >= 16`. Artifact: `verify_checked_states: 4098 / 1048576` = **0,39%**.

`verify_quadratic_consistency` gọi `qp.objective.evaluate(z)` trong vòng lặp Python cho từng z (`consistency.py:77-82`) — đây là lý do full enumeration quá chậm.

**Sửa:** Vectorise việc so sánh — trích `(Q, linear, constant)` từ `QuadraticProgram` một lần rồi tính batch bằng NumPy, thay vì gọi `evaluate` 1M lần. Full 2²⁰ khi đó chỉ mất vài giây.

**AC:** `verify_checked_states == 1048576` trong evidence run, runtime < 60s.

---

#### **P1-5 · Candidate gate stability không bao giờ được đánh giá**

`configs/workflow_update.yaml:568` `stability_rankings_path: null` ⇒ `risk/cli.py:534-538` trả `None` ⇒ `candidate_gate.py:167-168` luôn thêm `STABILITY_NOT_EVALUATED`. Kết quả là `median_overlap_at_n`, `worst_overlap_at_n`, `median_jaccard`, `median_spearman`, `median_kendall` **đều null trong mọi artifact**.

Đồng thời `sensitivity_coverage` cho thấy coverage@15 = 0,783 > ngưỡng 0,70 trong khi coverage@10 = 0,599 — tức là **N=10 không đủ**, cần N=15 (đúng plan CR-WF2-005), nhưng không có logic tự chọn.

**Sửa:** Sinh ranking variants bằng cách chạy lại candidate ranking với 5–10 seed bootstrap / block length khác nhau, ghi ra artifact, trỏ `stability_rankings_path` vào đó. Thêm logic dynamic N: thử 10→12→15, chọn N nhỏ nhất đạt **cả** coverage lẫn stability.

**AC:** `candidate_gate.json` có `median_overlap_at_n` phi null; có artifact ghi rõ N được chọn và lý do.

---

#### **P1-6 · Objective là weighted-sum, không phải lexicographic như plan D5**

`objective.py:240-251` cộng 6 thành phần đã scale. `priority: cvar_first` (`workflow_update.yaml:252`) **không có code nào đọc**. Plan D5 đề xuất lexicographic: trong các nghiệm đạt budget, chọn theo return sacrifice/cost/turnover thấp nhất, CVaR tie-break.

Weighted-sum với `scale` khác nhau 20× giữa các thành phần (`0.01` cho cost vs `0.2` cho turnover) khiến trọng số hiệu dụng khó diễn giải và dễ tạo degenerate như P0-1.

**Sửa:** Hoặc implement lexicographic thật, hoặc **xoá key `priority`** để không gây hiểu nhầm là đã có. Nếu giữ weighted-sum, phải fit weights/scales trên validation như plan D5 yêu cầu và ghi vào artifact bằng chứng fit đó.

**AC:** Không tồn tại config key mô tả hành vi không có trong code.

---

#### **P1-7 · Codec four-level cài đặt hai lần độc lập**

`quantum/formulation/four_level.py:60` (`10*b₀ + 20*b₁`) và `risk/sampling.py:40` (`0.10*b₀ + 0.20*b₁`). Hiện khớp nhau, nhưng CLAUDE.md quy tắc 11 nói rõ `risk ← quantum` là import chéo duy nhất được phép — và ở đây quantum đã import risk (`quantum/cli.py:37`). Codec nên nằm ở `contracts` và cả hai cùng import.

**AC:** Một nguồn duy nhất cho mapping bit→%; có test cross-check hai chiều encode/decode giữa hai package.

---

#### **P1-8 · Không có memory budget / kill process tree / peak memory**

Plan E3 yêu cầu hard wall-time **và memory** budget, dừng process tree khi tràn. Hiện có: timeout theo seed và total (`workflow.py:234-284`) — nhưng chỉ kiểm **sau khi seed kết thúc**, nên seed 337s vẫn chạy hết với budget 300s. `peak_memory_mb` = `null` trong mọi artifact. `reference_hardware.cpu/ram_gb/os` = `null`.

**AC:** `peak_memory_mb` và `reference_hardware` phi null trong evidence run; seed vượt budget bị hủy giữa chừng.

---

#### **P1-9 · `artifacts/dev/` bị ghi đè giữa các lần chạy**

Plan H1: *"Artifact theo run_id, không trộn `artifacts/dev` nhiều lần chạy"*. Git status hiện tại: 20+ artifact bị modified, 8 bị deleted (`artifacts/dev/optimization/*` biến mất hoàn toàn, `final_recommendation.json`, `reranked_candidates.csv`, `true_benchmark.json` cũng vậy). `metrics.json` chỉ giữ stage cuối cùng ghi (`risk_workflow`), không giữ lịch sử.

**AC:** Mỗi lần chạy sinh `artifacts/runs/<run_id>/`; `artifacts/dev/` chỉ là symlink/copy của run mới nhất.

---

#### **P1-10 · 3 test AI fail do config đã bị xoá**

`packages/ai/tests/test_config_keys.py:73` đọc `configs/scenarios.yaml` — file không tồn tại. `:82` assert `num_scenarios == 500`, thực tế `5000`. `test_cli_scenarios.py::test_scenarios_without_a_regime_artifact_fails_clearly` cũng fail.

Test drift sau khi gộp config. Không ảnh hưởng correctness nhưng làm CI không tin cậy được.

**AC:** `uv run pytest` xanh toàn bộ.

---

### P2 — UX / documentation / presentation

**P2-1.** Tagline landing *"Phòng vệ bằng lượng tử"* (`components/landing/Hero.tsx:85`) và title metadata *"Phòng vệ rủi ro danh mục bằng lượng tử"* (`app/landing/page.tsx:27`) nói quá so với thực tế (QAOA không chạy trên đường sản phẩm). Đề xuất: *"Phòng vệ rủi ro danh mục — mô hình hoá bằng QUBO"*.

**P2-2.** Card "Constraints: PASS" màu xanh (`quantum/page.tsx:94-98`) khi `constraints_passed` — nhưng giá trị này luôn `true` vì `risk_policy = null`. Nên hiển thị `NOT_EVALUATED` (màu xám) khi không có policy.

**P2-3.** `mean_feasibility_rate` hiển thị trên UI (`quantum/page.tsx:107-115`) là số vô nghĩa khi không có constraint. Ẩn hoặc ghi "n/a — no constraints encoded".

**P2-4.** `polishing_dependency` — chỉ số quan trọng nhất để hiểu "quantum đóng góp bao nhiêu" — không được hiển thị ở đâu. Nên đưa lên trang Quantum như một metric chính.

**P2-5.** `artifacts_bench/README.md` không cảnh báo rằng `warm_start_run`/`no_warm_start_run` là 10-bit với full settings, khác hẳn artifact 20-bit dev settings. Đây đúng là rủi ro plan R08 nêu.

**P2-6.** Trang Overview dùng "Recommended action" (`overview/page.tsx:91`) trong khi `handoff_status = "ANALYSIS_ONLY_NON_BASELINE_RUN"`. Nên đổi thành "Analysis output (NON_BASELINE)".

**P2-7.** `docs/workflow-v2.md` là SoT nhưng không có mục nào ghi rõ "component nào đã implement / chưa" — nên có một bảng trạng thái sống, cập nhật mỗi PR.

---

## 6. Phân tích hiện tượng all-ones

### 6.1 Bitstring đó là gì?

`11111111111111111111` (20 bit). Decode qua `four_level.py:60` (`10·b₀ + 20·b₁`): mỗi cặp `11` → **30%**.

⇒ **Bán 30% vị thế của cả 10 candidate.** Xác nhận trong artifact:
```json
"decoded_actions": {"MWG":0.30, "GVR":0.30, "BSR":0.30, "PLX":0.30, "GAS":0.30}
"turnover": 0.0499999999   // = 5 × 0.0333 × 0.30
```
(run 10-bit; run 20-bit tương tự với 10 mã, turnover ≈ 0.10)

Đây là **nghiệm biên tuyệt đối** — góc xa nhất của hypercube so với no-action.

### 6.2 Objective/target cash có khuyến khích nghiệm biên không? — CÓ, và đây là nguyên nhân chính

Số học chính xác:

```
Danh mục evidence: 30 mã equal-weight, mỗi mã w = 1/30 = 0.0333333
Top-10 candidates: tổng weight = 10 × 0.0333333 = 0.333333
Mức bán tối đa mỗi mã = 30%
⇒ Cash tối đa tạo được = 0.333333 × 0.30 = 0.10000

target_cash_increment = 0.10   (configs/workflow_update.yaml:506)
```

`objective.py:210-214`: `cash_deviation = |cash_increment − 0.1|`.
`configs/workflow_update.yaml:542-544`: weight 0.35 / scale 0.1 ⇒ hệ số hiệu dụng **3.5**.

**Deviation chỉ bằng 0 tại đúng một điểm: bán hết mức mọi mã.** Mọi hành động ít hơn đều bị phạt tuyến tính với hệ số 3.5 — lớn hơn nhiều so với lợi ích CVaR biên.

Đo thực tế trên 711 mẫu train:

| Thành phần | Đóng góp tại all-zero | Biên độ toàn tập |
|---|---|---|
| `cash_budget_deviation` | **0.35000** | **0.30257** |
| `cvar` | 0.74234 | 0.11157 |
| `turnover` | 0.0 | 0.02167 |
| `transaction_cost` | 0.0 | 0.00542 |
| `return_sacrifice` | 0.0 | 0.00297 |
| `liquidity_penalty` | 0.0 | 0.00108 |
| **Tổng objective** | **1.09234** | — |

Biên độ cash term (0.303) **lớn gấp 2,7×** biên độ CVaR (0.112) và **gấp 14×** tổng mọi chi phí giao dịch. Kết quả: `corr(objective, reduction_sum) = −0.9993`.

### 6.3 Nguyên nhân là gì? — Phân tách 4 khả năng

| Nghi vấn | Kết luận | Bằng chứng |
|---|---|---|
| **Risk logic sai (lẫn dấu loss/return)?** | **KHÔNG** | `loss_sign_convention: "positive_is_loss"`; CVaR trước 0.0742 → sau 0.0664 (giảm, đúng chiều); test tay pass |
| **Cost scaling quá nhỏ?** | **CÓ, thứ yếu** | Tổng cost span 0.0081 vs CVaR span 0.112 — cost gần như không có tiếng nói. Nhưng ngay cả khi cost lớn gấp 10×, cash term 0.303 vẫn thắng |
| **Cash constraint?** | **CÓ, đây là nguyên nhân chính** | Xem §6.2. Target 0.1 = max khả thi 0.1 ⇒ nghiệm duy nhất |
| **Surrogate sai?** | **KHÔNG** | all-ones là tối ưu **của cả true objective lẫn surrogate**. Mẫu true objective (`objective` column, tính bằng `financial_objective` thật) đã đơn điệu giảm theo `reduction_sum`. Surrogate chỉ trung thành tái tạo lại |

**Bổ sung — một dấu hiệu tài chính bất thường cần điều tra riêng:**
```
expected_return_before = 0.015609
expected_return_after  = 0.016575   ← TĂNG sau khi bán 30%
expected_return_sacrifice = 0.0
```
Bán cổ phiếu sang tiền mặt (yield 0%) mà **kỳ vọng lợi nhuận tăng** ⇒ scenario cube đang cho kỳ vọng lợi nhuận **âm** ở các mã này trên horizon 20 phiên. Đây là hệ quả của việc cube được bootstrap từ regime `volatile` với chỉ 71 block độc nhất trong cửa sổ 2026-03-17 → 2026-07-23.

⇒ **Trong cube này, bán mọi thứ đồng thời giảm rủi ro VÀ tăng lợi nhuận kỳ vọng.** Không tồn tại đánh đổi ⇒ không tồn tại bài toán tối ưu. Đây là lý do thứ hai, độc lập với cash target.

### 6.4 Cần kiểm baseline nào

`rerank.py:307-387` `build_financial_baselines` **đã implement** 3/5 baseline: `no_action`, `pro_rata`, `greedy`. Cần bổ sung và ghi thành artifact so sánh:

| Baseline | Trạng thái | Cách tính | Mục đích chẩn đoán |
|---|---|---|---|
| **no_action** | ✅ có (`:318-320`) | `reductions = 0` | Điểm tham chiếu tuyệt đối. Nếu all-ones không thắng no-action **sau chi phí** ⇒ không nên hành động |
| **pro_rata** | ✅ có (`:323-336`) | bán đều để chạm `cash_min` | Phân biệt "chọn đúng mã" vs "chỉ cần bán đủ tiền". **Nếu pro_rata ≈ optimal ⇒ bài toán không cần solver** |
| **greedy** | ✅ có (`:338-366`) | tăng dần 10% theo marginal CVaR | Baseline O(n) — nếu greedy = exact thì QUBO thừa |
| **cash-target-only** | ❌ thiếu | tối thiểu hoá **chỉ** `cash_budget_deviation`, bỏ CVaR | **Test quyết định:** nếu nghiệm này = nghiệm full objective ⇒ chứng minh cash term chi phối |
| **risk-only** | ❌ thiếu | tối thiểu hoá **chỉ** `cvar`, bỏ cash term | Cho thấy bài toán *thực sự* trông thế nào nếu bỏ cash constraint |
| **max-sell** | ❌ thiếu | all-ones cứng | Trivial upper bound — nếu bằng optimal thì optimal là trivial |

### 6.5 Cách phân biệt "nghiệm hợp lý" với "degenerate solution"

**Test 1 — Ablation từng thành phần objective.**
Chạy exact 6 lần, mỗi lần tắt một thành phần (weight = 0). Nếu nghiệm chỉ đổi khi tắt `cash_budget_deviation` ⇒ degenerate do cash term. *Dự đoán dựa trên số liệu: sẽ đúng.*

**Test 2 — Sweep target cash.**
Chạy với `target_cash_increment ∈ {0.02, 0.04, 0.06, 0.08, 0.10}`. Nghiệm hợp lý sẽ chuyển dần từ sparse sang dense. Nếu all-ones chỉ biến mất khi target < max khả thi ⇒ xác nhận cơ chế.

**Test 3 — Landscape diagnostics.** (đã có sẵn code trong `tools/qaoa_stress_bakeoff.py`)
- Số local minima theo 1-flip. Bài toán hiện tại: dự kiến **1** (chỉ có all-ones). Instance synthetic của team có **232**.
- `lin_over_quad_ratio`: tỷ lệ độ lớn hệ số tuyến tính / bậc 2. Ratio cao ⇒ QUBO gần như linear ⇒ không cần solver tổ hợp.
- Hamming distance từ optimum tới all-ones và tới all-zeros. Nghiệm hợp lý nằm ở giữa.

**Test 4 — Phân bố hạng của all-ones qua nhiều danh mục.**
Chạy trên ≥10 danh mục khác nhau (không equal-weight). Nếu all-ones luôn đứng #1 ⇒ degenerate. Nghiệm hợp lý phải phụ thuộc danh mục.

**Test 5 — Sanity kinh tế.**
`expected_return_after > expected_return_before` là cờ đỏ. Với cash yield 0%, bán cổ phiếu **phải** làm giảm kỳ vọng lợi nhuận trừ khi kỳ vọng của cổ phiếu âm. Kiểm tra `mean(cube)` theo từng mã; nếu âm ⇒ scenario generation có vấn đề, không phải optimizer.

**Test 6 — Perturbation trên chi phí.**
Chạy `cost_sensitivity.high` (`workflow_update.yaml:520-523`). Nếu all-ones vẫn thắng khi fee tăng 33% ⇒ chi phí không có tiếng nói trong objective, cần scale lại.

---

## 7. Kể câu chuyện quantum một cách trung thực

### 7.1 Quantum đóng vai trò gì trong hệ thống

**Vai trò thiết kế:** một **candidate generator** ở bước 5/7 của pipeline. Nó nhận một mô hình bậc 2 đã fit từ Risk, sinh ra một pool bitstring, và pool đó được chấm lại bằng true CVaR ở bước sau. Nó **không** dự báo thị trường, **không** ước lượng rủi ro, **không** quyết định danh mục cuối.

**Vai trò thực tế hiện tại:** chưa hoạt động trên đường sản phẩm. Exact solver đang đảm nhiệm vai trò này.

### 7.2 Vì sao action selection biểu diễn được bằng QUBO

Ba tính chất làm bài toán này *tự nhiên* là QUBO:

1. **Biến quyết định rời rạc và hữu hạn.** Mỗi mã có 4 lựa chọn, không phải một số thực. 4 = 2² ⇒ 2 bit/mã, ánh xạ song ánh, **không cần slack/ancilla**.
2. **Không gian tăng theo cấp số nhân.** 10 mã → 4¹⁰ ≈ 1,05 triệu tổ hợp. 15 mã → 4¹⁵ ≈ 1,07 tỷ. Đây là chỗ brute-force bắt đầu thất bại.
3. **Hàm mục tiêu có tương tác cặp thật.** Đây là điểm quan trọng nhất về mặt khái niệm — xem §7.3.

### 7.3 Interaction terms nào làm bài toán có ý nghĩa

CVaR của danh mục **không tách được thành tổng đóng góp từng mã**. Bán MWG làm thay đổi lợi ích biên của việc bán GVR, vì:

- **Tương quan chéo:** hai mã cùng ngành cùng rơi trong một kịch bản. Bán một mã đã cắt phần lớn đuôi mà mã kia đóng góp ⇒ lợi ích biên của mã thứ hai giảm (submodular).
- **Dịch chuyển đuôi:** CVaR₀.₉₅ là trung bình của 5% kịch bản xấu nhất. Bán một mã có thể **đổi tập kịch bản** nằm trong đuôi đó ⇒ toàn bộ marginal benefit của các mã khác được tính lại.
- **Ngân sách tiền mặt chung:** mọi mã cạnh tranh cho cùng một cash target ⇒ ràng buộc ghép cặp.
- **Chi phí thanh khoản phi tuyến:** bán nhiều mã cùng lúc trong một phiên.

Đây chính là các hệ số off-diagonal `Q[i,j]` mà surrogate đang fit (190 hệ số cặp tại d=20). **Nếu các hệ số này lớn so với hệ số tuyến tính, bài toán là combinatorial thật. Nếu nhỏ, bài toán suy biến về greedy.**

⚠️ **Trạng thái hiện tại: đang suy biến.** `tools/qaoa_stress_bakeoff.py` đo `lin_over_quad_ratio` và phải nhân hệ số bậc 2 lên **179×** để tạo instance có cấu trúc. Nghĩa là trong bài toán thật, phần bậc 2 nhỏ hơn phần tuyến tính khoảng hai bậc độ lớn.

### 7.4 Vì sao QAOA là candidate generator, không phải nguồn dự báo

QAOA không biết gì về thị trường. Nó nhận một ma trận `Q` và vector `linear` — những con số này đã được Risk tính xong từ scenario cube. QAOA chỉ tìm bitstring có năng lượng thấp. Mọi thông tin tài chính nằm ở upstream (Data → Regime → Scenario → Risk).

Hơn nữa, output của QAOA là một **phân phối xác suất trên bitstring**, không phải một đáp án. Đó là lý do `qaoa_results.json` lưu `candidate_pool` (`workflow.py:356-398`) và Risk rerank lại toàn bộ pool. Cách dùng đúng của QAOA trong kiến trúc này là: *"cho tôi 20 phương án hứa hẹn để tôi chấm bằng mô hình tài chính thật"* — chứ không phải *"cho tôi đáp án"*.

### 7.5 Exact và classical kiểm chứng quantum thế nào

- **Exact (2²⁰ duyệt hết):** cho `optimality_gap` tuyệt đối. Không có exact thì "QAOA ra nghiệm tốt" là câu vô nghĩa.
- **Classical local search:** cho biết bài toán có **cần** solver phức tạp không. Nếu coordinate descent 64 restart trong 0,5s ra đúng nghiệm exact, thì QAOA 40s không có lý do tồn tại về mặt kỹ thuật.
- **True CVaR rerank:** cho biết surrogate energy có tương quan với giá trị tài chính thật không. `ranking_disagreement` trong `true_benchmark.json` là chỉ số này.

Ba lớp kiểm chứng này **đều đã có trong code**. Đây là điểm mạnh thật.

### 7.6 Metric bắt buộc phải hiển thị trên UI/report

| Metric | Nguồn | Vì sao bắt buộc |
|---|---|---|
| `requested_solver` / `actual_solver` | `workflow_benchmark.json` | Phân biệt "định chạy QAOA" và "thực sự chạy gì" |
| `fallback_reason` | như trên | Nếu fallback, phải nói vì sao |
| `backend` = "StatevectorSampler" | `solver_manifest` | Không được để người xem tưởng là QPU |
| `qaoa_seed_count` / `n_seeds_feasible` | như trên | 0 seed = không có QAOA |
| `shots`, `maxiter`, `reps`, `warm_start` | `solver_manifest` | Cấu hình dev vs full khác nhau 100× |
| `optimality_gap` vs exact | như trên | Con số duy nhất định lượng chất lượng QAOA |
| `exact_evaluated_states` | như trên | Chứng minh ground truth đầy đủ |
| **`true_cvar_before/after`** | `true_benchmark.json` | Đại lượng tài chính duy nhất có nghĩa với người dùng |
| **`materiality_met`** | như trên | Cải thiện có vượt ngưỡng 1% sau chi phí không |
| **`polishing_dependency`** | `final_recommendation.json` | Bao nhiêu % cải thiện đến từ polish cổ điển thay vì solver |
| `classical_energy` + runtime | `workflow_benchmark.json` | Không có nó thì không so được |
| `profile_status` = NON_BASELINE_RUN | provenance | Phải xuất hiện trên mọi trang |

### 7.7 Claim được phép / phải tránh

**✅ ĐƯỢC PHÉP (có bằng chứng trong repo):**
- "Bài toán chọn hành động phòng vệ four-level đã được formulate thành QUBO 20 biến nhị phân, verify khớp trên ba đường tính độc lập."
- "Exact solver duyệt đủ 2²⁰ = 1.048.576 trạng thái trong ~38 giây, làm ground truth."
- "QAOA đã chạy thật trên simulator statevector ở quy mô 10 biến, đạt optimality gap 0–2,03% so với exact tuỳ cấu hình warm-start."
- "Mọi nghiệm solver được chấm lại bằng true CVaR trên scenario cube, không chọn theo QUBO energy."
- "`qubo_hash` ổn định giữa các lần chạy độc lập — kết quả tái lập được."
- "Hệ thống báo cáo trung thực khi QAOA không hoàn thành, ghi rõ solver thực trả nghiệm."

**❌ CHƯA ĐƯỢC PHÉP:**
- "QAOA giải bài toán 20 biến của Q-SHIELD." — chưa có artifact nào
- "Quantum advantage" / "nhanh hơn cổ điển" — classical nhanh hơn 600–2400× và cho nghiệm bằng hoặc tốt hơn
- "Chạy trên máy tính lượng tử" / "không giả lập" — 100% simulator
- "Quantum tìm ra chiến lược phòng vệ giảm X% CVaR" — nghiệm hiện tại đến từ exact solver
- "QAOA tự tìm ra nghiệm tối ưu" (với warm_start_run) — SLSQP cổ điển đã prime initial state
- "Bài toán quá lớn cho máy tính cổ điển" — exact duyệt hết trong 38s trên laptop
- "Phòng vệ bằng lượng tử" như một mô tả sản phẩm

### 7.8 Narrative đề xuất (3–5 câu, dùng được trong tài liệu kỹ thuật)

> Q-SHIELD mô hình hoá bài toán chọn hành động phòng vệ — mỗi mã trong shortlist nhận một trong bốn mức bán 0/10/20/30%, mã hoá bằng hai bit — thành một QUBO 20 biến, trong đó các hệ số bậc hai biểu diễn tương tác chéo giữa các mã trong đuôi phân phối lỗ mà CVaR không tách rời được. QAOA được dùng như một **bộ sinh ứng viên**: nó trả về một phân phối bitstring, không phải một đáp án, và mọi ứng viên đều được chấm lại bằng true CVaR trên scenario cube trước khi vào báo cáo. Exact solver duyệt đủ 2²⁰ trạng thái đóng vai trò ground truth, còn local search cổ điển đóng vai trò đối chứng ngân sách; cả ba giải cùng một QUBO được xác thực bằng `qubo_hash`. Ở quy mô hiện tại, exact và classical đủ nhanh và cho nghiệm ngang bằng, nên **chúng tôi không tuyên bố quantum advantage** — giá trị của nhánh quantum nằm ở việc chứng minh bài toán biểu diễn được dưới dạng QUBO và ở khả năng mở rộng khi số ứng viên tăng, chứ chưa nằm ở hiệu năng đo được hôm nay. Toàn bộ QAOA chạy trên simulator statevector của qiskit; `backends/hardware.py` cố ý để trống.

---

## 8. Thiết kế benchmark và thí nghiệm

### E1 — Classical-only vs Classical+QAOA (thí nghiệm quyết định)

| Yếu tố | Quy định |
|---|---|
| Objective | Cùng một `qubo_hash` |
| Candidate order | Cùng `candidate_order_hash` |
| Feasible domain | Cùng predicate (sau khi P0-3 được sửa) |
| Budget | Cùng wall-time **và** cùng số lần đánh giá objective |
| Arm A | classical local search, budget T |
| Arm B | QAOA (budget T/2) → pool → classical polish (budget T/2) |
| Cả hai arm | đi qua đúng cùng rerank + polish |
| Metric chính | `true_objective` sau polish, không phải QUBO energy |

**Cấm:** inject nghiệm exact vào QAOA; cherry-pick seed; so QAOA full-settings với classical dev-settings.

**Diễn giải:** nếu Arm B không thắng Arm A về `true_objective` với ngân sách bằng nhau ⇒ QAOA hiện chưa đóng góp incremental value. Đó là kết quả hợp lệ và phải báo cáo (plan E4: *"Không yêu cầu kết quả phải thắng mới được báo"*).

### E2 — Multi-seed stability

10 seed đăng ký trước (đã có trong config), báo **toàn bộ** kể cả seed tệ. Metric: `energy_stats.{best, median, worst, std}`, `n_seeds_feasible/n_seeds_total`, `success_prob` phân phối. Ngưỡng đề xuất: `std/|median| < 0.05` mới coi là ổn định.

### E3 — Surrogate energy vs true financial objective

Trên toàn bộ pool ≥50 bitstring: tính Spearman ρ giữa `qubo_energy` và `true_objective`; đếm `ranking_disagreement ≠ 0`; đo top-20 recall (bao nhiêu trong top-20 theo surrogate thực sự nằm trong top-20 theo true objective). **Đây là thí nghiệm chứng minh surrogate có dùng được không** — hiện đang thiếu hoàn toàn (P0-2).

### E4 — Bảng metric bắt buộc cho mọi so sánh solver

`feasible_rate` · `best_feasible_true_objective` · `true_CVaR_after` · `turnover` · `transaction_cost` · `runtime_seconds` · `objective_evaluations` · `peak_memory_mb` · `seed_std` · `optimality_gap_vs_exact`

### E5 — Scaling theo số asset / action level

| n candidates | bits | states | exact khả thi? | QAOA statevector RAM |
|---|---|---|---|---|
| 5 | 10 | 1.024 | ✅ 0,04s | trivial |
| 8 | 16 | 65.536 | ✅ ~2s | ~1 MB |
| 10 | 20 | 1.048.576 | ✅ ~38s | ~16 MB |
| 12 | 24 | 16.777.216 | ✅ ~10 phút | ~268 MB |
| 15 | 30 | 1.073.741.824 | ⚠️ ~10 giờ | **~16 GiB** (plan R09) |

Chạy exact + classical + QAOA ở n = 5, 8, 10, 12 với **cùng settings**; fit đường cong runtime. Đây mới là "thí nghiệm scaling có kiểm soát" mà plan R08 yêu cầu — khác hẳn việc so hai batch settings khác nhau.

Lưu ý plan R09: 30 bit statevector complex128 = 2³⁰ × 16 byte = 16 GiB **chưa kể overhead**. Không chạy trên laptop.

### E6 — Ablation warm-start

Đã có dữ liệu sơ bộ (`artifacts_bench/warm_start_run` vs `no_warm_start_run`) nhưng chỉ 1 instance. Cần: ≥5 instance × 10 seed × 2 arm. Báo riêng:
- Nghiệm đến từ SLSQP pre-solver hay từ đo lượng tử? Đo bằng `success_prob` và bằng cách so nghiệm QAOA với nghiệm relaxation của SLSQP.
- **Bắt buộc:** ghi rõ trong artifact rằng warm-start = classical priming.

### E7 — Ablation penalty / constraint

Sau khi P0-3 được sửa: sweep `P ∈ {0.5, 1, 2, 5, 10} × suggest_penalty()`. Đo `feasibility_rate` và `optimality_gap` theo P. Kỳ vọng: P quá nhỏ → nhiều nghiệm infeasible; P quá lớn → landscape phẳng, QAOA khó hội tụ. Đây là thí nghiệm chuẩn của QAOA có ràng buộc.

### E8 — Out-of-sample trên holdout (P0-2)

Fit surrogate trên train, chọn hyperparameter trên validation, **xác nhận một lần** trên holdout. Holdout không được dùng để chọn bất cứ thứ gì.

### E9 — Scenario regime stress testing

Chạy toàn bộ pipeline riêng cho từng regime (`normal` / `volatile` / `stress`) — cần sửa stress pool trước (P0-4). So nghiệm tối ưu giữa 3 regime: **nếu nghiệm không đổi theo regime, hệ thống không phản ứng với thị trường** và toàn bộ nhánh AI/regime là trang trí.

### E10 — Ablation objective (bổ sung, quan trọng nhất cho P0-1)

6 lần chạy exact, mỗi lần zero-out một thành phần objective. Ghi nghiệm + Hamming distance tới all-ones. Đây là thí nghiệm rẻ nhất (6 × 38s) và trả lời trực tiếp câu hỏi degenerate.

### Điều kiện để được dùng từ "quantum advantage"

Cần **đồng thời**:
1. Instance mà exact không khả thi (n ≥ 15 bit thật sự cần thiết về mặt tài chính, không phải tăng N để tạo câu chuyện — plan R09).
2. Classical baseline mạnh (tabu/SA/branch-and-bound), matched budget, được tune tử tế.
3. QAOA thắng trên **true financial objective**, không phải surrogate energy.
4. Thắng ổn định qua ≥10 seed, ≥5 instance, có CI.
5. Chạy trên hardware thật hoặc có phân tích noise/scaling nghiêm túc.

**Hiện tại: 0/5.**

---

## 9. Roadmap ưu tiên

### Giai đoạn 0 — Sửa ngay (trước bất kỳ demo nào)

| # | Việc | Expected outcome |
|---|---|---|
| 0.1 | `quantum/cli.py:514,777` — bỏ `gate_status: "PASS"` hard-code | Không còn artifact báo PASS khi QAOA skip |
| 0.2 | `ai/cli.py:616-618` — `skipped_regimes` phi rỗng ⇒ `INCOMPLETE` | Scenario gate phản ánh đúng việc thiếu Stress |
| 0.3 | Backend: từ chối hoặc cảnh báo rõ khi `weights` không được áp dụng | Người dùng không nhận số của danh mục khác |
| 0.4 | UI: đổi `quantum_reduction` → `solver_reduction` + banner khi `actual_solver != "qaoa"` | Không còn nhãn "quantum" trên kết quả exact |
| 0.5 | `dev_mode.enabled: false` mặc định | Config mặc định là cấu hình có ý nghĩa |
| 0.6 | Sửa 3 test AI fail | CI xanh, tin cậy được |

### Giai đoạn 1 — Trước baseline approval

| # | Việc | Expected outcome |
|---|---|---|
| 1.1 | **Sửa objective degenerate** (P0-1): cash band thay target cứng, hạ weight, danh mục không equal-weight | `corr(objective, reduction_sum)` < 0.85; nghiệm không còn là all-ones |
| 1.2 | **Surrogate validation gate** (P0-2): stage mới, 4 metric, hard-stop | `surrogate_validation.json` tồn tại, pipeline fail khi ρ < 0.7 |
| 1.3 | **Encode constraints** (P0-3): Risk xuất `quantum_constraints` thật; penalty vào QUBO cho ràng buộc tuyến tính | `feasible_states < evaluated_states`; feasibility metric có tín hiệu |
| 1.4 | Sửa stress pool: điều tra 259 `incomplete_panel`, tách market-feature panel khỏi asset panel (plan C5) | Cả 3 regime có cube |
| 1.5 | Candidate gate stability: sinh ranking variants, dynamic N 10→12→15 | `median_overlap_at_n` phi null; N được chọn có lý do ghi lại |
| 1.6 | Thêm 3 baseline còn thiếu (cash-target-only, risk-only, max-sell) | Bảng 6 baseline đầy đủ trong artifact |
| 1.7 | Artifact theo `run_id`, không ghi đè `artifacts/dev/` | Replay được mọi run lịch sử |
| 1.8 | E10 ablation objective (6 lần chạy) | Xác nhận/bác bỏ giả thuyết cash term chi phối |

### Giai đoạn 2 — Chứng minh quantum contribution

| # | Việc | Expected outcome |
|---|---|---|
| 2.1 | Bật `solve_qaoa_one_seed_fast` trong `run_four_level_workflow` (P1-1) | Artifact 20-bit đầu tiên với `actual_solver: "qaoa"`, 10 seed, 1024 shots |
| 2.2 | Vectorise `verify_quadratic_consistency` (P1-4) | Full 2²⁰ verify < 60s |
| 2.3 | Classical benchmark matched budget + đo trên true objective (P1-3) | So sánh công bằng, đúng đại lượng |
| 2.4 | E1 ablation classical-only vs classical+QAOA | Con số incremental value đầu tiên (dù âm) |
| 2.5 | E2 multi-seed stability + E6 ablation warm-start ≥5 instance | Biết QAOA ổn định tới đâu và warm-start đóng góp bao nhiêu |
| 2.6 | E5 scaling n = 5/8/10/12 cùng settings | Đường cong scaling có kiểm soát (trả lời plan R08) |
| 2.7 | E7 ablation penalty (sau 1.3) | Chọn P có cơ sở, không đoán |
| 2.8 | E9 stress testing theo regime (sau 1.4) | Chứng minh hệ thống phản ứng với regime |
| 2.9 | Memory/process budget (P1-8) | `peak_memory_mb`, `reference_hardware` phi null |

### Giai đoạn 3 — UX / Documentation

| # | Việc | Expected outcome |
|---|---|---|
| 3.1 | Đổi tagline landing, bỏ "Phòng vệ bằng lượng tử" | Marketing khớp với capability thật |
| 3.2 | Hiển thị `polishing_dependency` trên trang Quantum | Người xem hiểu quantum đóng góp bao nhiêu |
| 3.3 | Ẩn/gắn nhãn `feasible_rate`, `constraints_passed` khi không có constraint/policy | Không hiển thị số vô nghĩa màu xanh |
| 3.4 | `artifacts_bench/README.md`: cảnh báo 10-bit-full vs 20-bit-dev | Tránh so sánh sai (plan R08) |
| 3.5 | Bảng trạng thái implement sống trong `docs/workflow-v2.md` | Plan và code không lệch nữa |
| 3.6 | Tạo `configs/policies/{risk_appetite,claim_policy}.yaml` + `decision_registry.yaml` (plan A3/A4/A5) | Governance có nơi cư trú thật |
| 3.7 | Thêm `approved_by`/`approved_at`/`effective_scope` (plan H2) | Không suy approval từ tên tác giả file |

---

## 10. Kết luận

### Ý tưởng tổng thể có đáng tiếp tục không?

**Có, rõ ràng đáng.** Bài toán thật, phạm vi được đóng băng hợp lý, kiến trúc đủ tốt để chịu được việc sửa các vấn đề nêu trên mà không phải viết lại. Điều đáng giá nhất không phải là quantum — mà là **hệ thống bằng chứng**: provenance hash xuyên suốt, exact ground truth, rerank bằng true objective, fallback trung thực, materiality gate. Đó là bộ khung mà rất nhiều dự án fintech nghiêm túc không có.

### Phần nào đang thật sự tốt

1. **Contracts + provenance + reproducibility.** `qubo_hash` ổn định giữa hai run độc lập là bằng chứng thực nghiệm, không phải lời hứa.
2. **Kỷ luật trung thực solver.** `requested_solver` vs `actual_solver` + `fallback_reason` bắt buộc + `seed_status` per-seed. Hiếm.
3. **Risk engine.** CVaR đúng định nghĩa, quy ước dấu nhất quán, cost tách thành phần, materiality gate, test tay.
4. **Regime labeling theo thống kê + filtered posterior.** Đúng cả CLAUDE.md quy tắc 7 lẫn plan R03.
5. **Encoding four-level.** Song ánh, không ancilla, không cần penalty cardinality — thiết kế sạch.
6. **Rerank + polishing với `polishing_dependency`.** Chỉ số đo được "quantum đóng góp bao nhiêu" — thiết kế xuất sắc, chỉ tiếc chưa dùng.
7. **Văn hoá tự phê bình.** `tools/qaoa_stress_bakeoff.py` tự vạch ra vấn đề degenerate. Comment trong `qaoa.py` không giấu phần chưa giải quyết.

### Phần nào hiện mới là prototype

- **Toàn bộ nhánh quantum trên đường sản phẩm** — chưa có một artifact 20-bit nào có QAOA chạy thật.
- **Scenario generation** — thiếu regime Stress, 5000 kịch bản từ 71 block, kỳ vọng lợi nhuận âm bất thường.
- **Bài toán tối ưu** — degenerate, không có cấu trúc tổ hợp.
- **Backend personalization** — nhận input nhưng không dùng.
- **Governance artifacts** — `risk_appetite.yaml`, `claim_policy.yaml`, `decision_registry.yaml` chỉ tồn tại trong plan.
- **Surrogate validation, walk-forward, UAT harness** — chưa có code.

### Quantum contribution đã được chứng minh đến mức nào?

Đo theo 5 mức:

| Mức | Nội dung | Trạng thái |
|---|---|---|
| 1 | Bài toán biểu diễn được thành QUBO | ✅ **Đã chứng minh** — verify 3 đường tính khớp |
| 2 | QAOA chạy được và ra nghiệm hợp lệ | ✅ **Đã chứng minh ở 10-bit** trên simulator, gap 0–2,03% |
| 3 | QAOA chạy được ở quy mô sản phẩm (20-bit) | ❌ **Chưa** — mọi artifact `qaoa_seed_count: 0` |
| 4 | QAOA đóng góp incremental value so với classical-only, cùng budget | ❌ **Chưa** — chưa có thí nghiệm |
| 5 | Quantum advantage | ❌ **Chưa, và với bài toán hiện tại là không thể** — exact duyệt hết trong 38s |

**Kết luận: chứng minh được đến mức 2/5.** Và điều quan trọng phải nói thẳng: **với hàm mục tiêu hiện tại (degenerate, corr = −0,9993), mức 4 và 5 là không đạt được về nguyên tắc** — không phải vì QAOA yếu, mà vì bài toán không có gì để giải. Sửa P0-1 là điều kiện tiên quyết cho mọi tham vọng quantum.

### Hệ thống hiện nên được mô tả là gì?

> **"Một khung phân tích rủi ro đuôi có kiểm chứng cho danh mục cổ phiếu VN30, chạy trên dữ liệu thị trường thật, với một nhánh nghiên cứu formulate bài toán chọn hành động phòng vệ dưới dạng QUBO và giải bằng exact solver, local search cổ điển và QAOA trên simulator. Trạng thái: NON_BASELINE_RUN — chưa nghiệm thu, không phải khuyến nghị đầu tư."**

Không phải: "hệ thống phòng vệ danh mục bằng lượng tử".

### Một câu claim AN TOÀN có thể dùng ngay

> *"Q-SHIELD formulate bài toán chọn hành động phòng vệ four-level thành QUBO 20 biến nhị phân, xác thực công thức khớp tuyệt đối trên ba đường tính độc lập, và đối chiếu nghiệm với exact solver duyệt đủ 2²⁰ trạng thái cùng local search cổ điển; mọi nghiệm được chấm lại bằng true CVaR trên scenario cube. QAOA chạy trên simulator statevector của qiskit — chúng tôi không tuyên bố quantum advantage."*

### Một câu claim CHƯA ĐƯỢC PHÉP dùng

> ~~*"Q-SHIELD dùng thuật toán lượng tử QAOA để tìm ra chiến lược phòng vệ tối ưu, giảm 10,6% CVaR cho danh mục VN30 — bài toán mà máy tính cổ điển không giải được."*~~

Sai ở **năm** điểm, mỗi điểm đều kiểm chứng được từ artifact trong repo:
1. Nghiệm đến từ **exact solver**, không phải QAOA (`actual_solver: "exact"` trong 100% artifact 20-bit).
2. Máy tính cổ điển giải bài toán này trong **0,56 giây** (`runtime_seconds.classical`), exact duyệt hết trong 38 giây.
3. Con số 10,6% đến từ run 10-bit trên 5 mã, không phải workflow 20-bit.
4. Nghiệm đó là all-ones — hệ quả của một `target_cash_increment` cứng bằng đúng lượng tiền tối đa có thể tạo ra, không phải kết quả của tối ưu hoá.
5. Run mang trạng thái `NON_BASELINE_RUN` với `candidate_gate: FAIL` và regime Stress rỗng.

---

## Phụ lục A — Phân biệt đường legacy 8-bit và workflow 20-bit hiện tại

| | Legacy 8-bit | Workflow 20-bit (SoT) |
|---|---|---|
| Entry point | `qshield-quantum solve` (`cli.py:529`) | `qshield-quantum workflow` (`cli.py:280`) |
| Biến | 8 mã × 1 bit ("có hành động hay không") | 10 mã × 2 bit (4 mức) |
| Objective | `−g'z + λ₁z'Cz + λ₂c'z + P(Σz−K)²` (`formulation/objective.py:29`) | Quadratic surrogate fit từ true objective (`surrogate.py`) |
| Ràng buộc | K-of-N với penalty trong QUBO (`penalty.py:15-26`) | Predicate ngoài QUBO, hiện **rỗng** (`workflow.py:206`) |
| Exact | `solve_exact` — 256 states (`exact.py:56-97`) | `solve_quadratic_exact` — 2²⁰ chunked (`exact.py:100-159`) |
| Classical | greedy top-K theo `g` (`benchmark.py:26-53`) | multi-start coordinate descent (`benchmark.py:122-172`) |
| Verify | `verify_consistency` full 256 (`consistency.py:118-180`) | `verify_quadratic_consistency`, sampled ở 20-bit (`:46-115`) |
| Artifact | `qaoa_result.json`, `benchmark.json` | `qubo_model.json`, `exact_solution.json`, `qaoa_results.json`, `workflow_benchmark.json` |
| Trạng thái | **Legacy** — giữ cho unit test/verify | **Đường sản phẩm** |

Đường legacy vẫn còn code và test đầy đủ. Không có gì sai, nhưng **docstring của nhiều file legacy vẫn nói "8 mã, K=3, 256 bitstring"** (`objective.py:5-6`, `exact.py:1-2`, `decode.py:2-6`, `qiskit_program.py:26`, `simulator.py:2`) trong khi các hàm đó đang được đường 20-bit dùng lại. Đây là nguồn nhầm lẫn thật cho người đọc code lần đầu — nên cập nhật docstring (P2).

## Phụ lục B — Phân biệt "requested solver" và "actual solver" trong mọi artifact

| Artifact | requested | actual | fallback_reason | qaoa_seed_count |
|---|---|---|---|---|
| `artifacts/runs/job_eae747c8.../workflow_benchmark.json` | qaoa | **exact** | "QAOA skipped/timeout in NON_FINAL_CONFIG" | 0 |
| `artifacts/runs/job_086a4f16.../workflow_benchmark.json` | qaoa | **exact** | như trên | 0 |
| `artifacts_bench/warm_start_run/` (10-bit) | qaoa | **qaoa** | null | 10 |
| `artifacts_bench/no_warm_start_run/` (10-bit) | qaoa | **exact** | "QAOA seed timeout (300s) on seed=101 (runtime=337.2s)" | 10 (chạy nhưng vượt budget) |
| `artifacts_bench/stress_run/` (synthetic 10-bit) | qaoa | qaoa | — | 1 |

**Chỉ có một artifact 10-bit duy nhất (`warm_start_run`) có `actual_solver: "qaoa"` — và nghiệm của nó được prime bởi SLSQP cổ điển.**

## Phụ lục C — Lệnh tái tạo các số trong review này

```bash
# corr(objective, reduction_sum) và biên độ từng thành phần
python3 -c "
import pandas as pd
d = pd.read_parquet('artifacts/dev/risk/qubo_objective_samples.parquet')
print('corr =', d.objective.corr(d.reduction_sum))
for c in ['cvar','cash_budget_deviation','turnover','transaction_cost',
          'return_sacrifice','liquidity_penalty']:
    col = d[c+'_contribution']
    print(f'{c:24s} span={col.max()-col.min():.5f}')
"

# Xác nhận target cash = max cash khả thi
python3 -c "
import pandas as pd
d = pd.read_csv('artifacts/dev/risk/candidate_top10.csv')
sel = d[d.selected_top10 == True]
print('max cash =', sel.current_weight.sum() * 0.30, '| target = 0.10')
"

# Stress regime bị skip nhưng gate PASS
python3 -c "
import json
m = json.load(open('artifacts/dev/scenarios/scenario_manifest.json'))
print('gate_status =', m['gate_status'])
print('skipped     =', m['skipped_regimes'])
print('unique_blocks =', m['primary']['unique_blocks_used'],
      '| reuse_rate =', m['primary']['reuse_rate'])
"

# Không có artifact 20-bit nào có QAOA
grep -l '"actual_solver": "exact"' artifacts/runs/*/outputs/optimization/workflow_benchmark.json

# Surrogate validation không có code
grep -rn "surrogate_validation" packages backend --include="*.py"   # → rỗng
```

---

*Review dựa hoàn toàn trên source code và artifact có trong repository tại commit `380974a`, branch `staging-tan-dev`, ngày 2026-09-03. Không có behavior nào được suy đoán. Mọi con số đều tái tạo được bằng lệnh ở Phụ lục C. Không có file nào bị chỉnh sửa trong quá trình review.*

---

# Phụ lục D — Trạng thái khắc phục (cập nhật 2026-09-04)

Bốn nhánh sửa chạy song song. Một nhánh hoàn tất, ba nhánh bị ngắt giữa chừng do hết session limit; phần dở dang được kiểm kê và hoàn thiện thủ công. **Trạng thái test cuối: 446 passed / 0 failed / ruff sạch** (8 test `slow` deselect).

## D.1 Đã xong

| ID | Nội dung | Bằng chứng |
|---|---|---|
| **P0-4a** | Scenario gate không còn PASS khi thiếu regime. Thêm `GATE_INCOMPLETE`; ưu tiên `FAIL > INCOMPLETE > WARN > PASS`; manifest ghi `gate_incomplete_reason` | `packages/ai/src/qshield_ai/cli.py`, `packages/ai/src/qshield_ai/scenarios/validate.py` |
| **P0-4b** | Bỏ `gate_status: "PASS"` hard-code. Thay bằng `_derive_gate_status()` suy từ `requested_solver`/`actual_solver`/`verify_full`/`seed_count` | `packages/quantum/src/qshield_quantum/cli.py:279`, dùng ở `:543` và `:831` |
| **P0-4c** | Rerank gate trả `NOT_EVALUATED` khi không có policy để kiểm, thay vì PASS giả | `packages/risk/src/qshield_risk/cli.py` |
| **P0-4d** | Diagnostic `block_diversity` với `effective_independent_windows` = số block độc nhất. Ngưỡng đọc từ config, vắng thì báo `NOT_CONFIGURED_PENDING_OWNER` — không tự bịa | `packages/ai/src/qshield_ai/cli.py` |
| **P0-3** | `policy_to_quantum_constraints()` dịch `RiskPolicy` sang predicate phía Quantum; `risk_summary.json` thêm `constraints_encoding` nói rõ ràng buộc nào vào QUBO, ràng buộc nào còn ở ngoài | `packages/risk/src/qshield_risk/policy.py`, `cli.py` |
| **P0-5** | Backend so `request.weights` với handoff, trả `personalization_status` + hai sha256. UI hiện callout đỏ khi `NOT_APPLIED` | `backend/.../subprocess_optimize_runner.py`, `frontend/components/quantum/RunOptimizePanel.tsx` |
| **P0-6** | Banner cảnh báo khi `actual_solver !== "qaoa"`; cột đổi thành "Solver reduction" + badge `source_solver` | `frontend/app/(console)/quantum/page.tsx`, `components/quantum/ActionTable.tsx` |
| **P1-1** | QAOA 20-bit dùng `solve_qaoa_one_seed_fast` (subprocess + transpile cưỡng bức + retry); constraints rỗng → `always_feasible=True` (pickle-safe) | `packages/quantum/src/qshield_quantum/workflow.py:270` |
| **P1-4** | Verify vectorised. `_qp_energy_arrays` + `_batch_energy` thay 2^20 lời gọi `objective.evaluate`. **Full 2²⁰ đo được 2,78s** (tiêu chí <60s). Gỡ mặc định lấy mẫu 4096; giữ `--verify-sample-size` làm lối thoát thủ công, và nó hạ `gate_status` | `packages/quantum/.../verify/consistency.py:44-72`, `cli.py:422` |
| **P1-10** | 3 test AI fail do đọc `configs/scenarios.yaml` đã xoá — sửa nguồn config, giữ nguyên mục đích test | `packages/ai/tests/test_config_keys.py`, `test_cli_scenarios.py` |
| **P2-1..4** | Tagline bỏ "bằng lượng tử"; `NOT_EVALUATED` xám thay PASS xanh; `feasible_rate` hiện "n/a — no constraints encoded"; thêm card `polishing_dependency` | `frontend/`, `backend/.../console/` |
| Baselines | Thêm `cash_target_only`, `risk_only`, `max_sell` vào `build_financial_baselines` | `packages/risk/src/qshield_risk/rerank.py` |

## D.2 Bug phát sinh trong quá trình sửa — đã tìm ra và sửa

**`RunContext.logger()` mất `logs.txt` khi trùng `run_id`.** Không nằm trong review gốc; phát hiện khi một test AI đổi trạng thái pass→fail.

`packages/contracts/src/qshield_contracts/runs.py:43` đặt tên logger là `qshield.{run_id}.{name}` rồi bỏ qua nếu `logger.handlers` phi rỗng. `logging.getLogger` là registry toàn cục theo tiến trình, nên hai `RunContext` khác `run_root` nhưng trùng `run_id` nhận đúng một logger — lần thứ hai tái dùng `FileHandler` cũ trỏ vào thư mục cũ và **`logs.txt` của run mới không bao giờ được tạo**. Mất lặng lẽ một trong bốn file metadata bắt buộc (CLAUDE.md quy tắc 13).

Sửa: so `handler.baseFilename` với `run_root` hiện tại, dựng lại handler khi lệch. Test hồi quy `test_second_run_context_with_same_run_id_still_writes_its_own_logs` (`packages/contracts/tests/test_runs.py`) đã kiểm chứng hai chiều — bỏ fix thì fail, có fix thì pass.

Production hiện không dính vì `pipeline/run.py` chạy mỗi stage trong subprocess riêng. Nó sẽ dính ngay khi có hai `RunContext` cùng tiến trình.

## D.3 Trạng thái các mục còn nợ (cập nhật cuối)

| ID | Nội dung | Trạng thái |
|---|---|---|
| **P0-2** | Surrogate validation gate trên holdout | **XONG.** `formulation/validation.py` + `surrogate_validation.json` + gate nối vào `_derive_gate_status`. Chạy thật: PASS, holdout ρ=1.0000. 6 test |
| **P0-1** | CLI `objective-diagnostics` | **XONG.** `risk/diagnostics.py` + lệnh CLI. Chạy thật trên dữ liệu evidence, kết quả ở Phụ lục E.1. 8 test |
| **P1-3** | Classical benchmark matched budget | **XONG.** `budget_seconds` khớp wall-time QAOA, `classical_search_stats` (số restart, số lần đánh giá objective), thêm khoá `qaoa_beats_classical_on_surrogate_energy` rõ nghĩa (giữ tên cũ để không phá backend). 3 test |
| **P1-5** | Ranking variants + dynamic N | **XONG.** Bootstrap variants nối vào gate; dynamic N 10→12→15 chọn N nhỏ nhất PASS. Chạy thật: N=15. 4 test. Hệ quả ở Phụ lục E.3 |
| **P1-4** | Verify full 2^20 mặc định | **XONG.** Gỡ hẳn mặc định lấy mẫu 4096. Chạy thật qua CLI: `checked=1048576 sampled=False` trong 2,69s |
| **P1-2** | `dev_mode.enabled: false` | **CHƯA — có lý do thực nghiệm, xem D.5** |

### Bằng chứng đối chiếu trước/sau trên cùng một lệnh

`qshield-quantum workflow --exact-only`, cùng handoff Risk:

| | Trước | Sau |
|---|---|---|
| `gate_status` | `PASS` | `FALLBACK` |
| `verify_checked_states` | 4.098 / 1.048.576 (0,39%) | **1.048.576 / 1.048.576** |
| `surrogate_validation_status` | *(không tồn tại)* | `PASS` |
| `fallback_reason` | có, nhưng bị `PASS` che | có, và gate phản ánh đúng |

## D.4 Nguyên tắc đã giữ trong toàn bộ đợt sửa

- **Không đổi tham số tài chính.** `target_cash_increment`, `financial_objective.*.weight/scale`, `transaction_cost`, `maximum_reduction`, ngưỡng gate — giữ nguyên. Thuộc quyền Phúc/Ngọc theo CLAUDE.md và plan CR-WF2-002. Đổi số để nghiệm hết degenerate chính là loại rủi ro review này tố cáo.
- **Không ghi đè artifact.** `artifacts/dev/`, `artifacts/runs/`, `artifacts_bench/` giữ nguyên. Mọi số trong Phụ lục C còn tái tạo được.
- **Không commit, không push.** Toàn bộ thay đổi ở working tree.
- **Ngưỡng mới đều đọc từ config**, vắng thì báo `NOT_CONFIGURED_PENDING_OWNER` thay vì đoán một con số.

---

# Phụ lục E — Đính chính review gốc bằng dữ liệu thực nghiệm mới (2026-09-04)

Sau khi triển khai công cụ đo (P0-1) và cổng chặn surrogate (P0-2), hai kết luận trong review gốc phải sửa lại. Ghi ở đây thay vì sửa ngầm phần trên, để giữ được dấu vết đã kết luận gì và vì sao đổi.

## E.1 ĐÍNH CHÍNH — `cash_budget_deviation` KHÔNG phải nguyên nhân duy nhất của all-ones

**Review gốc (§6.2, P0-1) nói:** target cash `0.1` đúng bằng trần vật lý nên chỉ tồn tại một nghiệm đưa deviation về 0, và đó là lý do nghiệm luôn là all-ones.

**Điều đó đúng nhưng KHÔNG đủ.** Ablation thật (`artifacts/dev/risk/objective_diagnostics.json`, sinh bởi `qshield-risk objective-diagnostics`):

| Thành phần bị tắt | Objective | Tổng bán | Vẫn là max-sell? |
|---|---|---|---|
| *(không tắt gì)* | 0.64739 | 300% | **có** |
| `cvar` | 0.03338 | 300% | **có** |
| `return_sacrifice` | 0.64739 | 300% | **có** |
| `transaction_cost` | 0.64114 | 300% | **có** |
| `turnover` | 0.62239 | 300% | **có** |
| `liquidity_penalty` | 0.64614 | 300% | **có** |
| **`cash_budget_deviation`** | 0.64651 | **300%** | **vẫn có** |

Tắt hẳn thành phần cash mà nghiệm **vẫn** là bán 30% mọi mã. Nghĩa là có **hai lực độc lập** cùng đẩy về biên:

1. **Cash target = trần vật lý** (đã nêu trong review gốc). Sweep xác nhận cơ chế này có thật và điều khiển được:

   | target | tổng bán | max-sell? |
   |---|---|---|
   | 0.02 | 60% | không |
   | 0.04 | 120% | không |
   | 0.06 | 180% | không |
   | 0.08 | 240% | không |
   | 0.10 (= trần) | 300% | **có** |

2. **Scenario cube có kỳ vọng lợi nhuận âm** — lực này review gốc chỉ ghi nhận như "một dấu hiệu bất thường cần điều tra riêng" (§6.3), thực ra nó là nguyên nhân ngang hàng. Cờ `SELLING_INCREASES_EXPECTED_RETURN` bật: bán cổ phiếu sang tiền mặt yield 0% mà kỳ vọng lợi nhuận **tăng**. Khi bán vừa giảm rủi ro vừa tăng lợi nhuận kỳ vọng thì **không tồn tại đánh đổi nào**, và CVaR một mình đã đủ đẩy nghiệm ra biên.

**Hệ quả cho roadmap:** sửa `target_cash_increment` là **cần nhưng chưa đủ**. Nếu chỉ hạ target mà không sửa cube, all-ones sẽ quay lại ngay khi cash band đủ rộng. Gốc rễ thứ hai nằm ở **scenario generation** (`packages/ai`), không ở objective — cùng chỗ với vấn đề stress pool rỗng và 5000 kịch bản từ 71 block. Đây là lý do phải ưu tiên nhánh AI trước nhánh Risk khi chốt tham số.

## E.2 ĐÍNH CHÍNH — Surrogate KHÔNG phải điểm yếu; nó tốt đến mức đáng lo

Review gốc xếp P0-2 là rủi ro correctness: "không ai biết sai số của surrogate; toàn bộ chuỗi exact→QAOA→rerank đang giải một mô hình chưa được kiểm định."

Cổng chặn đã triển khai và chạy trên dữ liệu thật (`qshield-quantum workflow` → `surrogate_validation.json`):

| Split | n | MAE | RMSE | Spearman ρ | top-20 recall |
|---|---|---|---|---|---|
| train | 711 | 0.00009 | 0.00011 | 1.0000 | 1.000 |
| validation | 500 | 0.00016 | 0.00022 | 1.0000 | 1.000 |
| **holdout** | **1000** | **0.00017** | **0.00022** | **1.0000** | **1.000** |

Ngưỡng: `mae_max 0.02`, `rmse_max 0.03`, `spearman_min 0.7`, `top_k_recall_min 0.6` → **PASS toàn bộ**, MAE tốt hơn ngưỡng ~118 lần, Spearman hoàn hảo trên holdout 1000 mẫu chưa từng dùng để fit.

**Surrogate được minh oan — nhưng kết quả này lại củng cố P0-1 mạnh hơn.** Một mô hình bậc 2 tái tạo hàm mục tiêu thật với ρ = 1.0000 chỉ có thể xảy ra khi hàm mục tiêu vốn đã gần bậc 2 — và ở đây nó còn gần tuyến tính (`corr(objective, tổng bán) = −0.999052`, đo lại độc lập bởi công cụ chẩn đoán, khớp con số −0,9993 của review gốc). Nói cách khác: **surrogate hoàn hảo vì bài toán quá dễ, không phải vì mô hình hoá giỏi.**

Điều này đóng lại một khả năng biện hộ: không thể nói "QAOA thua vì surrogate kém". Surrogate đúng; bài toán không có gì để giải.

## E.3 PHÁT HIỆN MỚI — Candidate gate PASS được ở N=15, và điều đó tạo ra vấn đề quantum

Sau P1-5, stability lần đầu tiên có số thật (trước đây toàn `null` vì `stability_rankings_path: null`):

- `median_overlap = 1.0`, `worst_overlap = 0.9`, `median_spearman = 0.9898` trên 5 seed bootstrap
- Lý do `STABILITY_NOT_EVALUATED` đã biến mất
- **Ranking ứng viên rất ổn định** — đây là tin tốt cho `packages/risk`

Dynamic N theo CR-WF2-005 chạy đúng như thiết kế:

| N | status | coverage | worst_overlap |
|---|---|---|---|
| 10 | FAIL | 0.5990 | 0.900 |
| 12 | FAIL | 0.6751 | 0.917 |
| **15** | **PASS** | **0.7829** | **0.933** |

Coverage là thứ fail, stability thì luôn đạt. **N=15 là N nhỏ nhất qua được gate** — đúng con số plan.md D6/CR-WF2-005 dự đoán.

**Nhưng đây là một đánh đổi kiến trúc, không phải chiến thắng.** N=15 nghĩa là 30 decision bit:

| | N=10 (hiện tại) | N=15 (để gate PASS) |
|---|---|---|
| decision bits | 20 | **30** |
| không gian exact | 1.048.576 | **1.073.741.824** |
| exact runtime đo được | 38 giây | ~10 giờ (ngoại suy tuyến tính) |
| statevector QAOA (complex128) | ~16 MB | **~16 GiB** |

Đúng cảnh báo plan.md R09 và §4.5. Nghĩa là: **qua được candidate gate sẽ làm mất exact ground truth và làm QAOA statevector không chạy nổi trên laptop.** Không thể có cả hai cùng lúc với kiến trúc hiện tại.

Ba lựa chọn, đều cần owner quyết, không lựa chọn nào là kỹ thuật thuần tuý:
1. Giữ N=10, chấp nhận candidate gate FAIL, và **không** gọi run là baseline (trạng thái hiện tại).
2. Lên N=15, mất exact ground truth ở quy mô đầy đủ — phải đổi cách chấm QAOA (branch-and-bound, hoặc exact trên tập con).
3. Sửa coverage ở gốc: coverage@10 thấp vì danh mục equal-weight 1/30 làm marginal benefit dàn đều. Danh mục thật có phân bố lệch sẽ cho coverage@10 cao hơn nhiều — đây là hướng rẻ nhất và cũng đúng với persona sản phẩm (nhà đầu tư cá nhân có danh mục thật, không phải equal-weight).

**Khuyến nghị: hướng 3 trước.** Nó vừa sửa coverage vừa có khả năng phá luôn tính degenerate ở E.1, vì danh mục lệch làm trần cash khác 0.10 và làm marginal benefit giữa các mã khác nhau thật sự.

---

# Phụ lục F — Bug im lặng trong fast path QAOA và thí nghiệm scaling (2026-09-04)

## F.1 `_qaoa_worker.py` treo lúc thoát, biến fast path thành đường đắt nhất

**Triệu chứng.** Đo scaling sau khi nối `solve_qaoa_one_seed_fast` vào workflow (P1-1), n=8 cho `runtime=600.2s` — đúng bằng `3 × 200s` timeout của subprocess.

**Chẩn đoán.** Probe trực tiếp: chạy worker thủ công và theo dõi `output.pkl`.

```
OUTPUT.PKL XUAT HIEN sau 2.0s (size=427)
→ tiến trình KHÔNG BAO GIỜ thoát
```

Worker tính xong và ghi kết quả hợp lệ sau **2 giây**, rồi treo vô hạn trong `Py_FinalizeEx`.

**Nguyên nhân.** Chính bẫy mà repo đã ghi lại ở `cli.py:59-66`: Rust `drop_glue` của `qiskit_circuit::CircuitData` (qiskit 2.5.1) có thể không bao giờ trả về khi interpreter finalize. `cli.py` đã xử lý bằng `_fast_exit_if_standalone()` → `os._exit(0)`. Nhưng `_qaoa_worker.py` thoát bằng `sys.exit(main(...))` — chạy đủ finalization.

Chuỗi hệ quả:
1. Worker ghi `output.pkl` sau 2s, rồi treo.
2. `subprocess.run(timeout=200)` bên `solve_qaoa_one_seed_fast` chờ hết 200s → `TimeoutExpired`.
3. Parent coi đó là crash (đúng theo thiết kế chống bug flaky của qiskit) → **retry**.
4. Lặp 3 lần = 600s, rồi rơi về đường chậm trong tiến trình.

Nghĩa là fast path không những không nhanh hơn, mà **đắt hơn đường thường ~430 lần** — và đắt một cách im lặng, vì kết quả cuối vẫn đúng.

**Sửa.** `os._exit(_exit_code)` sau khi `output.pkl` đã ghi xong. An toàn vì không còn buffer nào cần dọn.

| | Trước | Sau |
|---|---|---|
| n=8, một seed | **600,2s** | **1,4s** |

Test hồi quy `test_worker_module_exits_without_interpreter_finalization` đã kiểm chứng hai chiều: đổi lại `sys.exit` thì fail, giữ `os._exit` thì pass. Test soi code sau khi lọc bỏ dòng comment — bản đầu tiên tui viết bắt nhầm chính chuỗi `sys.exit()` nằm trong comment giải thích bug.

## F.2 Thí nghiệm scaling có kiểm soát (E5 trong §8)

Cùng instance sinh theo seed cố định, cùng settings (`shots=128, maxiter=10, reps=1, warm_start=False`), đo trên một máy. Đây là "thí nghiệm scaling có kiểm soát" mà plan.md R08 yêu cầu — khác hẳn việc so hai batch settings lệch nhau.

| n | states | QAOA (s) | Exact (s) | gap vs exact | peak RSS con (GiB) |
|---|---|---|---|---|---|
| 8 | 256 | 1,3 | 0,0 | 0,0000 | 0,20 |
| 10 | 1.024 | 1,4 | 0,0 | 0,0139 | 0,21 |
| 12 | 4.096 | 1,7 | 0,0 | 0,0445 | 0,23 |
| 14 | 16.384 | 2,3 | 0,1 | 0,1514 | 0,36 |
| 16 | 65.536 | 6,0 | 0,2 | 0,2001 | 1,01 |
| 18 | 262.144 | 22,7 | 1,0 | −0,0000 | 4,18 |
| **20** | **1.048.576** | **183,6** | **4,5** | **0,0609** | **9,11** |

**Đọc bảng này cẩn thận:**

1. **QAOA giờ chạy được tới 18 qubit** — trước khi sửa F.1 thì ngay n=8 đã mất 10 phút. Đây là điều kiện cần để bàn về quantum ở quy mô sản phẩm.
2. **Exact nhanh hơn QAOA ở MỌI kích thước đo được** — 4,5s vs 183,6s tại n=20, chênh ~41 lần. Khoảng cách **nới rộng** theo n (23× tại n=18 → 41× tại n=20), không hề thu hẹp. Không có dấu hiệu điểm giao (crossover) nào trong dải đo được.
3. **Gap không đơn điệu** (0,0000 → 0,0139 → 0,0445 → 0,1514 → 0,2001 → −0,0000). Mỗi n là một instance ngẫu nhiên KHÁC nhau, nên các gap **không so được với nhau**. Riêng n=18 tình cờ dễ. Muốn kết luận về xu hướng gap theo n phải cố định instance family và chạy nhiều seed — chưa làm.
4. **Bộ nhớ tăng nhanh hơn nhiều so với statevector lý thuyết.** Statevector 18 qubit chỉ cần 2¹⁸ × 16 byte ≈ 4 MB, nhưng đo được **4,18 GiB**. Nghĩa là bộ nhớ bị chi phối bởi **biểu diễn mạch đã transpile**, không phải statevector: QUBO dày có O(n²) số hạng bậc hai ⇒ O(n²) cổng hai qubit. Đo thật tại n=20: **9,11 GiB**. Ngoại suy n=30 (N=15 candidates) vượt xa mọi laptop.

Điểm 4 sửa lại một giả định trong review gốc §8 (E5): tui ước lượng giới hạn theo statevector complex128 (30 bit = 16 GiB). Thực tế **giới hạn tới sớm hơn nhiều** vì chi phí mạch, không phải chi phí statevector. Trần thực dụng nằm quanh n=18–20 trên máy 16 GB, không phải n=30.

**Hệ quả cho P1-2 và cho roadmap quantum:** xem F.3.

## F.3 Rủi ro tồn dư: đường fallback KHÔNG còn là fallback thật ở n lớn

`solve_qaoa_one_seed_fast` được thiết kế ba tầng: (1) subprocess có transpile cưỡng bức, (2) retry trong subprocess mới nếu crash, (3) hết lượt thì rơi về `solve_qaoa_one_seed` chạy thẳng trong tiến trình — "chậm nhưng LUÔN đúng" theo docstring `qaoa.py:216-217`.

Tầng (3) đúng ở n≤8, nhưng **không còn đúng ở n=20**: `_make_transpiler` (`qaoa.py:52-59`) trả `None` khi `num_qubits > _TRANSPILE_SAFE_MAX_QUBITS = 8`, nên đường in-process rơi vào `PauliEvolutionGate.to_matrix()` với `scipy.sparse.linalg.expm` trên ma trận 2²⁰×2²⁰ — thực tế là treo, không phải "chậm".

Nghĩa là ở quy mô sản phẩm, chuỗi thực tế khi subprocess crash là: retry → retry → **treo vô hạn**, chứ không phải "trả kết quả chậm". Trước khi sửa F.1 điều này bị che vì mọi lần chạy đều đi qua đường timeout; sau khi sửa thì subprocess gần như luôn thành công nên tầng (3) hiếm khi chạm tới — nhưng rủi ro vẫn còn nguyên nếu bug flaky của qiskit tái xuất hiện.

**Đề xuất (chưa làm, cần quyết định):** ở `num_qubits > _TRANSPILE_SAFE_MAX_QUBITS`, tầng (3) nên **raise có ngữ cảnh** thay vì im lặng đi vào đường treo — để `workflow.py` ghi `fallback_reason` trung thực và hạ `gate_status`, đúng tinh thần P0-4b. Một treo vô hạn không có thông báo là dạng lỗi tệ nhất trong cả chuỗi này.

**Ngưỡng `_TRANSPILE_SAFE_MAX_QUBITS = 8` bản thân nó vẫn đúng và không cần đổi** — nó chỉ chi phối đường in-process; worker cố ý cưỡng bức transpile bất kể ngưỡng, vì subprocess CHÍNH LÀ cơ chế an toàn.

## F.4 P1-2 (`dev_mode.enabled: false`) — quyết định: **CHƯA FLIP**, kèm số liệu

Chi phí QAOA tại n=20 (shots=128) đo trên hai điểm:

| maxiter | runtime |
|---|---|
| 10 | 175,0s |
| 30 | 533,9s |

Quan hệ tuyến tính sạch: **17,9 giây mỗi vòng lặp COBYLA**, chi phí cố định ≈ 0.

Ngoại suy sang cấu hình baseline đang khai trong `configs/workflow_update.yaml` (`optimizer_maxiter: 200`, `min_seeds: 10`):

| Hạng mục | Ngoại suy | Ngân sách trong config | Kết quả |
|---|---|---|---|
| 1 seed | ~3.590s (60 phút) | `qaoa_seed_timeout_seconds: 600` | **vượt 6,0×** |
| 10 seed | ~35.890s (10,0 giờ) | `qaoa_total_timeout_seconds: 7200` | **vượt 5,0×** |
| maxiter vừa ngân sách 600s/seed | **33** | khai báo 200 | — |

Nếu flip `dev_mode.enabled: false` ngay bây giờ, chuỗi sự kiện thực tế sẽ là: mỗi seed chạy subprocess 600s → timeout → retry → retry (3 × 600s = 1.800s) → cạn lượt → **trước F.3 thì treo vô hạn**. Nghĩa là flip không chỉ chậm, mà làm pipeline đứng hẳn mà không ghi artifact nào.

Vì vậy F.3 đã được sửa trong cùng đợt này (`TranspileFallbackUnavailableError` + `workflow.py` bắt lỗi → `fallback_reason` → `gate_status=FALLBACK`). Sau khi sửa, kịch bản xấu nhất là "mất 1.800s rồi báo lỗi trung thực", không còn là "treo im lặng".

**Ba phương án, đều cần owner quyết — không phải quyết định kỹ thuật thuần tuý:**

| | Phương án | Đánh đổi |
|---|---|---|
| A | Giữ `dev_mode` (1 seed / 128 shots / maxiter 10) | Chạy 183s, nhưng **không đủ tư cách thống kê**: 1 seed vi phạm quy tắc "tối thiểu 10 seed, không cherry-pick" (CLAUDE.md 18) |
| B | Hạ `optimizer_maxiter` 200 → 30 | Vừa ngân sách 600s/seed; 10 seed ≈ 89 phút, vừa `qaoa_total_timeout_seconds: 7200`. **Nhưng maxiter=30 có đủ để COBYLA hội tụ ở 20 tham số hay không thì chưa đo** |
| C | Nâng `qaoa_seed_timeout_seconds` lên ~3.600s và `qaoa_total` lên ~36.000s | Giữ maxiter=200 nhưng mỗi lần chạy baseline mất 10 giờ |

**Khuyến nghị: B, nhưng phải đo trước khi chốt.** Cần một thí nghiệm hội tụ: cố định instance, chạy maxiter ∈ {10, 30, 50, 100, 200} × nhiều seed, xem gap so exact bão hoà từ đâu. Nếu gap bão hoà ở maxiter ≈ 30 thì B là lựa chọn đúng và rẻ. Nếu không, phải chọn C và chấp nhận baseline 10 giờ.

Thí nghiệm đó **chưa chạy** — nên `dev_mode` giữ nguyên `true`, và `gate_status` vẫn phản ánh trung thực rằng run không đủ tư cách final (`NON_FINAL` do seed < `minimum_seeds`).

## F.5 ĐÍNH CHÍNH NẶNG — kết quả QAOA KHÔNG tái lập được dù cùng seed (đã sửa)

Review gốc §3.13 kết luận: *"Hai run độc lập cho cùng `qubo_hash` ⇒ reproducibility đã được chứng minh bằng thực nghiệm. Đây là điểm rất tốt."*

**Câu đó đúng về MODEL và sai về SOLVER.** `qubo_hash` ổn định thật, nhưng tui đã không kiểm tra rằng chạy lại cùng seed có ra cùng nghiệm hay không. Nó không.

**Phát hiện.** Ba lần đo n=20 cho gap khác nhau (+0,0609 rồi +0,0000) dù cùng instance, cùng `seed=101`, cùng shots/maxiter. Test trực tiếp ba lần trong CÙNG một tiến trình:

```
lần 1: 00111011  energy=-0.15286668
lần 2: 00111111  energy=-0.18319979
lần 3: 00111111  energy=-0.18319979
```

**Nguyên nhân.** `seed` chỉ được truyền cho `make_sampler(shots=shots, seed=seed)` — nó seed việc **lấy mẫu**. Nhưng `QAOA(initial_point=None)` bốc điểm khởi tạo tham số qua `validate_initial_point` → `algorithm_globals.random.uniform(bounds)`, một **RNG toàn cục không liên quan gì tới `seed` của ta** (`qiskit_algorithms/utils/validate_initial_point.py:43-56`).

**Mức độ nghiêm trọng.** Mọi con số solver trong `workflow_benchmark.json` — `winning_bitstring`, `optimality_gap`, `success_prob`, `energy_stats`, `qaoa_beats_classical` — **không tái tạo được**, dù artifact mang đủ `registered_seeds`, `qubo_hash` và `candidate_order_hash`. Trực tiếp phá yêu cầu plan.md G3 (*"Ngọc ký final trên run/config hash cụ thể"*): ký vào một hash không dựng lại được con số.

Nó cũng làm hỏng ngầm quy tắc CLAUDE.md 18 theo hướng ngược lại: "chạy đủ 10 seed, không cherry-pick" giả định mỗi seed là một điểm xuất phát xác định. Khi initial point ngẫu nhiên không kiểm soát, 10 seed không phải 10 cấu hình đăng ký trước mà là 10 lần bốc thăm.

**Sửa.** `algorithm_globals.random_seed = seed` trong `solve_qaoa_one_seed`, ngay trước khi dựng sampler. Chọn cách này thay vì tự truyền `initial_point` để **giữ nguyên phân phối và logic bounds của qiskit** (lấy từ circuit nếu có, else `[-2π, 2π]`) — chỉ làm nó tất định, không đổi hành vi tìm kiếm.

| | Trước | Sau |
|---|---|---|
| 3 lần cùng seed=101 | 2 kết quả khác nhau | **3/3 giống hệt** |
| seed khác nhau | — | vẫn cho kết quả khác (seed còn tác dụng) |

Test hồi quy `test_same_seed_reproduces_the_same_qaoa_result` khoá cả hai chiều: cùng seed phải giống, và seed khác vẫn phải tái lập được riêng nó (chống việc khoá cứng một `initial_point` làm mọi seed như nhau).

**Cảnh báo về dữ liệu cũ:** mọi artifact QAOA sinh TRƯỚC bản sửa này (`artifacts_bench/warm_start_run`, `no_warm_start_run`, `stress_run`, `narrative_run`) đều mang con số không tái lập được. Chúng vẫn dùng được làm ghi chép lịch sử, nhưng **không được dùng làm bằng chứng cho bất kỳ so sánh solver nào**, và phải chạy lại sau khi có bản sửa nếu muốn đưa vào báo cáo.

---

# Phụ lục G — Nguyên nhân gốc của degeneracy: danh mục thử nghiệm, KHÔNG phải tham số objective

Thí nghiệm này trả lời câu hỏi mở lớn nhất của review mà **không đổi một tham số tài chính nào** — nên nó hợp lệ theo plan.md §7 (*"chạy nghiên cứu có nhãn rõ"*) và không vi phạm A5 (*"gói nháp không kích hoạt runtime"*).

## G.1 Thiết kế

Giữ nguyên toàn bộ config, scenario cube và code. Chỉ đổi **hình dạng danh mục** đầu vào, rồi chạy lại candidate selection + candidate gate + đo hình dạng objective trên thiết kế structured 211 mẫu.

Bốn dạng: `equal_weight` (đang dùng), `zipf 1/rank`, `concentrated top5=60%`, `realistic 12 holdings`. Ba dạng sau là **giả định do reviewer dựng**, không phải danh mục nhà đầu tư thật.

## G.2 Kết quả

| Danh mục | Trần cash | corr(obj, tổng bán) | all-ones tối ưu? | coverage@10 |
|---|---|---|---|---|
| **equal_weight (hiện tại)** | **0,1000** = đúng target | **−0,9817** | **Có** | **0,5990** ❌ |
| zipf 1/rank | 0,2152 | −0,4526 | Không | 0,8463 ✅ |
| concentrated top5=60% | 0,2040 | −0,4582 | Không | 0,8393 ✅ |
| realistic 12 holdings | 0,2700 | −0,7253 | Không | 0,9712 ✅ |

**Degeneracy biến mất ở cả ba dạng lệch. Coverage@10 vượt ngưỡng 0,70 ở cả ba.**

Nghiệm tối ưu trên `realistic 12 holdings` là **nghiệm trong lòng miền thật sự**:

```
mức bán = [30, 30, 30, 10, 0, 0, 0, 0, 0, 0] %
```

Bán 4 trong 10 mã, ở ba mức khác nhau — không phải góc, không phải no-action. Đây là dạng nghiệm mà một bài toán tổ hợp phải có.

Ablation giờ mới có sức phân biệt:

| Tắt thành phần | Nghiệm | Đọc |
|---|---|---|
| *(không tắt)* | `[30,30,30,10,0,…]` | nghiệm cơ sở |
| `cvar` | `[30,0,10,20,0,20,0,10,20,10]` | **hoàn toàn khác** ⇒ CVaR thật sự điều khiển nghiệm |
| `cash_budget_deviation` | tổng bán 270% (gần trần) | cash term là thứ **kìm** việc bán, không phải thứ ép bán |
| 4 thành phần còn lại | không đổi | biên độ quá nhỏ, đúng như đo ở E.2 |

Sweep target cash cũng trở nên đơn điệu và luôn nội tại: 0,02→20%, 0,04→40%, 0,06→50%, 0,08→70%, 0,10→100%; **không mức nào chạm max-sell**.

Cờ `SELLING_INCREASES_EXPECTED_RETURN` **tắt** (chỉ 1/10 candidate có kỳ vọng âm, thay vì đủ để lật dấu toàn danh mục).

## G.3 Nguyên nhân gốc

`configs/base.yaml:337-368` khai `sample_portfolio_weights` = **equal-weight 1/30 cho cả 30 mã**, cash 0. Từ đó:

1. Tổng weight của top-10 candidate = 10 × 0,0333 = 0,3333.
2. Trần cash = 0,3333 × 0,30 = **0,10000**, đúng bằng `target_cash_increment: 0.1`.
3. Chỉ tồn tại **một** nghiệm đưa `cash_budget_deviation` về 0 ⇒ all-ones.
4. Marginal benefit dàn đều giữa 30 mã giống hệt nhau ⇒ top-10 chỉ giữ được 59,9% tổng lợi ích ⇒ coverage fail.

Cả hai triệu chứng P0 đến từ **một fixture thử nghiệm**, không từ tham số tài chính.

## G.4 Đính chính các kết luận trước

| Kết luận cũ | Trạng thái |
|---|---|
| **P0-1** (§5, E.1): all-ones do `target_cash_increment` + cube kỳ vọng âm; cần Phúc/Ngọc đổi tham số | **Sai trọng tâm.** Cả hai lực đó có thật nhưng chỉ trở nên chi phối vì danh mục equal-weight. Đổi fixture là đủ; **không cần đổi tham số nào** |
| **E.3**: candidate gate chỉ PASS ở N=15 ⇒ 30 bit ⇒ mất exact ground truth | **Sai.** N=15 là hệ quả của coverage thấp do equal-weight. Với danh mục lệch, **N=10 PASS** ⇒ giữ nguyên 20 bit, giữ nguyên exact 2²⁰ |
| §6.5 Test 4 (*"chạy trên ≥10 danh mục khác nhau; nếu all-ones luôn đứng #1 ⇒ degenerate"*) | **Đã chạy, và cho kết quả ngược lại điều tui lo:** all-ones chỉ thắng ở đúng danh mục equal-weight |

## G.5 Việc còn lại — và nó KHÔNG còn là quyết định tham số

`sample_portfolio_weights` là **fixture thử nghiệm**, không phải tham số tài chính như `target_cash_increment` hay `financial_objective.*.weight`. Thay nó không phải "đổi số cho ra kết quả đẹp" mà là **sửa một thiết lập thử nghiệm không đại diện**: plan.md A1 định nghĩa persona là *"nhà đầu tư cá nhân có danh mục cổ phiếu hiện hữu"* — không ai nắm equal-weight cả 30 mã VN30.

Nhưng nó vẫn nằm trong `configs/` nên vẫn cần Ngọc duyệt, và **quan trọng hơn**: plan.md §7 ghi *"chưa có investor portfolio thật"*. Con số đúng phải đến từ một danh mục thật có consent (plan G2), không phải từ một dạng lệch do reviewer bịa ra.

**Đề xuất:** giữ `equal_weight` làm một trong các fixture hồi quy (nó bộc lộ đúng trường hợp biên), nhưng **evidence run phải chạy trên danh mục có phân bố thật**. Ba dạng ở G.2 dùng được làm bộ test tạm trong lúc chờ danh mục thật.

## G.6 Điều KHÔNG đổi

Thí nghiệm này **không** đụng tới kết luận quantum. Exact vẫn nhanh hơn QAOA 41 lần ở n=20 và khoảng cách vẫn nới rộng theo n. Bài toán hết degenerate nghĩa là **giờ mới đáng để đo nhánh quantum** — thí nghiệm E4 (ablation classical-only vs classical+QAOA) trước đây vô nghĩa thì bây giờ mới có ý nghĩa. Đó là việc tiếp theo, chưa làm.

---

# Phụ lục H — Phát hiện quyết định: surrogate là nút thắt, không phải solver

Đây là kết quả quan trọng nhất của toàn bộ đợt review. Nó chỉ lộ ra sau khi (a) sửa fixture danh mục ở Phụ lục G, và (b) cổng chặn P0-2 được triển khai.

## H.1 Cổng chặn surrogate FAIL trên danh mục thực tế

Cùng config, cùng cube, cùng thiết kế lấy mẫu thật của pipeline (`sample_objective_dataset`: train 711 = 211 structured + 500 random stratified; validation 500; holdout 1000). Chỉ đổi danh mục từ equal-weight sang `realistic 12 holdings`:

| Split | n | MAE | RMSE | Spearman | top-20 recall |
|---|---|---|---|---|---|
| train | 711 | 0,01571 | 0,02090 | 0,9874 | 0,500 |
| validation | 500 | **0,03004** | **0,03866** | 0,8939 | **0,250** |
| holdout | 1000 | **0,03086** | **0,03900** | 0,8887 | **0,250** |

**STATUS: FAIL** — 6 vi phạm ngưỡng trên cả validation lẫn holdout (`mae_max 0.02`, `rmse_max 0.03`, `top_k_recall_min 0.6`).

Đối chiếu với equal-weight (E.2): Spearman **1,0000**, recall **1,000**, PASS toàn bộ. Cùng một code, cùng ngưỡng — chỉ đổi hình dạng danh mục.

**Kết luận: cổng chặn P0-2 hoạt động đúng.** Nó im lặng khi bài toán tầm thường và bắt được khi bài toán thật. Nếu không có cổng này, pipeline sẽ chạy tiếp và không ai biết.

`top-20 recall = 0,25` là con số đáng lo nhất: surrogate chỉ giữ được **5 trong 20** nghiệm tốt nhất thật sự. Vì solver chỉ trả về một pool ứng viên rồi Risk rerank lại, việc đánh rơi 15/20 nghiệm tốt nghĩa là rerank không còn gì tốt để chọn.

## H.2 So sánh cuối cùng — trên cùng một true financial objective

| Phương án | true objective | chi phí |
|---|---|---|
| no-action | 1,293691 | 0 |
| all-ones (bán 30% mọi mã) | 1,357435 | — |
| **exact 2²⁰ trên surrogate (TOÀN BỘ pipeline QUBO)** | **0,938997** | 16s lấy mẫu + 4,6s exact ≈ **21s** |
| **coordinate descent trực tiếp trên true objective** | **0,835184** | **7,3s** (16 restart) |

Nghiệm classical trực tiếp: `[30, 30, 30, 10, 0, 0, 0, 0, 0, 0]%`.

**Tối ưu cổ điển trực tiếp trên hàm mục tiêu thật vừa NHANH HƠN ~3 lần, vừa TỐT HƠN ~11%** so với toàn bộ chuỗi surrogate → QUBO → exact.

## H.3 Vì sao điều này quan trọng hơn mọi phát hiện trước

Lý do tồn tại của surrogate là "true objective quá đắt để tối ưu trực tiếp". Đo thật: **một lần đánh giá true objective mất 7,2 ms**. Ở quy mô này, tiền đề đó **không đúng**.

Hệ quả cho nhánh quantum, và nó nghiêm trọng:

1. **Trần chất lượng của cả nhánh QUBO bị đặt bởi surrogate, không phải bởi solver.** Exact duyệt đủ 2²⁰ đã tìm ĐÚNG cực tiểu của surrogate — và cực tiểu đó vẫn kém nghiệm thật 11%.
2. **Cải thiện solver không thể vá được điều này.** QAOA dù hoàn hảo cũng chỉ tìm lại đúng nghiệm 0,938997 mà exact đã tìm. Một solver hoàn hảo vẫn thua coordinate descent cổ điển.
3. Nói cách khác: **QAOA đang cạnh tranh để giải tối ưu một mô hình vốn đã sai 11%.** Mọi thí nghiệm so sánh solver (E4) đều bị chặn trên bởi con số này.

Điều này KHÔNG nói QAOA tệ. Nó nói **nền móng mà nhánh quantum đứng lên đang yếu**, và phải sửa nền trước khi đo gì trên đó.

## H.4 Đính chính E.2

E.2 kết luận: *"Surrogate được minh oan — nhưng kết quả này lại củng cố P0-1... surrogate hoàn hảo vì bài toán quá dễ."*

Nửa sau đúng, nửa đầu **sai**. Surrogate không được minh oan — nó chỉ chưa bị thử thách. Ngay khi danh mục thực tế làm hàm mục tiêu phi tuyến thật, surrogate hỏng và cổng chặn bắt được.

## H.5 Việc cần làm — theo thứ tự

1. **Chạy lại H.1 trên nhiều danh mục** (≥5 dạng, gồm cả danh mục thật khi có consent theo plan G2). Một danh mục tổng hợp chưa đủ để kết luận chung.
2. **Nếu FAIL lặp lại:** ba hướng, cần Phúc + Tân quyết:
   - Tăng số mẫu (plan D8: *"sample count scale theo số hệ số"*) — nhưng bậc 2 vẫn là bậc 2, có thể không đủ.
   - Đổi lớp mô hình (bậc cao hơn, hoặc thêm số hạng ba biến) — phá vỡ dạng QUBO thuần, **ảnh hưởng trực tiếp tới khả năng chạy quantum**.
   - Bỏ surrogate ở quy mô này, tối ưu trực tiếp true objective bằng classical; giữ QUBO/QAOA làm **nhánh nghiên cứu có nhãn rõ** cho quy mô lớn hơn nơi 7,2ms/lần đánh giá trở thành rào cản thật.
3. **Thí nghiệm E4 (classical-only vs classical+QAOA) tạm hoãn.** Chạy nó bây giờ chỉ đo được hai solver cùng giải một mô hình sai 11% — con số thu được không trả lời câu hỏi plan E4 đặt ra.

## H.6 Giới hạn của chính phát hiện này

- Một danh mục tổng hợp, do reviewer dựng, chưa phải danh mục thật.
- Coordinate descent trên true objective **không đảm bảo tối ưu toàn cục** — nó chỉ tình cờ tốt hơn. Chưa có exact trên true objective để biết cả hai còn cách optimum bao xa (duyệt 4¹⁰ × 7,2ms ≈ 2,1 giờ — khả thi, nên chạy).
- Ngưỡng `mae_max: 0.02` / `top_k_recall_min: 0.6` đang mang trạng thái `PROVISIONAL_PENDING_OWNER`. FAIL đo được là FAIL **so với ngưỡng chưa ký**. Owner có thể nới ngưỡng — nhưng khi đó phải chấp nhận con số 11% ở H.2 một cách tường minh.

---

# Phụ lục I — Duyệt đủ trên hàm mục tiêu thật: khép lại con số

Chạy 2026-09-04, **2.004 giây** (33 phút) trên 8 tiến trình, duyệt đủ **1.048.576 tổ hợp** bằng chính hàm `financial_objective_from_growth` canonical — không viết lại công thức. Danh mục `realistic 12 holdings`, cùng candidate order với Phụ lục H.

## I.1 Optimum thật, và khoảng cách của từng phương án

| Phương án | true objective | lệch optimum | hạng trong 1.048.576 |
|---|---|---|---|
| **OPTIMUM THẬT** `11001111000101000000` | **0,821059** | 0,00% | **1** |
| coordinate descent (16 restart, 7,3s) | 0,835184 | **1,72%** | **525** (top 0,05%) |
| **exact 2²⁰ trên surrogate (pipeline QUBO)** | **0,938997** | **14,36%** | **307.751** (top 29,3%) |
| no-action | 1,293691 | 57,56% | 1.048.359 |
| all-ones | 1,357435 | 65,33% | **1.048.576 — tệ nhất tuyệt đối** |

Mức bán của optimum thật: `[30, 0, 30, 30, 0, 20, 20, 0, 0, 0]%` — bán 5 trong 10 mã ở hai mức khác nhau.

**Đính chính H.2:** tui báo cáo khoảng cách "11%" giữa pipeline QUBO và coordinate descent. Con số đúng so với **optimum thật** là **14,36%** cho pipeline QUBO và **1,72%** cho coordinate descent. Coordinate descent cũng KHÔNG tối ưu — nhưng nó nằm ở hạng 525/1.048.576, còn pipeline QUBO ở hạng 307.751.

Diễn đạt theo lợi ích thu được (từ no-action tới optimum là toàn bộ lợi ích khả dụng):

| Phương án | Thu được |
|---|---|
| coordinate descent | **97,0%** lợi ích khả dụng |
| pipeline QUBO | **75,0%** lợi ích khả dụng |

Hai điểm phụ đáng ghi nhận:
- **all-ones là nghiệm TỆ NHẤT trong toàn bộ 1.048.576 tổ hợp.** Việc equal-weight biến nó thành nghiệm tối ưu (Phụ lục G) vì thế còn nghiêm trọng hơn tưởng.
- **Tối ưu hoá thật sự có giá trị:** khoảng cách no-action → optimum là 57,6%. Bài toán đáng giải; vấn đề là đường QUBO chỉ thu được 3/4 lợi ích đó.

## I.2 Chất lượng surrogate đo trên TOÀN không gian, không phải mẫu

Có đủ 1.048.576 giá trị thật nên đo được chính xác thay vì ước lượng:

| Chỉ số | **Toàn không gian** | Holdout 1.000 mẫu (cổng chặn đang dùng) | Holdout lệch |
|---|---|---|---|
| Spearman ρ | 0,8334 | 0,8887 | **lạc quan +0,055** |
| **top-20 recall** | **0,000** | 0,250 | **lạc quan** |
| top-100 recall | **0,000** | — | — |
| top-1000 recall | 0,011 | — | — |
| MAE | 0,03400 | 0,03086 | lạc quan |
| RMSE | 0,04235 | 0,03900 | lạc quan |

**`top-20 recall = 0,000` và `top-100 recall = 0,000`.** Surrogate không giữ được **một nghiệm nào** trong 100 nghiệm tốt nhất thật sự. Bước rerank bằng true CVaR — vốn là lớp bảo vệ cuối theo CLAUDE.md quy tắc 17 — **không có gì tốt để chọn**, vì solver không bao giờ đưa nghiệm tốt vào pool.

Đối xứng: **optimum thật xếp hạng 133.367 theo surrogate.** Surrogate coi nghiệm tốt nhất là hạng trung bình.

## I.3 Hai kết luận phương pháp luận

**1. Holdout 1.000 mẫu ước lượng LẠC QUAN.** Mọi chỉ số đều tốt hơn sự thật, `top-20 recall` lệch từ 0,000 lên 0,250. Cổng chặn P0-2 **vẫn bắt được FAIL** — nhưng nó đang bảo vệ **yếu hơn** Phúc nghĩ. Đây là câu trả lời trực tiếp cho câu hỏi A2.

**2. Spearman là chỉ số SAI cho mục đích này.** ρ = 0,8334 nghe "khá tốt" và vượt ngưỡng `spearman_min: 0.7`. Nhưng tối ưu hoá chỉ quan tâm phần **đuôi trên**, và ở đó recall bằng **0,000**. Một surrogate có thể đạt Spearman cao trên toàn không gian trong khi hoàn toàn vô dụng để tìm nghiệm tốt.

**Khuyến nghị cho A2:** bỏ `spearman_min` khỏi vai trò tiêu chí quyết định (giữ để báo cáo), lấy `top_k_recall` làm tiêu chí chính, và tính nó trên tập mẫu lớn hơn nhiều hoặc trên toàn không gian khi khả thi.

## I.4 Ảnh hưởng tới câu A3

Câu hỏi *"surrogate bậc 2 có đủ không"* nay có câu trả lời định lượng: **không, ở danh mục thực tế**. Không phải "hơi lệch" mà là **giữ được 0 trong 100 nghiệm tốt nhất**.

Ba hướng ở A3 giờ có thể đánh giá:
- **(a) tăng số mẫu** — không giải quyết được. Vấn đề là lớp mô hình, không phải số mẫu: bậc 2 không biểu diễn nổi hàm CVaR ở vùng nhiều hành động.
- **(b) đổi lớp mô hình** — có thể, nhưng phá dạng QUBO thuần và **ảnh hưởng trực tiếp khả năng chạy quantum**.
- **(c) classical trực tiếp ở N=10** — thu được 97,0% lợi ích trong 7,3 giây, so với 75,0% trong 21 giây của đường QUBO.

## I.5 Giới hạn của chính Phụ lục I

- **Một danh mục tổng hợp**, do reviewer dựng. Cần lặp lại trên ≥5 danh mục, gồm danh mục thật có consent (plan G2), trước khi coi là kết luận chung.
- Kết quả này **không** nói QAOA tệ. Nó nói mọi solver trên đường QUBO — exact, classical local search, QAOA — đều bị chặn trên bởi cùng một surrogate. Exact đã tìm ĐÚNG cực tiểu của surrogate; đó là điều tốt nhất bất kỳ solver nào có thể làm trên mô hình đó.
- Coordinate descent trên true objective (hạng 525) cũng **không tối ưu**. Nếu chọn hướng (c) thì vẫn cần một thuật toán tốt hơn, hoặc chấp nhận 1,72%.

---

# Phụ lục J — Sổ tổng hợp: đã làm gì, số liệu nào

Các phụ lục D–I được ghi theo trình tự thời gian nên trạng thái nằm rải rác. Mục này gộp lại thành **một bảng kê duy nhất** — mọi việc đã làm, mọi con số đo được, và mọi chỗ tui đã tự đính chính.

**Chốt trạng thái:** 476 test pass + 8 chậm, 0 fail · `ruff` sạch · `mypy` không còn lỗi thuộc phần thêm mới · 0 commit, 0 push · **không tham số tài chính nào bị đổi**.

---

## J.1 Trạng thái kiểm thử

| Gói | Đầu phiên | Cuối phiên |
|---|---|---|
| contracts | 55 | **56** |
| data | 62 | **62** |
| ai | 169 pass / **3 fail** | **177** |
| risk | 70 | **88** |
| quantum | 40 | **59** |
| pipeline | 13 | **13** |
| backend | 4 | **21** |
| chậm (`slow`) | — | **8** |
| **Tổng** | **416 thu thập / 3 fail** | **476 + 8 / 0 fail** |

`ruff check packages backend tools` → sạch.
`mypy packages/*/src backend/src` → 83 → **81** lỗi; 2 lỗi do phần thêm mới đã sửa, 81 lỗi còn lại là thiếu stub có sẵn (pandas, supabase, qiskit).

---

## J.2 Mười ba mục P0/P1 đã xử lý, kèm số

| ID | Việc | Trước | Sau |
|---|---|---|---|
| **P0-1** | CLI `objective-diagnostics` — ablation, sweep, landscape, cờ sanity | không có | `corr = −0,999052`; thành phần chi phối `cash_budget_deviation`, biên độ **2,66×** CVaR |
| **P0-2** | Cổng chặn surrogate trên holdout | khoá config **không có code nào đọc** | equal-weight: ρ=1,0000 recall 1,000 **PASS**<br>danh mục lệch: ρ=0,8887 recall 0,250 **FAIL** (6 vi phạm) |
| **P0-3** | Xuất `quantum_constraints` thật từ `RiskPolicy` | `{}` — bài toán **không ràng buộc nào** | `policy_to_quantum_constraints()` + khối `constraints_encoding` nói rõ ràng buộc nào vào QUBO, ràng buộc nào ở ngoài |
| **P0-4a** | Cổng kịch bản khi thiếu regime | `PASS` + Stress rỗng | `INCOMPLETE` + nêu tên regime thiếu |
| **P0-4b** | `gate_status` hard-code trong quantum | hằng số `"PASS"` ở 2 chỗ | `_derive_gate_status()`; đo thật trên cùng lệnh: **`PASS` → `FALLBACK`** |
| **P0-4c** | Cổng rerank khi không có policy | `PASS` giả | `NOT_EVALUATED` |
| **P0-4d** | Chẩn đoán đa dạng khối bootstrap | không có | `unique_blocks_used: 71`, `reuse_rate: 0,99645`, `effective_independent_windows` |
| **P0-5** | Backend nhận danh mục nhưng không dùng | im lặng | `personalization_status` = `MATCHED_HANDOFF`/`NOT_APPLIED` + 2 sha256 đối chiếu |
| **P0-6** | UI dán nhãn "quantum" lên kết quả exact | cột `quantum_reduction` | banner cảnh báo + badge `source_solver` mỗi dòng |
| **P1-1** | QAOA 20-bit không chạy được | n=8: **600,2s**; n=20: bất khả thi | n=8: **1,4s** (nhanh **429×**); n=20: **183,6s** |
| **P1-3** | Classical benchmark khớp ngân sách | 64 restart cố định (~0,5s) vs QAOA 600s/seed | `budget_seconds` = đúng wall-time QAOA + `classical_search_stats` |
| **P1-4** | Verify chỉ chạy 0,39% không gian | **4.098** / 1.048.576 | **1.048.576** / 1.048.576 trong **2,69s** |
| **P1-5** | Stability chưa từng được đánh giá | mọi chỉ số `null` | trùng lặp **0,933**, Spearman **0,99**; dynamic N: 10 FAIL → 12 FAIL → **15 PASS** |
| **P1-7** | Codec 2-bit cài trùng ở 2 gói | không gì bắt nếu lệch | test duyệt đủ **4³ = 64** tổ hợp + đối chiếu bảng mapping profile |
| **P1-8** | `peak_memory_mb` và `reference_hardware` | cả hai **luôn `null`** | **291,5 MB**; `arm / 8 lõi / Darwin 25.6.0 / 32 GB` |
| **P1-10** | 3 test AI fail do config đã xoá | 3 fail | 0 fail, giữ nguyên mục đích test |

---

## J.3 Bảy lỗi im lặng — sáu cái KHÔNG có trong review gốc

| # | Lỗi | Cách phát hiện | Số đo |
|---|---|---|---|
| 1 | `gate_status` hard-code `"PASS"` | có trong review gốc (P0-4b) | `PASS` → `FALLBACK` |
| 2 | **`RunContext.logger()` mất `logs.txt`** khi hai run trùng `run_id` | một test AI đổi pass→fail | mất 1/4 tệp metadata bắt buộc |
| 3 | **Worker QAOA treo trong `Py_FinalizeEx`** | probe trực tiếp | ghi kết quả sau **2,0s** rồi treo ⇒ parent timeout ×3 = **600,2s** |
| 4 | **Fallback in-process treo vô hạn ở n>8** | truy vết sau lỗi #3 | `expm(2²⁰)` — treo, không phải "chậm" |
| 5 | **QAOA không tái lập dù cùng seed** | 3 phép đo n=20 cho gap khác nhau | 3 lần cùng `seed=101` → **2 kết quả**; sau sửa **3/3 giống hệt** |
| 6 | **Dynamic N đẩy quantum lên 30 bit mà không ai chặn** | do chính đợt sửa tạo ra | 2³⁰ = 1,07 tỷ trạng thái ≈ **78 phút** rồi hết RAM |
| 7 | **`selected_count` cũ sau dynamic N** | chạy `prepare-workflow` e2e lần đầu | `has 15 selected rows, expected 10` — unit test không bắt được |

Lỗi #2–#5 và #7 đều **im lặng**: hệ thống vẫn chạy, vẫn ghi artifact, vẫn báo thành công.

---

## J.4 Toàn bộ số liệu đo được

### Thí nghiệm quy mô có kiểm soát (plan R08)

Cùng cấu hình, cùng máy, mỗi n một instance sinh theo seed cố định · `shots=128, maxiter=10, reps=1, warm_start=False`

| n | states | QAOA | Exact | gap | peak RSS |
|---|---|---|---|---|---|
| 8 | 256 | 1,3s | 0,0s | 0,0000 | 0,20 GiB |
| 10 | 1.024 | 1,4s | 0,0s | 0,0139 | 0,21 GiB |
| 12 | 4.096 | 1,7s | 0,0s | 0,0445 | 0,23 GiB |
| 14 | 16.384 | 2,3s | 0,1s | 0,1514 | 0,36 GiB |
| 16 | 65.536 | 6,0s | 0,2s | 0,2001 | 1,01 GiB |
| 18 | 262.144 | 22,7s | 1,0s | −0,0000 | 4,18 GiB |
| **20** | **1.048.576** | **183,6s** | **4,5s** | **0,0609** | **9,11 GiB** |

Exact nhanh hơn ở **mọi** kích thước, khoảng cách **nới rộng**: 23× tại n=18 → **41×** tại n=20.

### Ngân sách QAOA (dry-run mà plan E3 yêu cầu)

| maxiter | runtime | Suy ra |
|---|---|---|
| 10 | 175,0s | **17,9 giây mỗi vòng COBYLA**, chi phí cố định ≈ 0 |
| 30 | 533,9s | |

| Hạng mục | Ngoại suy (maxiter 200) | Ngân sách config | Vượt |
|---|---|---|---|
| 1 seed | 3.590s (60 phút) | 600s | **6,0×** |
| 10 seed | 35.890s (10,0 giờ) | 7.200s | **5,0×** |
| maxiter vừa ngân sách | **33** | khai 200 | — |

### Hình dạng danh mục (Phụ lục G)

| Danh mục | Trần cash | corr | all-ones tối ưu? | coverage@10 |
|---|---|---|---|---|
| **equal-weight (hiện tại)** | 0,1000 = đúng target | **−0,9817** | **Có** | **0,599** ❌ |
| zipf 1/rank | 0,2152 | −0,4526 | Không | 0,846 ✅ |
| concentrated top5=60% | 0,2040 | −0,4582 | Không | 0,839 ✅ |
| realistic 12 holdings | 0,2700 | −0,7253 | Không | 0,971 ✅ |

### Duyệt đủ trên hàm mục tiêu thật (Phụ lục I)

**2.004 giây, 8 tiến trình, 1.048.576 tổ hợp, hàm canonical không viết lại**

| Phương án | true objective | lệch optimum | hạng | lợi ích thu được |
|---|---|---|---|---|
| **Optimum thật** `[30,0,30,30,0,20,20,0,0,0]%` | **0,821059** | — | **1** | 100% |
| coordinate descent (7,3s) | 0,835184 | **1,72%** | **525** | **97,0%** |
| **pipeline QUBO** (≈21s) | **0,938997** | **14,36%** | **307.751** | **75,0%** |
| no-action | 1,293691 | 57,56% | 1.048.359 | 0% |
| all-ones | 1,357435 | 65,33% | **1.048.576 — tệ nhất** | — |

### Chất lượng surrogate: toàn không gian vs holdout

| Chỉ số | Toàn không gian | Holdout 1.000 (cổng chặn dùng) | Holdout lệch |
|---|---|---|---|
| **top-20 recall** | **0,000** | 0,250 | **lạc quan** |
| **top-100 recall** | **0,000** | — | — |
| top-1000 recall | 0,011 | — | — |
| Spearman ρ | 0,8334 | 0,8887 | lạc quan |
| MAE | 0,03400 | 0,03086 | lạc quan |
| RMSE | 0,04235 | 0,03900 | lạc quan |

Optimum thật xếp **hạng 133.367** theo surrogate.

### Chi phí đơn vị

| Thao tác | Thời gian |
|---|---|
| 1 lần đánh giá true objective | **7,2 ms** |
| Sinh 711 mẫu train | ~16s |
| Verify full 2²⁰ (sau vectorise) | **2,69s** |
| Exact 2²⁰ trên surrogate | **4,5s** |
| Coordinate descent 16 restart | **7,3s** |
| QAOA 1 seed n=20 (dev settings) | **183,6s** |
| Duyệt đủ 4¹⁰ trên true objective, 8 tiến trình | **2.004s** |

---

## J.5 Bảy chỗ tui đã tự đính chính

| # | Kết luận ban đầu | Đính chính | Ở đâu |
|---|---|---|---|
| 1 | `cash_budget_deviation` là nguyên nhân **duy nhất** của all-ones | Tắt hẳn nó mà nghiệm **vẫn** là all-ones — có **hai** lực độc lập | E.1 |
| 2 | "Surrogate được minh oan" | **Sai.** Nó chỉ chưa bị thử thách; equal-weight làm bài toán tuyến tính | E.2, H.4 |
| 3 | Candidate gate chỉ PASS ở N=15 ⇒ mất exact ground truth | **Sai.** Với danh mục lệch, **N=10 PASS** | E.3, G.4 |
| 4 | Giới hạn bộ nhớ theo cỡ statevector (30 bit = 16 GiB) | **Sai.** Statevector 18 qubit chỉ ~4 MB nhưng đo **4,18 GiB** — chi phối bởi **mạch đã transpile** | F.2 |
| 5 | "Reproducibility đã được chứng minh" (§3.13) | **Đúng về model hash, sai về solver.** Cùng seed cho 2 kết quả khác nhau | F.5 |
| 6 | P0-1 cần Phúc/Ngọc đổi tham số tài chính | **Sai trọng tâm.** Nguyên nhân là **fixture danh mục**, không cần đổi tham số nào | G.4 |
| 7 | Pipeline QUBO kém classical "11%" | Con số đúng so với **optimum thật** là **14,36%** | I.1 |

Thêm ba lỗi trong chính script/test tui viết, đã tự bắt: script E4 dùng sai bộ mẫu (211 thay vì 711); test codec so bằng chính xác số thực; script duyệt đủ in sai đơn vị mức bán (`int()` trên phân số).

---

## J.6 Tệp mới tạo trong phiên

| Tệp | Nội dung |
|---|---|
| `packages/quantum/src/qshield_quantum/formulation/validation.py` | Cổng chặn surrogate (P0-2) |
| `packages/quantum/tests/test_surrogate_validation.py` | 6 test |
| `packages/risk/src/qshield_risk/diagnostics.py` | Chẩn đoán objective (P0-1) |
| `packages/risk/tests/test_diagnostics.py` | 9 test |
| `backend/tests/test_optimize_personalization.py` | 8 test (P0-5) |
| `backend/tests/test_optimize_router.py` | 3 test |
| `backend/tests/test_console_quantum_honesty.py` | 6 test |
| `docs/questions-for-ngoc-phuc.md` | 9 câu hỏi cần owner quyết |
| `artifacts_bench/README.md` *(viết lại)* | 3 cảnh báo về dữ liệu không tái lập |

Config chỉ thêm **3 khoá kỹ thuật**: `candidate_gate.stability_seeds`, `candidate_gate.stability_block_length`, `performance_budget.exact_states_per_second`. Thay đổi trong `configs/base.yaml` (ngày IPO VPL, cờ chất lượng SSB) là công việc có sẵn của người dùng, không thuộc đợt này.

---

## J.7 Còn nợ

| Mục | Vì sao chưa | Ai quyết |
|---|---|---|
| **P1-2** `dev_mode: false` | Vượt ngân sách 6× — cần chọn 1 trong 3 phương án | Ngọc (B4) |
| Thí nghiệm hội tụ maxiter | Chưa chạy — cần để chốt B4 | — (tui chạy được) |
| **E4** ablation có/không QAOA | Cơ chế sẵn sàng, **hoãn có chủ đích**: chạy lúc này chỉ đo hai solver cùng giải một mô hình lệch 14,36% | Sau khi chốt A3 |
| E3 "dừng cây tiến trình" | Đổi hành vi khi lỗi, cần Tân xem trước | Tân |
| Chạy lại `artifacts_bench/` | Số cũ không tái lập được | Ngọc (B5) |
| Lặp thí nghiệm danh mục ≥5 dạng | 4 dạng hiện tại, 3 do reviewer dựng | Phúc (A1) |
| Stress pool rỗng, cube kỳ vọng âm | Gốc ở `packages/ai` | Tú |
| Cash band, lexicographic, `risk_policy` | Tham số tài chính | Phúc (A2–A5) |
| 3 tệp governance | Chưa tồn tại | Ngọc (B2) |

---

# Phụ lục K — Benchmark có đối chứng null: QAOA thật sự có cấu trúc

Ba benchmark trước (H, I, và so sánh 8 mã đầu tiên) đều thiếu **giả thuyết null**: chúng so QAOA
với exact và classical, nhưng chưa ai hỏi *một pool bốc ngẫu nhiên thì sao*. Thiếu đối chứng đó,
mọi kết luận "QAOA hữu ích" đều không đứng vững — vì lợi thế có thể chỉ đến từ việc **có pool**,
không phải từ cách sinh pool.

Phụ lục này bổ sung đối chứng đó, cùng ba đối chứng khác.

## K.1 Thiết kế

- **5 danh mục sinh ngẫu nhiên** (8–16 mã nắm giữ, trọng số Dirichlet α = 0,7, seed 9000–9004)
- **8 ứng viên → 16 bit → 65.536 tổ hợp**: quy mô duy nhất mà **duyệt đủ hàm mục tiêu THẬT**
  còn khả thi (132–136 giây mỗi danh mục, 8 tiến trình)
- Mọi phương pháp chấm bằng **true financial objective**, so với **optimum tuyệt đối**
- **Cùng pool size** K = 1, 20, 200 — sửa đúng lỗi so 1 nghiệm với 200 nghiệm ở lần đo trước
- QAOA: 10 seed, 128 shots, maxiter 10, **warm-start TẮT** (theo `plan.md` E4: không prime bằng
  classical rồi gọi là tự tìm)

## K.2 Kết quả — trung bình % lệch optimum trên 5 danh mục

| Phương pháp | K=1 | K=20 | K=200 |
|---|---|---|---|
| Duyệt đủ TRUE *(mốc chuẩn)* | 0,00% | 0,00% | 0,00% |
| **Classical trực tiếp trên TRUE objective** | **0,41%** | **0,41%** | **0,41%** |
| QAOA pool | 7,39% | **1,67%** | 1,15% |
| Exact top-K | 9,33% | 1,74% | **0,69%** |
| Classical pool trên surrogate | 9,33% | 3,15% | 2,43% |
| **RANDOM K bitstring** *(giả thuyết null)* | 13,87% | 7,16% | 2,96% |
| No-action | 58,54% | 58,54% | 58,54% |

Optimum thật của 5 danh mục: 0,743671 · 0,825238 · 0,975671 · 0,733921 · 0,599045.
Khoảng cách no-action → optimum nhất quán **33–38%** ⇒ bài toán thật sự đáng giải.

## K.3 QAOA vượt qua giả thuyết null — đính chính dự đoán của reviewer

Trước khi chạy, reviewer **dự đoán** random-200 sẽ ngang QAOA-200, và ghi rõ dự đoán đó vào biên
bản để không sửa lại sau. **Dự đoán sai.**

| Đối chứng | K=1 | K=20 | K=200 |
|---|---|---|---|
| QAOA vs **random** | 7,39 vs 13,87 | 1,67 vs 7,16 | 1,15 vs 2,96 |
| QAOA vs **classical local search cùng surrogate** | 7,39 vs 9,33 | 1,67 vs 3,15 | 1,15 vs 2,43 |

QAOA thắng **cả hai đối chứng ở mọi K**. Đây là **bằng chứng thật đầu tiên trong repo** rằng
phân phối mà mạch QAOA sinh ra **có cấu trúc hữu ích**, không phải nhiễu — đúng vai trò
"candidate generator" mà §7 mô tả, và lần này đo sòng phẳng: cùng K, có đối chứng null, chấm
bằng true objective, warm-start tắt.

Điều này **mạnh hơn** kết quả bị rút lại ở lượt trước (khi so 1 nghiệm exact với 200 nghiệm QAOA).

## K.4 Nhưng bức tranh lớn không đổi

**Classical trực tiếp trên true objective đạt 0,41%** — thắng mọi phương pháp đi qua mô hình xấp
xỉ, kể cả exact top-200 (0,69%).

| | Chất lượng | Chi phí |
|---|---|---|
| Classical trực tiếp trên true objective | **0,41%** | **7,3 s** |
| QAOA pool 200 (qua surrogate) | 1,15% | **58 s** |
| Exact top-200 (qua surrogate) | 0,69% | 0,2 s + 16 s lấy mẫu |

Kết luận chính xác: **QAOA là bộ lấy mẫu tốt cho surrogate, nhưng surrogate là thứ không đáng
lấy mẫu.** Trần chất lượng của cả đường QUBO vẫn bị đặt bởi mô hình xấp xỉ, đúng như Phụ lục H
và I đã chỉ ra.

## K.5 Ba hệ quả thực dụng

**1. Đường sản phẩm đang ở cấu hình tệ nhất.** Nó lấy **1 nghiệm** exact — cột K=1, ô 9,33%. Chỉ
cần đổi `top_n` từ 1 lên 200 rồi rerank: **9,33% → 0,69%**, tốn thêm 0,2 giây. Đây là cải thiện
rẻ nhất trong toàn bộ đợt rà soát, và **không cần quantum, không cần đổi tham số tài chính**.

**2. Nếu chọn hướng (c) ở câu A3** — bỏ surrogate ở N=10, dùng classical trực tiếp — con số kỳ
vọng là **0,41%**, tốt hơn mọi thứ đo được, với 7,3 giây.

**3. Nhánh quantum có một luận điểm thật để giữ.** Không phải "nhanh hơn" hay "tối ưu hơn", mà:
*mạch QAOA sinh ra phân phối ứng viên tốt hơn cả lấy mẫu ngẫu nhiên lẫn tìm kiếm cục bộ cổ điển
trên cùng một mô hình*. Đó là phát biểu **đo được, đã kiểm chứng, và không phóng đại**. Nó xứng
đáng được nghiên cứu tiếp ở quy mô mà exact không còn khả thi.

## K.6 Giới hạn

- **5 danh mục, một quy mô (8 mã).** Chưa biết quy luật có giữ ở 10–15 mã không.
- **Mỗi danh mục một instance surrogate.** Chưa tách được "QAOA tốt hơn" với "instance này hợp
  với QAOA".
- **QAOA chạy ở cấu hình dev** (128 shots, maxiter 10). Chưa biết cấu hình đầy đủ có tốt hơn không.
- **Vẫn là simulator.** Mọi kết luận về QAOA ở đây là về *thuật toán*, không phải về phần cứng
  lượng tử — trên simulator QAOA không có lợi thế độ phức tạp nào so với exact.
- **Eligibility bị bỏ qua trong script benchmark** (`{t: True}` thay vì đọc artifact thật). Ảnh
  hưởng tới *ứng viên nào được chọn*, không tới *solver nào tốt hơn trên bộ ứng viên đó* — nhưng
  vẫn là sai lệch so với pipeline thật. Đã sửa ở tầng production (K.7).

## K.7 Hai lỗ hổng eligibility phát hiện nhân tiện — đã sửa

**Lỗ hổng 8: `risk_summary.json` không ghi gì về nguồn eligibility.** Không ai truy được một run
đã dùng ảnh chụp ngày nào. Nếu artifact eligibility cũ ba tháng, hoặc ai đó trỏ
`eligibility_artifact` sang tệp khác, run vẫn chạy im lặng.

Đã thêm khối provenance vào `risk_summary.json`:

```json
"eligibility": {
  "source": "data/processed/eligibility_daily.parquet",
  "evaluation_date": "2026-07-30", "snapshot_date": "2026-07-30",
  "snapshot_is_stale": false, "staleness_days": 0,
  "eligible_count": 29, "total_count": 30,
  "ineligible": {"VPL": "INSUFFICIENT_HISTORY"}
}
```

`snapshot_is_stale` là trường quan trọng nhất — nó biến một lỗi im lặng thành một cờ đọc được.

**Lỗ hổng 9: chưa có test nào kiểm bất biến "không đủ điều kiện ⇒ không bao giờ được chọn".**
Production làm đúng (VPL hạng 30, `selected_top10: False`, lý do `INSUFFICIENT_HISTORY`), nhưng
nếu ai truyền `{t: True for t in tickers}` — đúng lỗi script benchmark của reviewer mắc — thì mã
đó lọt vào ứng viên và **không gì báo lỗi**.

Test mới đặt mã không đủ điều kiện ở vị trí **rủi ro nhất** (trọng số lớn nhất, chắc chắn đứng
đầu bảng nếu không bị chặn), và kèm **đối chứng ngược**: nếu bỏ qua eligibility thì mã đó *phải*
được chọn — nếu không thì assert chính không chứng minh được gì.

`plan.md` C5 yêu cầu mã thiếu dữ liệu *"giữ residual risk hoặc block"*, không được biến mất. Test
cũng assert mã bị loại **vẫn xuất hiện** trong bảng ứng viên kèm lý do.
