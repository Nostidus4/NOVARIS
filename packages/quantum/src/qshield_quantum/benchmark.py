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

from collections.abc import Callable

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


def build_generic_benchmark(
    exact: GenericExactResult,
    qaoa_by_seed: dict[int, QaoaSeedResult],
    *,
    model: QuadraticSurrogate,
    feasibility: Callable[[np.ndarray], bool] | None = None,
    classical_restarts: int = 64,
    classical_seed: int = 0,
) -> dict:
    """Compare workflow QAOA honestly with exact exhaustive and local-search baselines."""
    if len(qaoa_by_seed) < 10:
        raise ValueError(
            f"Generic benchmark requires at least 10 QAOA seeds, got {len(qaoa_by_seed)}."
        )
    feasible = [result for result in qaoa_by_seed.values() if result.feasible]
    qaoa_pool = feasible or list(qaoa_by_seed.values())
    winning = min(qaoa_pool, key=lambda result: (result.energy, result.bitstring))
    classical_bits, classical_energy = coordinate_descent_classical(
        model,
        feasibility=feasibility,
        restarts=classical_restarts,
        seed=classical_seed,
    )
    return {
        "winning_seed": winning.seed,
        "winning_bitstring": winning.bitstring,
        "winning_energy": winning.energy,
        "winning_is_feasible": winning.feasible,
        "n_seeds_feasible": len(feasible),
        "n_seeds_total": len(qaoa_by_seed),
        "exact_best_bitstring": exact.best_feasible_bitstring,
        "exact_best_energy": exact.best_feasible_energy,
        "exact_evaluated_states": exact.evaluated_states,
        "qaoa_optimality_gap": _relative_gap(
            winning.energy, exact.best_feasible_energy
        ),
        "mean_feasibility_rate": float(
            np.mean([result.feasibility_rate for result in qaoa_by_seed.values()])
        ),
        "classical_bitstring": classical_bits,
        "classical_energy": classical_energy,
        "classical_gap": _relative_gap(classical_energy, exact.best_feasible_energy),
        "qaoa_beats_classical": bool(winning.energy < classical_energy),
        "warm_start_seeds": sum(
            result.warm_start_used for result in qaoa_by_seed.values()
        ),
        "runtime_seconds_total": float(
            sum(result.runtime_seconds for result in qaoa_by_seed.values())
        ),
        "caveat": (
            "Statevector simulation is not quantum hardware and this benchmark does not "
            "establish quantum advantage."
        ),
    }
