# Đỗ Ngọc Tân - P·(Σz − K)² — ép đúng K=3 hành động được chọn.
"""Khai triển penalty `P·(Σz − K)²` thành dạng QUBO (ma trận vuông + tuyến tính + hằng số), và đề
xuất một giá trị `P` đủ lớn khi config chưa khóa (`configs/quantum.yaml: penalty.P` hiện đang
`null` — TBD-006 trong `docs/product/mvp_scope.md` §23).

Dùng chung bởi `formulation/qubo.py` và `formulation/qiskit_program.py` để đảm bảo cả hai đường
convert cho ra đúng MỘT QUBO (không tự thêm penalty khác nhau ở hai chỗ).
"""

from __future__ import annotations

import numpy as np


def penalty_terms(
    n: int, k_actions: int, penalty: float
) -> tuple[np.ndarray, np.ndarray, float]:
    """`P·(Σz−K)² = P·(1−2K)·Σz + 2P·Σ_{i<j}(z_i z_j) + P·K²` (vì `z_i² = z_i` khi z nhị phân).

    Trả `(Q, linear, constant)` sao cho `z'Qz + linear'z + constant == penalty*(sum(z)-k_actions)**2`
    với `Q` đối xứng, đường chéo = 0 (phần `z_i²` đã gộp vào `linear`).
    """
    Q = penalty * (np.ones((n, n)) - np.eye(n))
    linear = penalty * (1 - 2 * k_actions) * np.ones(n)
    constant = penalty * k_actions**2
    return Q, linear, constant


def suggest_penalty(
    g: np.ndarray,
    C: np.ndarray,
    c: np.ndarray,
    *,
    lambda_1: float,
    lambda_2: float,
    margin: float = 2.0,
) -> float:
    """Đề xuất `P` đủ lớn để penalty luôn thắng phần còn lại của objective — theo nguyên tắc
    CLAUDE.md ("P phải đủ lớn so với λ1, λ2"), không phải số đoán mò.

    Chặn trên của `|-g'z + λ1*z'Cz + λ2*c'z|` trên MỌI z nhị phân là
    `sum(|g|) + λ1*sum(|C|) + λ2*sum(|c|)` (trường hợp xấu nhất z toàn 1). Lệch K đi 1 đơn vị làm
    penalty tăng ít nhất `P` — chọn `P = margin * chặn_trên` để chắc chắn không bitstring
    infeasible nào thắng được bitstring feasible tốt nhất. Kết quả PROVISIONAL, đánh dấu
    `NON_BASELINE_RUN` khi dùng (xem `plan.md` câu hỏi 3) — chờ Phúc/Ngọc duyệt số chính thức.
    """
    bound = np.abs(g).sum() + lambda_1 * np.abs(C).sum() + lambda_2 * np.abs(c).sum()
    return float(margin * max(bound, 1e-9))
