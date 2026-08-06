# Đỗ Ngọc Tân - dựng ma trận Q từ g, C, c.
"""Dựng `(Q, linear, constant)` sao cho `z'Qz + linear'z + constant == objective.objective(z, ...)`
với MỌI z nhị phân — `verify/consistency.py` test bằng cách so trên toàn bộ 256 bitstring, không
phải vài mẫu.
"""

from __future__ import annotations

import numpy as np

from qshield_quantum.formulation.penalty import penalty_terms


def build_qubo(
    g: np.ndarray,
    C: np.ndarray,
    c: np.ndarray,
    *,
    lambda_1: float,
    lambda_2: float,
    penalty: float,
    k_actions: int,
) -> tuple[np.ndarray, np.ndarray, float]:
    """`C` phải ĐÃ ĐỐI XỨNG HÓA trước khi gọi (xem `fixtures.py`) — `z'Qz` dùng ma trận đầy đủ,
    không phải tam giác trên, nên `Q_interaction = lambda_1 * C` tái tạo đúng `lambda_1*z'Cz` mà
    không cần convert gì thêm.
    """
    n = g.shape[0]
    Q_interaction = lambda_1 * C
    linear_objective = -g + lambda_2 * c

    Q_penalty, linear_penalty, constant_penalty = penalty_terms(n, k_actions, penalty)

    Q = Q_interaction + Q_penalty
    linear = linear_objective + linear_penalty
    constant = constant_penalty
    return Q, linear, constant
