# Đỗ Ngọc Tân - BenchmarkDTO.
from __future__ import annotations

from pydantic import BaseModel


class BenchmarkDTO(BaseModel):
    winning_seed: int
    winning_bitstring: str
    winning_energy: float
    winning_is_feasible: bool
    n_seeds_feasible: int
    n_seeds_total: int
    exact_best_feasible_bitstring: str
    exact_best_feasible_energy: float
    exact_evaluated_states: int
    optimality_gap: float
    mean_feasibility_rate: float
    mean_success_prob: float
    classical_bitstring: str
    classical_energy: float
    classical_gap: float
    qaoa_beats_classical: bool
    runtime_seconds_total: float
    caveat: str
