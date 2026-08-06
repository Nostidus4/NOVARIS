# Đỗ Ngọc Tân - f(z) NumPy thuần — ĐÂY LÀ GROUND TRUTH. QuadraticProgram và QUBO sau convert phải khớp với hàm này.
"""Ground truth của bài toán tối ưu: `f(z) = -g'z + λ1·z'Cz + λ2·c'z + P·(Σz − K)²`.

Phạm vi đã khóa (CLAUDE.md, `docs/limitations.md` §1): 8 mã, K=3, MỘT mức hành động duy nhất (giảm
20% vị thế). `z_i ∈ {0,1}` là "có chọn hành động i hay không" — không phải mã hóa nhiều mức hành
động như thiết kế PSS gốc (xem `plan.md` §0).

`formulation/qubo.py` và `formulation/qiskit_program.py` phải cho energy khớp hàm này TUYỆT ĐỐI
trên toàn bộ 2⁸=256 bitstring — `verify/consistency.py` kiểm tra việc đó trước khi tin bất kỳ kết
quả QAOA nào (CLAUDE.md quy tắc 15).
"""

from __future__ import annotations

import numpy as np


def objective(
    z: np.ndarray,
    g: np.ndarray,
    C: np.ndarray,
    c: np.ndarray,
    *,
    lambda_1: float,
    lambda_2: float,
    penalty: float,
    k_actions: int,
) -> float:
    """`f(z) = -g'z + lambda_1*z'Cz + lambda_2*c'z + penalty*(sum(z) - k_actions)**2`.

    `z`: (n,) 0/1. `g`: (n,) mức giảm CVaR mỗi hành động một mình. `C`: (n,n) ma trận tương tác cặp
    ĐÃ ĐỐI XỨNG HÓA (caller chịu trách nhiệm, xem `fixtures.py`). `c`: (n,) chi phí giao dịch. Trả
    về energy — thấp hơn = tốt hơn (cực tiểu hóa `-g'z` nghĩa là cực đại hóa lợi ích giảm CVaR).
    """
    z = np.asarray(z, dtype=float)
    linear_term = -g @ z
    interaction_term = lambda_1 * (z @ C @ z)
    cost_term = lambda_2 * (c @ z)
    penalty_term = penalty * (z.sum() - k_actions) ** 2
    return float(linear_term + interaction_term + cost_term + penalty_term)


def objective_batch(
    Z: np.ndarray,
    g: np.ndarray,
    C: np.ndarray,
    c: np.ndarray,
    *,
    lambda_1: float,
    lambda_2: float,
    penalty: float,
    k_actions: int,
) -> np.ndarray:
    """Bản vector hóa của `objective` trên nhiều bitstring `Z` (M, n) cùng lúc — dùng cho
    `solvers/exact.py` (duyệt 256 bitstring, tính một lần thay vì loop Python 256 lần)."""
    Z = np.asarray(Z, dtype=float)
    linear_term = -Z @ g
    interaction_term = lambda_1 * np.einsum("mi,ij,mj->m", Z, C, Z)
    cost_term = lambda_2 * (Z @ c)
    penalty_term = penalty * (Z.sum(axis=1) - k_actions) ** 2
    return linear_term + interaction_term + cost_term + penalty_term
