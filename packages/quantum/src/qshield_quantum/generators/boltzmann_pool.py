# Đỗ Ngọc Tân - control Boltzmann khớp energy với QAOA: tách "tập trung vùng energy thấp" khỏi QAOA.
"""Boltzmann energy-matched pool.

Nếu QAOA chỉ đơn giản dồn xác suất vào vùng energy thấp, một sampler cổ điển
``p(x) ∝ exp(-β E(x))`` với β chọn sao cho ``E_β[E]`` bằng energy trung bình của phân phối QAOA
sẽ tạo pool tương đương. QAOA chỉ có cấu trúc riêng nếu nó vượt control này.

Lấy B trạng thái KHÔNG hoàn lại bằng Gumbel-top-k (tương đương rút tuần tự theo trọng số).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qshield_quantum.generators.common import Proposal, StateSpace

_BETA_ITERATIONS = 200


@dataclass(frozen=True)
class BoltzmannFit:
    beta: float
    target_mean_energy: float
    achieved_mean_energy: float
    uniform_mean_energy: float
    status: str  # MATCHED | TARGET_ABOVE_UNIFORM | TARGET_BELOW_MINIMUM


def _mean_energy(energies: np.ndarray, beta: float) -> float:
    shifted = energies - energies.min()
    logits = -beta * shifted
    logits -= logits.max()
    weights = np.exp(logits)
    return float((weights * energies).sum() / weights.sum())


def fit_beta(energies: np.ndarray, target_mean_energy: float) -> BoltzmannFit:
    values = np.asarray(energies, dtype=float)
    uniform = float(values.mean())
    minimum = float(values.min())
    scale = float(values.std()) or 1.0
    if target_mean_energy >= uniform:
        return BoltzmannFit(
            0.0, target_mean_energy, uniform, uniform, "TARGET_ABOVE_UNIFORM"
        )
    low, high = 0.0, 1.0 / scale
    while _mean_energy(values, high) > target_mean_energy and high < 1e12 / scale:
        high *= 2.0
    if _mean_energy(values, high) > target_mean_energy:
        return BoltzmannFit(
            high,
            target_mean_energy,
            _mean_energy(values, high),
            uniform,
            "TARGET_BELOW_MINIMUM",
        )
    for _ in range(_BETA_ITERATIONS):
        middle = 0.5 * (low + high)
        if _mean_energy(values, middle) > target_mean_energy:
            low = middle
        else:
            high = middle
    beta = 0.5 * (low + high)
    status = "MATCHED" if target_mean_energy > minimum else "TARGET_BELOW_MINIMUM"
    return BoltzmannFit(
        beta, target_mean_energy, _mean_energy(values, beta), uniform, status
    )


def boltzmann_pool(
    space: StateSpace, *, budget: int, seed: int, target_mean_energy: float
) -> tuple[list[Proposal], BoltzmannFit]:
    if budget < 0:
        raise ValueError(f"budget must be non-negative, got {budget}.")
    feasible = np.flatnonzero(space.predicate_feasible)
    energies = space.energies[feasible]
    fit = fit_beta(energies, target_mean_energy)
    rng = np.random.default_rng(seed)
    log_weights = -fit.beta * (energies - energies.min())
    keys = log_weights + rng.gumbel(size=len(feasible))
    count = min(budget, len(feasible))
    top = np.argpartition(-keys, count - 1)[:count] if count else np.empty(0, dtype=int)
    ordered = top[np.argsort(-keys[top], kind="stable")]
    proposals = [
        space.proposal(
            feasible[position],
            source_method="boltzmann",
            source_rank=rank,
            source_seed=seed,
        )
        for rank, position in enumerate(ordered, start=1)
    ]
    return proposals, fit
