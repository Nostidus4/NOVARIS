# Đỗ Ngọc Tân - duyệt đủ 2^8 = 256 bitstring — ground truth để chấm QAOA, không được bỏ để tiết kiệm thời gian.
"""Exact solver — duyệt ĐỦ 2⁸=256 bitstring bằng `objective.py` trực tiếp (CLAUDE.md quy tắc 16:
"thước đo, không phải đối thủ" — không qua QUBO convert, đây là ground truth độc lập).

Báo cáo cả `best_feasible` (Σz=K — dùng làm optimum thật) và `best_overall` (kể cả infeasible —
nếu một bitstring infeasible thắng thì `penalty P` chưa đủ lớn, đúng lỗi hay gặp đã ghi trong
`docs/runbook/troubleshooting.md` §4: "QAOA luôn trả bitstring vi phạm K → penalty P quá nhỏ").
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qshield_quantum.formulation.objective import objective_batch
from qshield_quantum.verify.consistency import all_bitstrings


@dataclass(frozen=True)
class ExactResult:
    best_feasible_bitstring: str
    best_feasible_energy: float
    best_overall_bitstring: str
    best_overall_energy: float
    all_energies: dict[str, float]  # toàn bộ 256, dùng cho benchmark (percentile, gap)
    evaluated_states: int


def _to_bitstring(z: np.ndarray) -> str:
    return "".join(str(int(b)) for b in z)


def solve_exact(
    g: np.ndarray,
    C: np.ndarray,
    c: np.ndarray,
    *,
    lambda_1: float,
    lambda_2: float,
    penalty: float,
    k_actions: int,
) -> ExactResult:
    n = g.shape[0]
    Z = all_bitstrings(n)
    energies = objective_batch(
        Z,
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )
    all_energies = {_to_bitstring(Z[i]): float(energies[i]) for i in range(len(Z))}

    feasible_mask = Z.sum(axis=1) == k_actions
    if not feasible_mask.any():
        raise ValueError(
            f"Không có bitstring feasible nào (Σz={k_actions}) trong {2**n} tổ hợp — "
            "kiểm tra lại k_actions/n."
        )
    feasible_idx = np.where(feasible_mask)[0]
    best_feasible_local = feasible_idx[np.argmin(energies[feasible_idx])]
    best_overall_idx = int(np.argmin(energies))

    return ExactResult(
        best_feasible_bitstring=_to_bitstring(Z[best_feasible_local]),
        best_feasible_energy=float(energies[best_feasible_local]),
        best_overall_bitstring=_to_bitstring(Z[best_overall_idx]),
        best_overall_energy=float(energies[best_overall_idx]),
        all_energies=all_energies,
        evaluated_states=len(Z),
    )
