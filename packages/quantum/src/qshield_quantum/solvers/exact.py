# Đỗ Ngọc Tân - duyệt đủ 2^8 = 256 bitstring — ground truth để chấm QAOA, không được bỏ để tiết kiệm thời gian.
"""Exact solver — duyệt ĐỦ 2⁸=256 bitstring bằng `objective.py` trực tiếp (CLAUDE.md quy tắc 16:
"thước đo, không phải đối thủ" — không qua QUBO convert, đây là ground truth độc lập).

Báo cáo cả `best_feasible` (Σz=K — dùng làm optimum thật) và `best_overall` (kể cả infeasible —
nếu một bitstring infeasible thắng thì `penalty P` chưa đủ lớn, đúng lỗi hay gặp đã ghi trong
`docs/runbook/troubleshooting.md` §4: "QAOA luôn trả bitstring vi phạm K → penalty P quá nhỏ").
"""

from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from qshield_quantum.formulation.objective import objective_batch
from qshield_quantum.formulation.surrogate import QuadraticSurrogate
from qshield_quantum.verify.consistency import all_bitstrings, bitstring_chunks


@dataclass(frozen=True)
class ExactResult:
    best_feasible_bitstring: str
    best_feasible_energy: float
    best_overall_bitstring: str
    best_overall_energy: float
    all_energies: dict[str, float]  # toàn bộ 256, dùng cho benchmark (percentile, gap)
    evaluated_states: int


@dataclass(frozen=True)
class ExactCandidate:
    bitstring: str
    energy: float


@dataclass(frozen=True)
class GenericExactResult:
    """Memory-bounded exact result for 16/20-bit workflow models."""

    best_feasible_bitstring: str
    best_feasible_energy: float
    best_overall_bitstring: str
    best_overall_energy: float
    top_feasible_candidates: tuple[ExactCandidate, ...]
    evaluated_states: int
    feasible_states: int


def _to_bitstring(z: np.ndarray) -> str:
    return "".join(str(int(b)) for b in z)


def solve_exact(
    g: np.ndarray,
    C: np.ndarray,
    c: np.ndarray,
    *,
    lambda_1: float,
    lambda_2: float,
    penalty: float,
    k_actions: int,
) -> ExactResult:
    n = g.shape[0]
    Z = all_bitstrings(n)
    energies = objective_batch(
        Z,
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )
    all_energies = {_to_bitstring(Z[i]): float(energies[i]) for i in range(len(Z))}

    feasible_mask = Z.sum(axis=1) == k_actions
    if not feasible_mask.any():
        raise ValueError(
            f"Không có bitstring feasible nào (Σz={k_actions}) trong {2**n} tổ hợp — "
            "kiểm tra lại k_actions/n."
        )
    feasible_idx = np.where(feasible_mask)[0]
    best_feasible_local = feasible_idx[np.argmin(energies[feasible_idx])]
    best_overall_idx = int(np.argmin(energies))

    return ExactResult(
        best_feasible_bitstring=_to_bitstring(Z[best_feasible_local]),
        best_feasible_energy=float(energies[best_feasible_local]),
        best_overall_bitstring=_to_bitstring(Z[best_overall_idx]),
        best_overall_energy=float(energies[best_overall_idx]),
        all_energies=all_energies,
        evaluated_states=len(Z),
    )


def solve_quadratic_exact(
    model: QuadraticSurrogate,
    *,
    feasibility: Callable[[np.ndarray], bool] | None = None,
    chunk_size: int = 65_536,
    top_n: int = 20,
) -> GenericExactResult:
    """Exhaust all states chunk-by-chunk, retaining only optima and a small candidate pool."""
    if top_n < 1:
        raise ValueError(f"top_n must be positive, got {top_n}.")
    is_feasible = feasibility or (lambda _bits: True)
    best_overall: tuple[float, str] | None = None
    best_feasible: tuple[float, str] | None = None
    # Max-heap represented as negative energy.  Only top_n feasible states are retained.
    pool: list[tuple[float, str]] = []
    evaluated = 0
    feasible_count = 0

    for Z in bitstring_chunks(model.dimension, chunk_size):
        energies = model.evaluate_batch(Z)
        overall_idx = int(np.argmin(energies))
        overall_bits = _to_bitstring(Z[overall_idx])
        overall = (float(energies[overall_idx]), overall_bits)
        if best_overall is None or overall < best_overall:
            best_overall = overall

        for z, energy_value in zip(Z, energies, strict=True):
            if not is_feasible(z):
                continue
            feasible_count += 1
            bitstring = _to_bitstring(z)
            energy = float(energy_value)
            candidate = (-energy, bitstring)
            if len(pool) < top_n:
                heapq.heappush(pool, candidate)
            elif energy < -pool[0][0]:
                heapq.heapreplace(pool, candidate)
            current = (energy, bitstring)
            if best_feasible is None or current < best_feasible:
                best_feasible = current
        evaluated += len(Z)

    if best_overall is None or best_feasible is None:
        raise ValueError(
            f"No feasible state found while evaluating {evaluated} states "
            f"for a {model.dimension}-bit model."
        )
    candidates = tuple(
        ExactCandidate(bitstring=bits, energy=-negative_energy)
        for negative_energy, bits in sorted(pool, key=lambda item: (-item[0], item[1]))
    )
    return GenericExactResult(
        best_feasible_bitstring=best_feasible[1],
        best_feasible_energy=best_feasible[0],
        best_overall_bitstring=best_overall[1],
        best_overall_energy=best_overall[0],
        top_feasible_candidates=candidates,
        evaluated_states=evaluated,
        feasible_states=feasible_count,
    )
