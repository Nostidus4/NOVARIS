"""Stress-instance bakeoff: exact vs classical vs QAOA (no warm-start).

NON_BASELINE / NON_PRODUCT. This does NOT replace workflow_update evidence.

Why it exists: the real cash-hedge QUBO is nearly linear (corner optimum all-1s), so
exact == classical and solvers cannot be distinguished. This script builds a
*sibling* 10-bit QUBO with strong frustrated interactions + mid-weight preference,
then compares solvers on that harder landscape.

Provenance: scale statistics taken from the real 10-bit fitted surrogate when available;
coefficients themselves are regenerated under a fixed seed so the instance is rugged.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from qshield_quantum.benchmark import coordinate_descent_classical
from qshield_quantum.formulation.qiskit_program import build_quadratic_program
from qshield_quantum.formulation.surrogate import QuadraticSurrogate
from qshield_quantum.solvers.exact import solve_quadratic_exact
from qshield_quantum.solvers.qaoa import solve_qaoa_one_seed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts_bench" / "stress_run"
REAL_QUBO = ROOT / "artifacts_bench" / "warm_start_run" / "qubo_model.json"


def _load_real_scale() -> tuple[float, int]:
    if not REAL_QUBO.exists():
        return 0.023, 10
    payload = json.loads(REAL_QUBO.read_text())
    linear = np.asarray(payload["linear"], dtype=float)
    return float(np.mean(np.abs(linear))), int(payload["dimension"])


def build_stress_model(*, seed: int = 20260807) -> tuple[QuadraticSurrogate, dict]:
    """Frustrated 10-bit QUBO: mixed linear, strong Q, soft prefer Hamming weight = 5."""
    scale, n = _load_real_scale()
    rng = np.random.default_rng(seed)

    # Mixed-sign linear (half assets "want" hedge, half "don't") — unlike real all-negative.
    linear = rng.normal(0.0, scale, size=n)

    # Dense frustrated couplings at ~0.4 * |linear| scale (real off-diag was ~1/400 of linear).
    Q = rng.normal(0.0, scale * 0.4, size=(n, n))
    Q = 0.5 * (Q + Q.T)
    np.fill_diagonal(Q, 0.0)

    # Soft cardinality: prefer ~n/2 ones via P*(sum z - k)^2 expanded into Q/linear/const.
    k = n // 2
    penalty = scale * 3.0
    # (sum z_i)^2 = sum z_i + 2 sum_{i<j} z_i z_j  (since z_i^2=z_i)
    # (sum z - k)^2 = sum z + 2 sum_{i<j} z_i z_j - 2k sum z + k^2
    constant = penalty * (k**2)
    linear = linear + penalty * (1.0 - 2.0 * k)
    for i in range(n):
        for j in range(i + 1, n):
            Q[i, j] += penalty
            Q[j, i] += penalty

    model = QuadraticSurrogate(
        Q=Q,
        linear=linear,
        constant=float(constant),
        residual_sum_squares=0.0,
        rank=n,
        sample_count=0,
    )
    meta = {
        "kind": "synthetic_frustrated_sibling",
        "seed": seed,
        "dimension": n,
        "linear_scale_from_real": scale,
        "quad_scale_factor_vs_real_approx": 0.4 / 5.3e-5 * scale if scale else None,
        "cardinality_target": k,
        "cardinality_penalty": penalty,
        "source_real_qubo": str(REAL_QUBO.relative_to(ROOT))
        if REAL_QUBO.exists()
        else None,
        "disclaimer": (
            "NOT the production cash-hedge QUBO. Solver bakeoff only. "
            "Do not mix with workflow_update true-CVaR claims."
        ),
    }
    return model, meta


def landscape_stats(model: QuadraticSurrogate) -> dict:
    n = model.dimension
    Z = np.array([[(i >> b) & 1 for b in range(n)] for i in range(1 << n)], dtype=float)
    energies = model.evaluate_batch(Z)
    order = np.argsort(energies)
    best_e = float(energies[order[0]])
    best_z = Z[order[0]].astype(int)
    # Count strict 1-bit local minima
    local_minima = 0
    for idx in range(1 << n):
        z = Z[idx].astype(int)
        e = float(energies[idx])
        is_min = True
        for b in range(n):
            neigh = z.copy()
            neigh[b] ^= 1
            if float(model.evaluate(neigh)) < e - 1e-12:
                is_min = False
                break
        if is_min:
            local_minima += 1
    corner_e = float(model.evaluate(np.ones(n)))
    zero_e = float(model.evaluate(np.zeros(n)))
    return {
        "states": int(1 << n),
        "global_optimum_bitstring": "".join(map(str, best_z)),
        "global_optimum_energy": best_e,
        "global_optimum_hamming_weight": int(best_z.sum()),
        "all_ones_energy": corner_e,
        "all_ones_is_optimum": bool(np.array_equal(best_z, np.ones(n, dtype=int))),
        "all_zeros_energy": zero_e,
        "local_minima_count": local_minima,
        "energy_gap_top2": float(energies[order[1]] - best_e),
        "lin_over_quad_ratio": float(
            np.mean(np.abs(model.linear))
            / max(np.mean(np.abs(model.Q - np.diag(np.diag(model.Q)))), 1e-12)
        ),
    }


def run_classical(model: QuadraticSurrogate, *, restarts: int, seed: int) -> dict:
    t0 = time.perf_counter()
    bitstring, energy = coordinate_descent_classical(
        model, feasibility=None, restarts=restarts, seed=seed
    )
    return {
        "bitstring": bitstring,
        "energy": float(energy),
        "restarts": restarts,
        "runtime_seconds": time.perf_counter() - t0,
    }


def run_qaoa(
    model: QuadraticSurrogate,
    *,
    seeds: list[int],
    shots: int,
    maxiter: int,
) -> dict:
    names = [f"b{i}" for i in range(model.dimension)]
    qp = build_quadratic_program(
        model.Q, model.linear, model.constant, ticker_order=names
    )
    by_seed: dict[str, dict] = {}
    t0 = time.perf_counter()
    for seed in seeds:
        result = solve_qaoa_one_seed(
            qp,
            seed=seed,
            shots=shots,
            maxiter=maxiter,
            feasibility=lambda _z: True,
            reference_bitstring=None,
            warm_start=False,
            candidate_pool_size=20,
        )
        by_seed[str(seed)] = {
            "bitstring": result.bitstring,
            "energy": float(result.energy),
            "feasible": result.feasible,
            "success_prob": float(result.success_prob),
            "feasibility_rate": float(result.feasibility_rate),
            "runtime_seconds": float(result.runtime_seconds),
            "warm_start_used": result.warm_start_used,
        }
        print(
            f"[stress] qaoa_seed_{seed}={result.runtime_seconds:.2f}s "
            f"bits={result.bitstring} E={result.energy:.6f}",
            flush=True,
        )
    total = time.perf_counter() - t0
    best = min(by_seed.values(), key=lambda row: row["energy"])
    return {
        "seeds": by_seed,
        "winning_bitstring": best["bitstring"],
        "winning_energy": best["energy"],
        "runtime_seconds_total": total,
        "shots": shots,
        "maxiter": maxiter,
        "warm_start": False,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    model, meta = build_stress_model()
    landscape = landscape_stats(model)
    print("[stress] landscape:", json.dumps(landscape, indent=2), flush=True)

    t0 = time.perf_counter()
    exact = solve_quadratic_exact(model, feasibility=None, top_n=20)
    exact_runtime = time.perf_counter() - t0
    exact_payload = {
        "best_feasible_bitstring": exact.best_feasible_bitstring,
        "best_feasible_energy": exact.best_feasible_energy,
        "evaluated_states": exact.evaluated_states,
        "runtime_seconds": exact_runtime,
    }
    print(
        f"[stress] exact={exact_runtime:.3f}s opt={exact.best_feasible_bitstring} "
        f"E={exact.best_feasible_energy:.6f}",
        flush=True,
    )

    classical_weak = run_classical(model, restarts=4, seed=0)
    classical_strong = run_classical(model, restarts=64, seed=0)
    print(
        f"[stress] classical_weak(restarts=4)={classical_weak['runtime_seconds']:.3f}s "
        f"bits={classical_weak['bitstring']} E={classical_weak['energy']:.6f}",
        flush=True,
    )
    print(
        f"[stress] classical_strong(restarts=64)={classical_strong['runtime_seconds']:.3f}s "
        f"bits={classical_strong['bitstring']} E={classical_strong['energy']:.6f}",
        flush=True,
    )

    # Fast 10-bit smoke: 1 seed, reduced shots/maxiter. NON_FINAL — not a 10-seed claim.
    qaoa = run_qaoa(model, seeds=[101], shots=256, maxiter=30)

    opt_e = exact.best_feasible_energy

    def gap(energy: float) -> float:
        if opt_e == 0:
            return float("nan")
        return (energy - opt_e) / abs(opt_e)

    summary = {
        "status": "NON_BASELINE_RUN",
        "NON_FINAL_CONFIG": True,
        "meta": meta,
        "landscape": landscape,
        "exact": exact_payload,
        "classical_weak": {
            **classical_weak,
            "optimality_gap": gap(classical_weak["energy"]),
        },
        "classical_strong": {
            **classical_strong,
            "optimality_gap": gap(classical_strong["energy"]),
        },
        "qaoa": {**qaoa, "optimality_gap": gap(qaoa["winning_energy"])},
        "comparison": {
            "qaoa_beats_classical_weak": bool(
                qaoa["winning_energy"] < classical_weak["energy"] - 1e-12
            ),
            "qaoa_beats_classical_strong": bool(
                qaoa["winning_energy"] < classical_strong["energy"] - 1e-12
            ),
            "qaoa_matches_exact": bool(
                qaoa["winning_bitstring"] == exact.best_feasible_bitstring
            ),
            "classical_strong_matches_exact": bool(
                classical_strong["bitstring"] == exact.best_feasible_bitstring
            ),
            "caveat": (
                "Synthetic frustrated sibling — not production true-CVaR evidence. "
                "No quantum-advantage claim (simulator StatevectorSampler)."
            ),
        },
    }

    (OUT / "stress_model.json").write_text(
        json.dumps({"meta": meta, **model.to_dict()}, indent=2)
    )
    (OUT / "stress_bakeoff.json").write_text(json.dumps(summary, indent=2))
    print("[stress] wrote", OUT / "stress_bakeoff.json", flush=True)
    print(
        "[stress] verdict:",
        json.dumps(summary["comparison"], indent=2),
        flush=True,
    )


if __name__ == "__main__":
    main()
