# Đỗ Ngọc Tân - FileBenchmarkRepository — implement BenchmarkRepository, đọc benchmark.json thật.
from __future__ import annotations

from dataclasses import dataclass

from qshield_contracts.config import Config
from qshield_contracts.enums import Stage

from qshield_api.domain.benchmark.entities import BenchmarkView
from qshield_api.infrastructure.persistence.artifact_reader import (
    build_paths,
    read_json,
)


@dataclass(frozen=True)
class FileBenchmarkRepository:
    cfg: Config

    def get_benchmark(self) -> BenchmarkView | None:
        paths = build_paths(self.cfg)
        payload = read_json(paths, Stage.SOLVE, "benchmark.json")
        if payload is None:
            return None
        return BenchmarkView(
            winning_seed=payload["winning_seed"],
            winning_bitstring=payload["winning_bitstring"],
            winning_energy=payload["winning_energy"],
            winning_is_feasible=payload["winning_is_feasible"],
            n_seeds_feasible=payload["n_seeds_feasible"],
            n_seeds_total=payload["n_seeds_total"],
            exact_best_feasible_bitstring=payload["exact_best_feasible_bitstring"],
            exact_best_feasible_energy=payload["exact_best_feasible_energy"],
            exact_evaluated_states=payload["exact_evaluated_states"],
            optimality_gap=payload["optimality_gap"],
            mean_feasibility_rate=payload["mean_feasibility_rate"],
            mean_success_prob=payload["mean_success_prob"],
            classical_bitstring=payload["classical_bitstring"],
            classical_energy=payload["classical_energy"],
            classical_gap=payload["classical_gap"],
            qaoa_beats_classical=payload["qaoa_beats_classical"],
            runtime_seconds_total=payload["runtime_seconds_total"],
            caveat=payload["caveat"],
        )
