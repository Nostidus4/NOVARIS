# Đỗ Ngọc Tân - QuadraticProgram → QuadraticProgramToQubo.
"""Dựng `QuadraticProgram` (qiskit_optimization) từ đúng `(Q, linear, constant)` của
`formulation/qubo.py` — không tính lại từ `g/C/c` để tránh hai đường công thức lệch nhau.

⚠️ Quy ước hệ số quadratic của `qiskit_optimization` KHÁC quy ước ma trận đối xứng `z'Qz`:
`qp.minimize(quadratic={(i,j): v})` cho `v * z_i * z_j` ĐÚNG MỘT LẦN (không nhân đôi), còn
`z'Qz` với `Q` đối xứng đầy đủ cộng cả `Q[i,j]` lẫn `Q[j,i]`. Nên hệ số truyền vào `quadratic`
phải là `Q[i,j] + Q[j,i] = 2*Q[i,j]` (đã verify bằng `qp.objective.evaluate`, xem `plan.md`).
Sai chỗ này là lỗi âm thầm — `verify/consistency.py` sẽ bắt được nếu quên.

`QuadraticProgramToQubo` không được dùng để TỰ THÊM constraint `sum(z)=K` — penalty đã ép sẵn
trong `objective.py`/`qubo.py`. Nếu thêm constraint cứng ở đây, converter sẽ tự sinh một penalty
KHÁC, lệch với `formulation/qubo.py` — vi phạm CLAUDE.md quy tắc 14 (một ground truth duy nhất).
"""

from __future__ import annotations

import numpy as np
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo


def build_quadratic_program(
    Q: np.ndarray, linear: np.ndarray, constant: float, *, ticker_order: list[str]
) -> QuadraticProgram:
    """8 biến nhị phân, đặt tên theo `ticker_order` (khớp `configs/base.yaml`) để dễ trace lúc
    debug — KHÔNG dùng để decode (đó là việc của `decode.py`, dựa trên index, không dựa trên tên
    biến qiskit trả về)."""
    n = len(ticker_order)
    qp = QuadraticProgram("qshield_qubo")
    for ticker in ticker_order:
        qp.binary_var(name=ticker)

    quadratic: dict[tuple[str, str], float] = {}
    linear_with_diag = linear.copy()
    for i in range(n):
        linear_with_diag[i] += Q[i, i]  # z_i^2 = z_i — đường chéo gộp vào tuyến tính
        for j in range(i + 1, n):
            coeff = Q[i, j] + Q[j, i]
            if coeff != 0:
                quadratic[(ticker_order[i], ticker_order[j])] = coeff

    qp.minimize(constant=constant, linear=list(linear_with_diag), quadratic=quadratic)
    return qp


def to_qubo(qp: QuadraticProgram) -> QuadraticProgram:
    """`QuadraticProgramToQubo` — với `qp` đã là 8 biến nhị phân không constraint, converter này
    thực chất không đổi gì (không có constraint để chuyển thành penalty), nhưng vẫn chạy qua đúng
    API chuẩn để `verify/consistency.py` kiểm tra được đường convert thật của qiskit, không phải
    đường tắt."""
    converter = QuadraticProgramToQubo()
    return converter.convert(qp)
