# Đỗ Ngọc Tân - gap, feasibility, success probability, runtime, circuit depth.
"""Tổng hợp benchmark: exact vs QAOA (mọi seed) vs classical baseline.

Classical baseline: greedy chọn K mã có `g_i` lớn nhất, bỏ qua tương tác `C` (đơn giản nhất có thể
biện minh được — `plan.md` câu hỏi 5). Cần có để CLAUDE.md quy tắc 18 ("QAOA thua exact hay thua
classical thì báo cáo trung thực") có cái để so — **không diễn giải kết quả theo hướng có lợi cho
QAOA** (CLAUDE.md quy tắc 18: không tuyên bố quantum advantage).

Đây là artifact PHỤ (`benchmark.json`), tách khỏi `qaoa_result.json` (theo đúng `schemas/
optimization.py::QaoaResult` đã khóa) — không nhét thêm field vào schema đã có.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

from qshield_quantum.formulation.objective import objective
from qshield_quantum.formulation.surrogate import QuadraticSurrogate
from qshield_quantum.solvers.exact import ExactResult, GenericExactResult
from qshield_quantum.solvers.qaoa import QaoaSeedResult


def greedy_classical_baseline(
    g: np.ndarray,
    C: np.ndarray,
    c: np.ndarray,
    *,
    lambda_1: float,
    lambda_2: float,
    penalty: float,
    k_actions: int,
) -> tuple[str, float]:
    """Chọn K mã có `g_i` lớn nhất, chấm energy bằng đúng `objective.objective` (có tính cả `C`
    dù bước chọn không dùng `C`) để so công bằng với exact/QAOA trên cùng một hàm mục tiêu."""
    n = g.shape[0]
    top_k = np.argsort(-g)[:k_actions]
    z = np.zeros(n, dtype=int)
    z[top_k] = 1
    bitstring = "".join(str(b) for b in z)
    energy = objective(
        z,
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )
    return bitstring, energy


def _relative_gap(value: float, reference: float) -> float:
    if reference == 0:
        return float("nan")
    return (value - reference) / abs(reference)


def build_benchmark(
    exact: ExactResult,
    qaoa_by_seed: dict[int, QaoaSeedResult],
    *,
    g: np.ndarray,
    C: np.ndarray,
    c: np.ndarray,
    lambda_1: float,
    lambda_2: float,
    penalty: float,
    k_actions: int,
) -> dict:
    if not qaoa_by_seed:
        raise ValueError("qaoa_by_seed rỗng — không có seed nào để benchmark.")

    feasible_seeds = [r for r in qaoa_by_seed.values() if r.feasible]
    pool = feasible_seeds if feasible_seeds else list(qaoa_by_seed.values())
    winning = min(pool, key=lambda r: r.energy)

    classical_bitstring, classical_energy = greedy_classical_baseline(
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )

    all_results = list(qaoa_by_seed.values())
    return {
        "winning_seed": winning.seed,
        "winning_bitstring": winning.bitstring,
        "winning_energy": winning.energy,
        "winning_is_feasible": winning.feasible,
        "n_seeds_feasible": len(feasible_seeds),
        "n_seeds_total": len(qaoa_by_seed),
        "exact_best_feasible_bitstring": exact.best_feasible_bitstring,
        "exact_best_feasible_energy": exact.best_feasible_energy,
        "exact_best_overall_bitstring": exact.best_overall_bitstring,
        "exact_best_overall_energy": exact.best_overall_energy,
        "exact_evaluated_states": exact.evaluated_states,
        "optimality_gap": _relative_gap(winning.energy, exact.best_feasible_energy),
        "mean_feasibility_rate": float(
            np.mean([r.feasibility_rate for r in all_results])
        ),
        "mean_success_prob": float(np.mean([r.success_prob for r in all_results])),
        "classical_bitstring": classical_bitstring,
        "classical_energy": classical_energy,
        "classical_gap": _relative_gap(classical_energy, exact.best_feasible_energy),
        # CLAUDE.md quy tắc 18 — báo cáo trung thực, KHÔNG diễn giải có lợi cho QAOA.
        "qaoa_beats_classical": bool(winning.energy < classical_energy),
        "runtime_seconds_total": float(sum(r.runtime_seconds for r in all_results)),
        "caveat": (
            "Simulator (StatevectorSampler), không phải phần cứng lượng tử thật. "
            "Không suy diễn kết luận về hiệu năng trên QPU thực (CLAUDE.md quy tắc 18)."
        ),
    }


def coordinate_descent_classical(
    model: QuadraticSurrogate,
    *,
    feasibility: Callable[[np.ndarray], bool] | None = None,
    restarts: int = 64,
    seed: int = 0,
) -> tuple[str, float]:
    """Deterministic-seeded multi-start one-bit local search for the generic branch."""
    if restarts < 1:
        raise ValueError(f"restarts must be positive, got {restarts}.")
    is_feasible = feasibility or (lambda _bits: True)
    rng = np.random.default_rng(seed)
    starts: list[np.ndarray] = [
        np.zeros(model.dimension, dtype=np.int8),
        np.ones(model.dimension, dtype=np.int8),
    ]
    starts.extend(
        rng.integers(0, 2, size=model.dimension, dtype=np.int8)
        for _ in range(max(0, restarts - len(starts)))
    )
    best: tuple[float, str] | None = None
    for start in starts:
        z = start.copy()
        if not is_feasible(z):
            continue
        energy = model.evaluate(z)
        improved = True
        while improved:
            improved = False
            move: tuple[float, int] | None = None
            for index in range(model.dimension):
                candidate = z.copy()
                candidate[index] ^= 1
                if not is_feasible(candidate):
                    continue
                candidate_energy = model.evaluate(candidate)
                if candidate_energy < energy - 1e-12 and (
                    move is None or (candidate_energy, index) < move
                ):
                    move = (candidate_energy, index)
            if move is not None:
                energy, index = move
                z[index] ^= 1
                improved = True
        bitstring = "".join(str(int(bit)) for bit in z)
        candidate_result = (energy, bitstring)
        if best is None or candidate_result < best:
            best = candidate_result
    if best is None:
        raise ValueError("Classical benchmark found no feasible starting state.")
    return best[1], best[0]


def _energy_stats(energies: list[float]) -> dict[str, float]:
    if not energies:
        return {}
    arr = np.asarray(energies, dtype=float)
    return {
        "best": float(np.min(arr)),
        "median": float(np.median(arr)),
        "worst": float(np.max(arr)),
        "std": float(np.std(arr)),
    }


def build_generic_benchmark(
    exact: GenericExactResult,
    qaoa_by_seed: dict[int, QaoaSeedResult],
    *,
    model: QuadraticSurrogate,
    feasibility: Callable[[np.ndarray], bool] | None = None,
    classical_restarts: int = 64,
    classical_seed: int = 0,
    minimum_seeds: int = 10,
    allow_non_final: bool = False,
    NON_FINAL_CONFIG: bool = False,
    requested_solver: str = "qaoa",
    actual_solver: str | None = None,
    fallback_reason: str | None = None,
    exact_runtime_seconds: float | None = None,
    classical_runtime_seconds: float | None = None,
    qubo_hashes: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Compare workflow QAOA honestly with exact exhaustive and local-search baselines.

    Final/baseline evidence requires ``minimum_seeds=10``. ``NON_FINAL_CONFIG`` /
    ``allow_non_final`` may lower the floor (including empty QAOA after exact fallback).
    When QAOA is empty, ``actual_solver`` must be honest (usually ``exact``) with
    ``fallback_reason``.
    """
    non_final = bool(allow_non_final or NON_FINAL_CONFIG)
    if minimum_seeds < 1:
        raise ValueError("minimum_seeds must be >= 1.")
    n_seeds = len(qaoa_by_seed)
    if n_seeds == 0:
        if not non_final:
            raise ValueError(
                "Generic benchmark requires QAOA seeds unless allow_non_final/"
                "NON_FINAL_CONFIG permits exact fallback."
            )
    elif n_seeds < minimum_seeds:
        raise ValueError(
            f"Generic benchmark requires at least {minimum_seeds} QAOA seeds, "
            f"got {n_seeds}."
        )

    if qubo_hashes:
        unique = {str(value) for value in qubo_hashes.values() if value}
        if len(unique) > 1:
            raise ValueError(f"qubo_hash mismatch across solvers: {dict(qubo_hashes)}.")

    classical_bits, classical_energy = coordinate_descent_classical(
        model,
        feasibility=feasibility,
        restarts=classical_restarts,
        seed=classical_seed,
    )
    classical_runtime = (
        0.0 if classical_runtime_seconds is None else float(classical_runtime_seconds)
    )
    exact_runtime = (
        0.0 if exact_runtime_seconds is None else float(exact_runtime_seconds)
    )

    resolved_requested = requested_solver
    resolved_actual = actual_solver
    resolved_fallback = fallback_reason

    if n_seeds == 0:
        if resolved_actual is None:
            resolved_actual = "exact"
        if resolved_requested != resolved_actual and not (
            resolved_fallback and str(resolved_fallback).strip()
        ):
            resolved_fallback = (
                resolved_fallback
                or "QAOA empty — exact fallback (NON_FINAL_CONFIG / timeout / skipped)"
            )
        return {
            "winning_seed": None,
            "winning_bitstring": exact.best_feasible_bitstring,
            "winning_energy": exact.best_feasible_energy,
            "winning_is_feasible": True,
            "n_seeds_feasible": 0,
            "n_seeds_total": 0,
            "qaoa_seed_count": 0,
            "exact_best_bitstring": exact.best_feasible_bitstring,
            "exact_best_energy": exact.best_feasible_energy,
            "exact_evaluated_states": exact.evaluated_states,
            "qaoa_optimality_gap": None,
            "optimality_gap": None,
            "mean_feasibility_rate": None,
            "feasible_rate": None,
            "mean_success_prob": None,
            "max_success_prob": None,
            "success_prob": None,
            "energy_stats": {},
            "classical_bitstring": classical_bits,
            "classical_energy": classical_energy,
            "classical_gap": _relative_gap(
                classical_energy, exact.best_feasible_energy
            ),
            "qaoa_beats_classical": False,
            "warm_start_seeds": 0,
            "runtime_seconds_total": 0.0,
            "runtime_seconds": {
                "exact": exact_runtime,
                "qaoa": 0.0,
                "classical": classical_runtime,
            },
            "requested_solver": resolved_requested,
            "actual_solver": resolved_actual,
            "fallback_reason": resolved_fallback,
            "NON_FINAL_CONFIG": non_final,
            "caveat": (
                "NON_FINAL_CONFIG exact fallback; no QAOA result and no quantum "
                "advantage claim."
            ),
        }

    feasible = [result for result in qaoa_by_seed.values() if result.feasible]
    qaoa_pool = feasible or list(qaoa_by_seed.values())
    winning = min(qaoa_pool, key=lambda result: (result.energy, result.bitstring))
    energies = [float(result.energy) for result in qaoa_by_seed.values()]
    success_probs = [float(result.success_prob) for result in qaoa_by_seed.values()]
    mean_success = float(np.mean(success_probs))
    max_success = float(np.max(success_probs))
    gap = _relative_gap(winning.energy, exact.best_feasible_energy)
    qaoa_runtime = float(
        sum(result.runtime_seconds for result in qaoa_by_seed.values())
    )
    feasible_rate = float(
        np.mean([result.feasibility_rate for result in qaoa_by_seed.values()])
    )

    if resolved_actual is None:
        resolved_actual = "qaoa"
    if resolved_requested != resolved_actual and not (
        resolved_fallback and str(resolved_fallback).strip()
    ):
        raise ValueError(
            "actual_solver differs from requested_solver — fallback_reason is required."
        )

    return {
        "winning_seed": winning.seed,
        "winning_bitstring": winning.bitstring,
        "winning_energy": winning.energy,
        "winning_is_feasible": winning.feasible,
        "n_seeds_feasible": len(feasible),
        "n_seeds_total": n_seeds,
        "qaoa_seed_count": n_seeds,
        "exact_best_bitstring": exact.best_feasible_bitstring,
        "exact_best_energy": exact.best_feasible_energy,
        "exact_evaluated_states": exact.evaluated_states,
        "qaoa_optimality_gap": gap,
        "optimality_gap": gap,
        "mean_feasibility_rate": feasible_rate,
        "feasible_rate": feasible_rate,
        "mean_success_prob": mean_success,
        "max_success_prob": max_success,
        "success_prob": mean_success,
        "energy_stats": _energy_stats(energies),
        "classical_bitstring": classical_bits,
        "classical_energy": classical_energy,
        "classical_gap": _relative_gap(classical_energy, exact.best_feasible_energy),
        "qaoa_beats_classical": bool(winning.energy < classical_energy),
        "warm_start_seeds": sum(
            result.warm_start_used for result in qaoa_by_seed.values()
        ),
        "runtime_seconds_total": qaoa_runtime,
        "runtime_seconds": {
            "exact": exact_runtime,
            "qaoa": qaoa_runtime,
            "classical": classical_runtime,
        },
        "requested_solver": resolved_requested,
        "actual_solver": resolved_actual,
        "fallback_reason": resolved_fallback,
        "NON_FINAL_CONFIG": non_final,
        "caveat": (
            "Statevector simulation is not quantum hardware and this benchmark does not "
            "establish quantum advantage."
        ),
    }
