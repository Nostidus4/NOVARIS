# Kế hoạch hoàn thiện Benchmark (GATE-08 Solver + comparison metrics)

Mục tiêu: đưa benchmark từ trạng thái "so được energy giữa exact/QAOA/classical" lên đủ điều kiện
nghiệm thu **GATE-08 Solver** và bộ `comparison_metrics_against_demo_fast` trong
`configs/profiles/workflow_update.yaml`.

Truy vết yêu cầu: FUNC-048…053, PR-SLV-012…015, PR-OPS-010, PR-NFR-PERF-003/005, NFR-013,
AC-SLV-006…010, KPI-008.

Ràng buộc không được vi phạm khi làm việc này: không cherry-pick seed, không tuyên bố quantum
advantage, không so số giữa hai profile khác nhau, không đặt lại ngưỡng sau khi đã xem kết quả
(CLAUDE.md quy tắc 18, `docs/limitations.md` §4 và §8).

---

## 1. Đang có gì

`packages/quantum/src/qshield_quantum/benchmark.py`:

- `build_benchmark()` — nhánh `demo_fast` (8-bit, K=3), classical baseline greedy theo `g`. Đã chạy
  thật, có `artifacts/dev/optimization/benchmark.json`.
- `build_generic_benchmark()` — nhánh `workflow_update`, classical baseline là coordinate descent
  đa khởi tạo. Trả `winning_*`, `n_seeds_feasible/total`, `exact_best_*`, `qaoa_optimality_gap`,
  `mean_feasibility_rate`, `classical_*`, `qaoa_beats_classical`, `warm_start_seeds`,
  `runtime_seconds_total`, `caveat`. **Chưa từng chạy trọn một lần** (xem
  `docs/perf/2026-08-06-workflow-update-downstream.md` §6).

## 2. Thiếu gì — 12 khoảng trống cụ thể

| # | Thiếu | Yêu cầu bị hở | Chạm vào |
|---|---|---|---|
| G1 | Benchmark không tự kiểm tra exact/QAOA/classical dùng **cùng `qubo_hash`**; hash hiện chỉ được `cli.py` dán vào payload sau khi tính | AC-SLV-008 (khác hash phải làm benchmark FAIL), FUNC-051, KPI-008 | `benchmark.py`, `cli.py` |
| G2 | Không báo `success_prob` (xác suất đo trúng nghiệm tối ưu) dù `QaoaSeedResult` đã có field | FUNC-052, PR-SLV-013 | `benchmark.py` |
| G3 | Không có solver manifest: shots, danh sách seed đã đăng ký, `reps`/depth, optimizer + maxiter, backend, version package, status từng seed | PR-SLV-007/008, AC-SLV-006/007 | `benchmark.py`, `cli.py` |
| G4 | Distribution mỗi seed bị cắt còn top-20 (`candidate_pool_size`) nên **tổng probability không khớp shots**; chưa có kiểm tra tính nhất quán | AC-SLV-010, PR-SLV-011 | `solvers/qaoa.py`, `cli.py` |
| G5 | Chỉ tổng runtime QAOA; không đo runtime exact, runtime classical, runtime từng seed | PR-SLV-013, PR-OPS-010 | `solvers/exact.py`, `benchmark.py` |
| G6 | Không có thống kê phân phối trên toàn bộ seed (best/median/worst/std energy, phân phối gap) — dễ bị đọc thành "chỉ báo seed tốt nhất" | AC-SLV-009, FUNC-053 | `benchmark.py` |
| G7 | Nhánh workflow không có `requested_solver` / `actual_solver` và cơ chế fallback khi QAOA fail/timeout (nhánh `demo_fast` đã có) | PR-SLV-015, FUNC-054 | `workflow.py`, `cli.py` |
| G8 | Không có benchmark ở **tầng tài chính**: exact/QAOA/classical sau khi rerank bằng true objective (CVaR reduction %, return sacrifice, cost per CVaR reduction, worst-drawdown reduction) | `workflow_update.yaml` → `comparison_metrics.risk_quality`, OBJ-007 | `packages/risk/rerank.py`, CLI mới |
| G9 | Không có candidate quality: `top10_risk_coverage_pct` (đã tính trong `candidate_order.json` nhưng chưa vào benchmark), `rank_stability_across_seeds`, `top10_overlap_across_scenario_configs` | `comparison_metrics.candidate_quality` | `packages/risk` |
| G10 | Surrogate mới có RSS/rank của `lstsq`; chưa có objective error, rank correlation, top-k recall so với true objective | FUNC-047, GATE-07 | `formulation/surrogate.py` |
| G11 | Payload benchmark chưa mang `profile_id`/`profile_status`, nên không có gì chặn việc ghép số `demo_fast` với `workflow_update` trong cùng bảng | `docs/limitations.md` §1, CLAUDE.md | contracts + `benchmark.py` |
| G12 | Peak memory và reference hardware chưa đo; chưa có runtime budget/timeout, chưa gắn `NON_FINAL_CONFIG` khi dev-mode giảm shots/seed | NFR-013, PR-OPS-010, PR-NFR-PERF-003/005 | `cli.py`, config |

