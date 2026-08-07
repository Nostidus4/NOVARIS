# Đỗ Ngọc Tân - use case: đọc benchmark.json. Trả None nếu chưa chạy solve() lần nào — router 404.
from __future__ import annotations

from qshield_api.application.benchmark.dto import BenchmarkDTO
from qshield_api.domain.benchmark.repository import BenchmarkRepository


def get_benchmark(repo: BenchmarkRepository) -> BenchmarkDTO | None:
    view = repo.get_benchmark()
    if view is None:
        return None
    return BenchmarkDTO(
        winning_seed=view.winning_seed,
        winning_bitstring=view.winning_bitstring,
        winning_energy=view.winning_energy,
        winning_is_feasible=view.winning_is_feasible,
        n_seeds_feasible=view.n_seeds_feasible,
        n_seeds_total=view.n_seeds_total,
        exact_best_feasible_bitstring=view.exact_best_feasible_bitstring,
        exact_best_feasible_energy=view.exact_best_feasible_energy,
        exact_evaluated_states=view.exact_evaluated_states,
        optimality_gap=view.optimality_gap,
        mean_feasibility_rate=view.mean_feasibility_rate,
        mean_success_prob=view.mean_success_prob,
        classical_bitstring=view.classical_bitstring,
        classical_energy=view.classical_energy,
        classical_gap=view.classical_gap,
        qaoa_beats_classical=view.qaoa_beats_classical,
        runtime_seconds_total=view.runtime_seconds_total,
        caveat=view.caveat,
    )
