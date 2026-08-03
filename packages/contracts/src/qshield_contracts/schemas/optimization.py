# Đỗ Ngọc Tân - schema qaoa_result.json: bitstring thắng + metrics benchmark (exact/QAOA/classical).
"""Schema `qaoa_result.json` — SPEC ĐI TRƯỚC, `packages/quantum/` còn là scaffold.

`qaoa_energy_by_seed` bắt buộc ≥ 10 seed (CLAUDE.md: "Không bỏ để tiết kiệm thời gian", giới hạn
mục 4 docs/limitations.md: "không được cherry-pick seed tốt nhất"). `true_cvar_before`/`after` PHẢI
đến từ `qshield_risk.evaluate` (chấm lại bằng CVaR thật), không phải suy ra từ objective value
(CLAUDE.md quy tắc 17).
"""

from __future__ import annotations

from dataclasses import dataclass

from qshield_contracts.enums import SolverKind

_MIN_SEEDS = 10


@dataclass(frozen=True)
class QaoaResult:
    bitstring: str  # 8 bit, đúng K=3 bit = 1 (phạm vi đã khóa)
    k_actions: int
    chosen_actions: list[int]
    requested_solver: SolverKind
    actual_solver: SolverKind  # có thể khác requested nếu QAOA timeout/fail và fallback
    exact_energy: float
    qaoa_energy_by_seed: dict[int, float]  # seed -> energy, KHÔNG chỉ seed tốt nhất
    optimality_gap: float
    feasibility_rate: float
    true_cvar_before: float  # từ qshield_risk.evaluate — KHÔNG phải objective value
    true_cvar_after: float
    shots: int
    backend: str
    runtime_seconds: float


def validate_qaoa_result(result: QaoaResult) -> None:
    """Raise `ValueError` nếu bitstring sai số bit K, hoặc chạy dưới số seed tối thiểu bắt buộc."""
    ones = result.bitstring.count("1")
    if ones != result.k_actions:
        raise ValueError(
            f"bitstring '{result.bitstring}' có {ones} bit=1, khác k_actions={result.k_actions}."
        )
    if len(result.qaoa_energy_by_seed) < _MIN_SEEDS:
        raise ValueError(
            f"qaoa_energy_by_seed chỉ có {len(result.qaoa_energy_by_seed)} seed, "
            f"cần tối thiểu {_MIN_SEEDS} (docs/limitations.md §4: không cherry-pick seed)."
        )