## 3. Kế hoạch theo pha

### 3.1. Pha 0 — Đo trước, tối ưu sau (chặn mọi pha còn lại)

`qshield-quantum workflow` chưa hoàn tất trong ~12 phút ở 16 bit / 10 seed. **Chưa biết** thời gian
nằm ở đâu, nên không được đoán.

1. Chạy có instrument: log runtime từng phần (fit surrogate → verify consistency → exact → từng
   seed QAOA → classical → benchmark).
2. Ghi số thật vào `docs/perf/` theo mẫu các file cùng thư mục.
3. Chỉ sau khi có số mới quyết định giảm gì: `maxiter`, `reps`, số seed dev-mode, hay chuyển
   `verify_quadratic_consistency` sang chế độ lấy mẫu ở `d ≥ 16`.
4. Mọi cấu hình rút gọn phải gắn `NON_FINAL_CONFIG` trong artifact (PR-NFR-PERF-005).

Owner: Tân. Kết quả: một bảng runtime theo chặng + quyết định cấu hình dev vs final.

### 3.2. Pha 1 — Contract và tính toàn vẹn của benchmark (G1, G3, G11)

- Thêm `BenchmarkReport` vào `packages/contracts/schemas/downstream.py` với provenance đầy đủ +
  `qubo_hash` + `candidate_order_hash` + `solver_manifest`.
- `build_generic_benchmark()` nhận `qubo_hash` của từng nguồn nghiệm và **raise** khi lệch, thay vì
  để `cli.py` dán hash vào sau.
- Solver manifest: `shots`, `registered_seeds`, `reps`, `optimizer`, `maxiter`, `backend`,
  `package_versions`, `warm_start`, `status` từng seed.
- Benchmark từ chối gộp dữ liệu khác `profile_id`.

Owner: Tân. Reviewer: Phúc.

### 3.3. Pha 2 — Chất lượng nghiệm và phân phối (G2, G4, G6, G7)

- Thêm `success_prob` (mean/max/per-seed) và thống kê energy theo seed: best/median/worst/std, phân
  phối `optimality_gap`.
- Tách distribution thành artifact riêng `qaoa_distribution.parquet` giữ **đủ** measured bitstrings
  + probability, kèm kiểm tra tổng probability ≈ 1 (và quy đổi ra counts theo shots). `qaoa_results.json`
  vẫn giữ top-20 để đọc nhanh.
- Thêm `requested_solver`/`actual_solver` + fallback exact khi mọi seed QAOA không khả thi hoặc
  timeout, ghi rõ lý do fallback.

Owner: Tân.

### 3.4. Pha 3 — Benchmark tầng tài chính (G8)

Đây là phần quan trọng nhất về mặt sản phẩm: energy thấp **không** đồng nghĩa CVaR thật giảm.

