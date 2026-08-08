# packages/quantum/

**Owner:** Đỗ Ngọc Tân
**Vai trò:** QUBO formulation, exact, QAOA, classical-on-QUBO, benchmark, verify.
**Workflow-v2:** §15–16.

## Nhiệm vụ

- Ground truth objective NumPy (`formulation/objective.py`) — QP/QUBO phải khớp.
- Build QUBO / four-level encoding (20-bit workflow).
- Exact brute-force (256 @ 8-bit; 2^20 @ 20-bit) = thước đo QUBO, không phải đối thủ marketing.
- QAOA qua **qiskit 2.x** `StatevectorSampler` (không dùng Sampler V1 đã xóa).
- Classical local search trên cùng QUBO hash.
- `verify/consistency.py` — chạy trước khi tin QAOA.
- Benchmark fair: cùng qubo_hash, đủ seed, true-objective rerank qua risk.

## Cây chính

```text
qshield_quantum/
  formulation/{objective,qubo,qiskit_program,penalty,surrogate,four_level}.py
  solvers/{exact,qaoa,warm_start}.py
  verify/consistency.py
  backends/{simulator.py, hardware.py}   # hardware cố ý trống
  benchmark.py, workflow.py, decode.py, io.py, cli.py
```

## Được làm

- Import `qshield_risk.evaluate` để chấm true CVaR (duy nhất cross-import ngược).
- Warm-start experiment **tách** khỏi no-warm-start — không dùng warm-start từ exact để claim QAOA tự tìm optimum.

## Không được làm

- Tuyên bố quantum advantage.
- Cherry-pick seed.
- Bỏ exact “cho nhanh”.
- Debug QAOA khi consistency QUBO còn lệch.
- `from qiskit.primitives import Sampler` (V1) — ImportError trên 2.x.
- Aer SamplerV2 trực tiếp trên ansatz QAOA (cần transpile ISA).

## Artifact điển hình

- `optimization/qubo_model.json`, `exact_solution.json`, `qaoa_result(s).json`
- `benchmark.json` / solver_benchmark — ghi `requested_solver` vs `actual_solver`

## Context cho Claude

- Dependency: cần `qiskit-algorithms` (QAOA) + `qiskit-optimization` (MinimumEigenOptimizer).
- Trước tin kết quả:

```bash
uv run pytest packages/quantum/tests/test_consistency.py -v
```

- Scope SoT: `workflow_update` = 20-bit, 4 mức/mã (0/10/20/30%).

## Test

```bash
uv run pytest packages/quantum -q
uv run pytest packages/quantum -m "not slow" -q
```
