# Đỗ Ngọc Tân - BenchmarkView — đọc workflow_benchmark.json (ưu tiên) hoặc benchmark.json legacy.
"""Không tự tính lại benchmark — chỉ mô tả artifact packages đã ghi. `qaoa_beats_classical=False`
là giá trị HỢP LỆ (CLAUDE.md quy tắc 18).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkView:
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
    # workflow_update provenance (optional on legacy benchmark.json)
    source_artifact: str
    profile_id: str | None
    requested_solver: str | None
    actual_solver: str | None
    fallback_reason: str | None