- Lệnh mới (đề xuất `qshield-risk benchmark-true`) chấm lại nghiệm tốt nhất của **cả ba** nguồn
  (exact / QAOA / classical) bằng `qshield_risk.objective.financial_objective`.
- Bảng kết quả: CVaR 95/97.5/99 trước–sau, `CVaR_reduction_pct`, `expected_return_sacrifice`,
  `worst_drawdown_reduction`, turnover, transaction cost, `cost_per_CVaR_reduction`.
- Báo `ranking_disagreement` giữa thứ hạng QUBO và thứ hạng true objective — đây là bằng chứng trực
  tiếp cho chất lượng surrogate.
- Nếu QAOA thua exact hoặc thua classical ở **tầng tài chính**, ghi đúng như vậy.

Owner: Phúc. Reviewer: Tân.

### 3.5. Pha 4 — Ổn định và chất lượng đầu vào (G9, G10)

- `top10_risk_coverage_pct` đưa từ `candidate_order.json` vào benchmark.
- `rank_stability_across_seeds`: lặp lại chọn ứng viên trên các seed kịch bản đã đăng ký, báo
  Kendall tau hoặc overlap@10.
- `top10_overlap_across_scenario_configs`: so giữa các cấu hình `block_length`/`num_scenarios` trong
  lưới nhạy cảm của profile.
- Surrogate validation: objective error (RMSE/MAE trên tập giữ lại), Spearman rank correlation,
  top-k recall. Ngưỡng do Phúc/Ngọc duyệt **trước** khi chạy final (FUNC-047).

Owner: Phúc (candidate) + Tân (surrogate).

### 3.6. Pha 5 — Vận hành và công bố (G5, G12)

- Đo peak memory (`resource.getrusage` hoặc `tracemalloc`) cho exact 2^16 và 2^20.
- Ghi reference hardware (CPU, RAM, OS, Python, qiskit version) vào benchmark.
- Timeout mỗi seed + tổng, có đường thoát an toàn.
- Viết `docs/perf/<ngày>-benchmark-workflow-update.md` với số thật, kèm caveat simulator.
- Cập nhật `docs/product/rtm.md` và test evidence: GATE-08, AC-SLV-006…010, KPI-008.

Owner: Tân + Ngọc.

## 4. Định nghĩa hoàn thành

Benchmark coi là xong khi **tất cả** đúng:

1. `workflow_benchmark.json` pass contract, có provenance đầy đủ và `qubo_hash` giống nhau ở cả ba
   nguồn nghiệm; đổi hash làm benchmark fail.
2. Có exact reference duyệt đủ `2^d` trạng thái (65.536 ở M=8, 1.048.576 ở M=10) và ít nhất một
   classical baseline trên cùng QUBO.
3. Báo đủ: best feasible energy, optimality gap, feasible rate, success probability, runtime tách
   theo solver, shots, seeds, depth, backend.
4. Có thống kê trên **toàn bộ** seed đã đăng ký, không chỉ seed thắng.
5. Có bảng benchmark tầng tài chính sau true-objective rerank cho cả ba nguồn.
6. Có peak memory + reference hardware.
7. Mọi kết luận không vượt quá bằng chứng: không có câu nào ngụ ý quantum advantage; caveat
   simulator xuất hiện trong artifact và trong báo cáo.

## 5. Thứ tự đề xuất

Pha 0 → Pha 1 → Pha 2 → Pha 3 → Pha 4 → Pha 5. Pha 3 có thể chạy song song với Pha 2 vì chạm hai
package khác nhau (`risk` vs `quantum`), miễn là contract ở Pha 1 đã chốt.

## 6. Việc KHÔNG làm trong kế hoạch này

- Không chạy phần cứng lượng tử thật (`backends/hardware.py` vẫn để trống theo thiết kế).
- Không thêm solver mới ngoài exact / QAOA / classical local search.
- Không dùng benchmark của một profile để kết luận cho profile kia.
- Không sửa ngưỡng surrogate validation sau khi đã nhìn kết quả.
