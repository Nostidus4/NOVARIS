# Benchmark repository reads workflow_update artifacts produced by packages.
from __future__ import annotations

from qshield_api.domain.benchmark.entities import BenchmarkView
from qshield_api.infrastructure.persistence.benchmark_repository_impl import (
    _view_from_workflow,
)


def test_view_from_workflow_benchmark_payload() -> None:
    view = _view_from_workflow(
        {
            "winning_seed": None,
            "winning_bitstring": "11111111111111111111",
            "winning_energy": 0.62,
            "winning_is_feasible": True,
            "n_seeds_feasible": 0,
            "n_seeds_total": 0,
            "exact_best_bitstring": "11111111111111111111",
            "exact_best_energy": 0.62,
            "exact_evaluated_states": 1_048_576,
            "optimality_gap": None,
            "mean_feasibility_rate": None,
            "mean_success_prob": None,
            "classical_bitstring": "11111111111111111111",
            "classical_energy": 0.62,
            "classical_gap": 0.0,
            "qaoa_beats_classical": False,
            "runtime_seconds": {"exact": 39.5, "qaoa": 0.0, "classical": 0.5},
            "caveat": "NON_FINAL exact fallback",
            "profile_id": "workflow_update_downstream",
            "requested_solver": "qaoa",
            "actual_solver": "exact",
            "fallback_reason": "QAOA skipped/timeout in NON_FINAL_CONFIG",
        }
    )
    assert isinstance(view, BenchmarkView)
    assert view.source_artifact == "workflow_benchmark.json"
    assert view.actual_solver == "exact"
    assert view.winning_seed is None
    assert view.runtime_seconds_total == 40.0
    assert view.qaoa_beats_classical is False
