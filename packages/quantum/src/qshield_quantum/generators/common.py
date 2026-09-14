# Đỗ Ngọc Tân - không gian trạng thái four-level đã enumerate + Proposal có provenance.
"""State space dùng chung cho mọi generator.

Chỉ số trạng thái = ``int(bitstring, 2)`` (MSB trước) — khớp thứ tự của
``verify.consistency.bitstring_chunks`` và ``solve_quadratic_exact``. Energy lấy từ
``QuadraticSurrogate.evaluate_batch`` (NumPy là ground truth, CLAUDE.md quy tắc 14).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from qshield_quantum.formulation.surrogate import QuadraticSurrogate
from qshield_quantum.verify.consistency import bitstring_chunks

MAX_ENUMERATED_BITS = 24


@dataclass(frozen=True)
class Proposal:
    """Một ứng viên do một nguồn đề xuất (chưa có true objective)."""

    bitstring: str
    source_method: str
    source_rank: int
    qubo_energy: float
    predicate_feasible: bool
    source_seed: int | None = None
    raw_probability: float | None = None


@dataclass(frozen=True)
class StateSpace:
    bit_count: int
    energies: np.ndarray
    predicate_feasible: np.ndarray
    active_counts: np.ndarray

    @property
    def total_states(self) -> int:
        return int(self.energies.shape[0])

    @property
    def total_feasible_states(self) -> int:
        return int(self.predicate_feasible.sum())

    def proposal(
        self,
        index: int,
        *,
        source_method: str,
        source_rank: int,
        source_seed: int | None = None,
        raw_probability: float | None = None,
    ) -> Proposal:
        return Proposal(
            bitstring=index_to_bitstring(int(index), self.bit_count),
            source_method=source_method,
            source_rank=int(source_rank),
            qubo_energy=float(self.energies[index]),
            predicate_feasible=bool(self.predicate_feasible[index]),
            source_seed=source_seed,
            raw_probability=raw_probability,
        )


def index_to_bitstring(index: int, bit_count: int) -> str:
    return format(int(index), f"0{bit_count}b")


def bitstring_to_index(bitstring: str) -> int:
    return int(bitstring, 2)


def bits_from_indices(indices: np.ndarray, bit_count: int) -> np.ndarray:
    values = np.asarray(indices, dtype=np.uint64)
    shifts = np.arange(bit_count - 1, -1, -1, dtype=np.uint64)
    return ((values[:, None] >> shifts) & np.uint64(1)).astype(np.int8)


def levels_from_bits(bit_matrix: np.ndarray) -> np.ndarray:
    """Vectorized four-level codec: cặp bit ``(b0, b1)`` → ``10*b0 + 20*b1`` phần trăm."""
    bits = np.asarray(bit_matrix, dtype=np.int16)
    if bits.ndim != 2 or bits.shape[1] % 2:
        raise ValueError(f"bit_matrix must be (rows, even bits), got {bits.shape}.")
    pairs = bits.reshape(bits.shape[0], -1, 2)
    return 10 * pairs[:, :, 0] + 20 * pairs[:, :, 1]


def constraint_mask(
    levels: np.ndarray, constraints: Mapping[str, Any] | None
) -> np.ndarray:
    """Cùng ngữ nghĩa với ``workflow.make_four_level_feasibility`` nhưng vectorized."""
    values = dict(constraints or {})
    active = np.count_nonzero(levels, axis=1)
    total = levels.sum(axis=1).astype(float)
    mask = active >= int(values.get("min_active_candidates", 0))
    if values.get("max_active_candidates") is not None:
        mask &= active <= int(values["max_active_candidates"])
    mask &= total >= float(values.get("min_total_action_pct", 0.0))
    if values.get("max_total_action_pct") is not None:
        mask &= total <= float(values["max_total_action_pct"])
    return mask


def enumerate_state_space(
    model: QuadraticSurrogate,
    constraints: Mapping[str, Any] | None,
    *,
    chunk_size: int = 65_536,
) -> StateSpace:
    """Energy + predicate feasibility cho toàn bộ ``2^d`` trạng thái (d ≤ 24)."""
    bit_count = model.dimension
    if bit_count > MAX_ENUMERATED_BITS or bit_count % 2:
        raise ValueError(
            f"[quantum.generators] state space enumeration needs an even bit count "
            f"<= {MAX_ENUMERATED_BITS}, got {bit_count}."
        )
    size = 1 << bit_count
    energies = np.empty(size, dtype=float)
    feasible = np.empty(size, dtype=bool)
    active = np.empty(size, dtype=np.int8)
    cursor = 0
    for chunk in bitstring_chunks(bit_count, chunk_size):
        stop = cursor + len(chunk)
        levels = levels_from_bits(chunk)
        energies[cursor:stop] = model.evaluate_batch(chunk)
        feasible[cursor:stop] = constraint_mask(levels, constraints)
        active[cursor:stop] = np.count_nonzero(levels, axis=1)
        cursor = stop
    if not feasible.any():
        raise ValueError("[quantum.generators] no predicate-feasible state exists.")
    return StateSpace(bit_count, energies, feasible, active)
