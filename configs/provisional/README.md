# configs/provisional/ — runtime overrides (NOT product baseline)

Files here are deep-merged after `configs/base.yaml` + `configs/profiles/*.yaml`
via `Config.load_profiled(..., override_yaml=...)`.

| File | Keep? | Role |
|---|---|---|
| `workflow_update_downstream.yaml` | **yes — default** | Decision-package numbers for `workflow_update` while gates unsigned (`NON_BASELINE_RUN`). Used by pipeline CLI + backend defaults. |
| `qaoa_benchmark_10bit.yaml` | yes — bakeoff only | Extends downstream; shrinks to 5 candidates / 10 bits so QAOA can finish on simulator. **Not** UAT. |

Rules:

1. Do not put baseline/UAT claims in this folder until gates are signed — then promote into
   `configs/profiles/workflow_update.yaml` (or module yaml), not by renaming provisional quietly.
2. Prefer `extends: <sibling.yaml>` for delta-only files (see 10-bit bakeoff) instead of copying
   the whole Decision-package block.
3. One-off smoke files that duplicate downstream get deleted after the experiment (e.g. retired
   `qaoa_20bit_no_warm_smoke.yaml`).
