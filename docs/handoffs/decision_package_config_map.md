# Decision-package → config key map

Ngày: 2026-08-07
Nguồn: `docs/handoffs/Decision-package.md`
Máy đọc được: `configs/profiles/workflow_update.yaml` + `configs/provisional/workflow_update_downstream.yaml`
Load: `Config.load_profiled(base, profile, override)`

Status mọi run dùng override này: **`NON_BASELINE_RUN`** tới khi đủ 3 gate (TL-019).

| TL | Quyết định (tóm tắt) | Khóa config chính |
|---|---|---|
| TL-001 | Universe 30 snapshot 2026-08-03 | `data.snapshot_date`, `data.expected_input_tickers`, artifact `universe_30_asof_20260803.csv` |
| TL-002 | Không gán `close=adjusted_close` im lặng | `data.adjusted_price_policy.*` |
| TL-003 | `asset_train_start=2016-01-01`, `test_end=2026-07-31` | `data.date_range.*` / `date_range.*` |
| TL-004 | Eligibility 252 / 98% / 1e9 VND + reason | `data.eligibility.*` |
| TL-005 | Dev 2000 / final ưu tiên 5000 | `scenarios.num_scenarios.{dev,final}`; override `num_scenarios` |
| TL-006 | Scenario Gate thresholds; fail quan trọng ≠ baseline | `scenarios.validation_gate.thresholds.*` |
| TL-007 | fee 0.0015, spread 0.0010, liq 0.0005, tol 1e-8 | `transaction_cost.*`, `weight_sum_tolerance`, `cost_sensitivity.{low,base,high}` |
| TL-008 | Liquidity tách khỏi txn cost | `financial_objective.components.transaction_cost` + `.liquidity_penalty` |
| TL-009 | Cash +10%, max reduction 30% | `target_cash_increment`, `maximum_reduction` |
| TL-010 | Net score ranking + tie-break | `candidate_selection.exclude_*`, `.tie_break`, `.score_weights` |
| TL-011 | CVaR trước cash target | `financial_objective.priority: cvar_first` |
| TL-012 | QAOA p=1, shots=1024, maxiter=200, 10 seeds, warm-start | `quantum.qaoa.*`; rút gọn → `NON_FINAL_CONFIG` / `dev_mode` |
| TL-013 | Timeout exact / seed / tổng + máy reference | `performance_budget.*` |
| TL-014 | Surrogate MAE/RMSE/Spearman/top-k/feasible/stability | `surrogate_validation.thresholds.*` (**PROVISIONAL**) |
| TL-015 | Exact+QAOA+classical cùng `qubo_hash` | `benchmark.require_same_qubo_hash`, schema `BenchmarkReport` |
| TL-016 | Rerank top 20 distinct feasible | `reranking.top_distinct_feasible: 20` |
| TL-017 | Polish zero-lock ±5pp, [0,30%] | `local_polishing.*` |
| TL-018 | Materiality ≥1% relative CVaR | `materiality.true_cvar_relative_reduction_min`; `FinalRecommendation.materiality_*` |
| TL-019 | 3 gate sign-off | `governance.approval_gates.*`; schema `GateVerdict` |
| TL-020 | Underfill `M=min(N_eligible,10)` | `runtime.*`, `candidate_selection.underfilled` |
| TL-021 | Dual candidate artifacts | `candidate_selection.output_filename`, `encoding.candidate_order_filename` |
| TL-022 | QAOA fail → exact + `actual_solver` | `BenchmarkReport.requested_solver` / `actual_solver` / `fallback_reason` |
| TL-023 | No quantum advantage claim | `profile.not_allowed_for`, `disclosures` |

Notebook kiểm tra: `notebooks/exploration/00_profile_config_check.ipynb`.
