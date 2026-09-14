# Đỗ Ngọc Tân - random baseline: uniform và stratified theo số mã active, trên cùng feasible domain.
"""Random matched pools — kiểm soát giả thuyết "chỉ là có thêm nhiều điểm bắt đầu".

Lấy mẫu KHÔNG hoàn lại trên đúng predicate-feasible domain mà QAOA dùng, seed đăng ký trước.
"""

from __future__ import annotations

import numpy as np

from qshield_quantum.generators.common import Proposal, StateSpace


def uniform_pool(space: StateSpace, *, budget: int, seed: int) -> list[Proposal]:
    if budget < 0:
        raise ValueError(f"budget must be non-negative, got {budget}.")
    feasible = np.flatnonzero(space.predicate_feasible)
    rng = np.random.default_rng(seed)
    chosen = rng.choice(feasible, size=min(budget, len(feasible)), replace=False)
    return [
        space.proposal(
            index, source_method="random_uniform", source_rank=rank, source_seed=seed
        )
        for rank, index in enumerate(chosen, start=1)
    ]


def stratified_pool(space: StateSpace, *, budget: int, seed: int) -> list[Proposal]:
    """Round-robin theo số mã active (0..M), uniform trong từng tầng."""
    if budget < 0:
        raise ValueError(f"budget must be non-negative, got {budget}.")
    rng = np.random.default_rng(seed)
    strata: list[list[int]] = []
    for active in range(int(space.active_counts.max()) + 1):
        members = np.flatnonzero(
            space.predicate_feasible & (space.active_counts == active)
        )
        if len(members):
            strata.append(rng.permutation(members).tolist())
    chosen: list[int] = []
    while len(chosen) < budget and any(strata):
        for stratum in strata:
            if stratum and len(chosen) < budget:
                chosen.append(stratum.pop())
    return [
        space.proposal(
            index, source_method="random_stratified", source_rank=rank, source_seed=seed
        )
        for rank, index in enumerate(chosen, start=1)
    ]
