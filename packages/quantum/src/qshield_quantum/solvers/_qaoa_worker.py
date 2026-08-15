# Đỗ Ngọc Tân - worker subprocess cho solve_qaoa_one_seed_fast() (xem qaoa.py).
"""Chạy `solve_qaoa_one_seed` với transpile CƯỠNG BỨC bật, trong 1 tiến trình con tách biệt.

Lý do tồn tại file này: transpile ansatz QAOA nhanh hơn nhiều (~14-100x, xem `Quantum_Reporting.md`
2026-08-15) nhưng có bug FLAKY (race condition) trong Rust core qiskit-terra 2.5.2 — thỉnh thoảng
crash (`pyo3_runtime.PanicException`, segfault) không tất định, không liên quan tên biến hay số qubit.
Chạy trong subprocess riêng cho phép `solve_qaoa_one_seed_fast()` (qaoa.py) bắt được crash đó (qua
exit code) và THỬ LẠI trong tiến trình con MỚI — không đánh đổi độ chính xác, vì công thức toán giống
hệt đường không-transpile khi không crash (đã verify khớp exact nhiều lần).

Input: đường dẫn pickle chứa `(qp, kwargs)`. Output: pickle `QaoaSeedResult` nếu thành công.
Không import module này trực tiếp trong code khác — chỉ gọi qua `subprocess` từ `qaoa.py`.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import qshield_quantum.solvers.qaoa as _qaoa_mod


def _force_transpile(_num_qubits: int):
    return generate_preset_pass_manager(
        optimization_level=1, basis_gates=["rz", "sx", "x", "cx"]
    )


def main(input_path: str, output_path: str) -> int:
    payload = pickle.loads(Path(input_path).read_bytes())
    qp = payload["qp"]
    kwargs = payload["kwargs"]

    # Cưỡng bức transpile bất kể ngưỡng an toàn của qaoa.py — subprocess này CHÍNH LÀ cơ chế an
    # toàn (crash ở đây không ảnh hưởng tiến trình gọi, sẽ được retry).
    _qaoa_mod._make_transpiler = _force_transpile
    result = _qaoa_mod.solve_qaoa_one_seed(qp, **kwargs)
    Path(output_path).write_bytes(pickle.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
