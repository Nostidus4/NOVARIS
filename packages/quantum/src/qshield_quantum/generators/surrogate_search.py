# Đỗ Ngọc Tân - classical control cùng thông tin với QAOA: local search trên QUBO surrogate.
"""Multi-start best-improvement one-bit local search trên surrogate energy.

Control công bằng nhất về THÔNG TIN: chỉ thấy QUBO + predicate, giống QAOA. Mọi trạng thái được
thăm (điểm xuất phát + từng bước chấp nhận) đi vào pool theo thứ tự thăm lần đầu cho tới khi đủ B
trạng thái unique. Không thêm all-zeros/all-ones làm điểm xuất phát (tránh "thắng nhờ khởi tạo",
xem ghi chú ``benchmark.coordinate_descent_classical``).
"""

from __future__ import annotations

import numpy as np

from qshield_quantum.generators.common import Proposal, StateSpace


def surrogate_local_search_pool(
    space: StateSpace, *, budget: int, seed: int, max_restarts: int = 100_000
) -> tuple[list[Proposal], dict[str, int]]:
    if budget < 0:
        raise ValueError(f"budget must be non-negative, got {budget}.")
    rng = np.random.default_rng(seed)
    feasible = np.flatnonzero(space.predicate_feasible)
    target = min(budget, len(feasible))
    flips = [1 << (space.bit_count - 1 - bit) for bit in range(space.bit_count)]
    visited: dict[int, None] = {}
    restarts = 0
    local_minima = 0
    while len(visited) < target and restarts < max_restarts:
        restarts += 1
        current = int(rng.choice(feasible))
        visited.setdefault(current, None)
        while len(visited) < target:
            neighbours = [current ^ flip for flip in flips]
            best = min(
                (
                    (float(space.energies[item]), item)
                    for item in neighbours
                    if space.predicate_feasible[item]
                ),
                default=None,
            )
            if best is None or best[0] >= float(space.energies[current]) - 1e-12:
                local_minima += 1
                break
            current = best[1]
            visited.setdefault(current, None)
    proposals = [
        space.proposal(
            index,
            source_method="classical_surrogate",
            source_rank=rank,
            source_seed=seed,
        )
        for rank, index in enumerate(visited, start=1)
    ]
    return proposals, {"restarts": restarts, "local_minima_reached": local_minima}
