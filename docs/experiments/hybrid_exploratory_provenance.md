# Pha 0 — Provenance của kết quả exploratory 1,11% / 4,79% / 5,84% và 1,9% coverage

Ngày: 2026-09-13 · Nhãn: `EXPLORATORY_NON_BASELINE` · Plan: `plan-qaoa-assisted.md` §4

## 0.1 Truy nguồn

| Kiểm tra | Kết quả |
|---|---|
| Tìm script/notebook sinh 1,11% / 4,79% / 5,84% trong **toàn bộ lịch sử git** (189 commit, mọi branch local + remote; tìm `seeded`, `1,9%`, `65536`, `polish`) | **Không có.** Chỉ `notebooks/exploration/06_qaoa_scaling_and_depth.ipynb` chứa số exact 0,223 s / classical 0,0114 s ở 16-bit |
| Artifact per-instance của 5 danh mục | Không có trong `artifacts/` |
| Kết luận | **`NOT_REPRODUCIBLE`** — ba con số chỉ là giả thuyết; không được dùng làm claim |

## 0.2 Vì sao 1,9% không thể đến từ code cũ

1. `solve_qaoa_one_seed` cũ chỉ giữ top-`candidate_pool_size` (20) sample/seed → tối đa 10 × 20 = 200
   trạng thái = 0,3% của 2^16.
2. **Bug đã xác minh** (qiskit-algorithms 0.4.0 + qiskit-optimization 0.7.0): `result.samples[i].probability`
   là `p²` chứ không phải `p`, vì `MinimumEigenOptimizer._eigenvector_to_solutions` coi eigenstate dạng
   `dict` (xác suất) là biên độ và bình phương. Σ probability ≈ 0,09–0,16 thay vì 1. Mọi
   `feasibility_rate` / `success_prob` cũ bị đánh giá thấp theo cùng cách. Đã sửa ở
   `solvers/qaoa.py::_measured_distribution` (đọc thẳng eigenstate, kiểm Σp = 1) và có test
   `test_qaoa_full_distribution_is_lossless`.
3. Trần lý thuyết với 10 seed × 1024 shots: ≤ 10.240 trạng thái unique = 15,6% của 65.536.

Coverage mới được báo dạng phân số tuyệt đối trong `instance_result.json → qaoa_distribution_metrics`
(`coverage_all_fraction`, `coverage_feasible_fraction`, duplicate đếm một lần).

## 0.3 / 0.4 — Optimum và phụ thuộc polishing

Không trả lời được cho số cũ (không có artifact). Với code mới, mỗi instance báo:

- `references.qubo_optimum_equals_true_grid_optimum`, `qubo_optimum_true_rank`,
  `spearman_energy_vs_true_all_feasible` — QUBO optimum có phải true optimum không;
- `raw_best_abs_gap` (so `J*_grid`) và `polished_abs_gap_best_known` cho **từng track**;
- `winner_polishing_dependency`, `winner_start_rank`, track ablation `heuristic_baselines`.

## 0.5 Contamination

Code cũ `_merge_candidate_pool` khởi tạo pool bằng `exact.top_feasible_candidates` → pool bị nhiễm exact.
Pool mới tách theo track; `validate_candidate_pool` hard-fail nếu track khác `exact_reference` mang
`source_method` chứa "exact".
