# Đỗ Ngọc Tân - BenchmarkDTO.
from __future__ import annotations

from pydantic import BaseModel


class BenchmarkDTO(BaseModel):
    winning_seed: int | None
    winning_bitstring: str
    winning_energy: float
    winning_is_feasible: bool
    n_seeds_feasible: int
    n_seeds_total: int
    exact_best_feasible_bitstring: str
    exact_best_feasible_energy: float
    exact_evaluated_states: int
    optimality_gap: float | None
    mean_feasibility_rate: float | None
    mean_success_prob: float | None
    classical_bitstring: str
    classical_energy: float
    classical_gap: float | None
    qaoa_beats_classical: bool
    runtime_seconds_total: float
    caveat: str
    source_artifact: str
    profile_id: str | None = None
    requested_solver: str | None = None
    actual_solver: str | None = None
    fallback_reason: str | None = None
