# Đỗ Ngọc Tân - BenchmarkView — đọc lại benchmark.json (exact vs QAOA vs classical).
"""Không tự tính lại benchmark — chỉ mô tả hình dạng dữ liệu `qshield_quantum.benchmark.
build_benchmark` đã ghi ra đĩa. `qaoa_beats_classical=False` là giá trị HỢP LỆ (CLAUDE.md quy tắc
18 — không tuyên bố quantum advantage khi không có), domain không được diễn giải lại giá trị này.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkView:
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
