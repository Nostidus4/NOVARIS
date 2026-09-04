# Đỗ Ngọc Tân - StatevectorSampler — môi trường thực thi DUY NHẤT (không có QPU thật).
"""`StatevectorSampler` — môi trường mô phỏng cho CẢ đường legacy 8 qubit LẪN đường four-level
20 qubit hiện tại. `backends/hardware.py` để trống có chủ đích (CLAUDE.md: ngoài phạm vi).

Chi phí KHÔNG phải do statevector: 2^20 biên độ complex128 chỉ 16 MB. Đo thật 2026-09-04 ở
n=20 cho peak RSS ~9,1 GiB — chi phối bởi biểu diễn MẠCH đã transpile (QUBO dày có O(n²) cổng
hai qubit), không phải vector trạng thái. Ước lượng giới hạn theo cỡ statevector sẽ cho ra con
số lạc quan sai vài bậc độ lớn (xem `reponse.md` F.2).
"""

from __future__ import annotations

from qiskit.primitives import StatevectorSampler


def make_sampler(*, shots: int, seed: int) -> StatevectorSampler:
    return StatevectorSampler(default_shots=shots, seed=seed)
