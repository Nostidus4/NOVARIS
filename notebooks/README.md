# notebooks/

Notebooks **chỉ gọi** CLI/`packages/` — không chứa công thức tài chính (CLAUDE.md).

## Chuỗi chính (`exploration/`) — workflow_update

Chạy theo thứ tự khi cần tái lập timing / smoke:

| # | File | Việc |
|---|---|---|
| 00 | `00_profile_config_check.ipynb` | Kiểm tra profile + override merge |
| 01 | `01_data_workflow_update.ipynb` | Data build / audit 30 mã |
| 02 | `02_ai_regime_scenarios_workflow.ipynb` | Regime + scenarios (S=5000) |
| 03 | `03_risk_workflow_update.ipynb` | Risk prepare / rerank / true-benchmark |
| 04 | `04_quantum_benchmark_workflow.ipynb` | Quantum workflow (thường exact-only) |
| 05 | `05_pipeline_workflow_update.ipynb` | Pipeline end-to-end |
| 06 | `06_qaoa_scaling_and_depth.ipynb` | Narrative: exact scaling + QAOA depth scan |

Mặc định override: `configs/provisional/workflow_update_downstream.yaml` (`NON_BASELINE_RUN`).

## Đã gỡ (2026-08-07)

Chuỗi cũ không số (`data_exploration`, `ai_regime_scenarios`, `risk_effects`, `quantum_solve`,
`pipeline_full_run`) đã bị thay bởi `01`…`05`. Thư mục trống `benchmarks/` / `validation/` cũng
gỡ — benchmark narrative nằm ở `06`.
