# Đỗ Ngọc Tân - worker subprocess cho solve_qaoa_one_seed_fast() (xem qaoa.py).
"""Chạy `solve_qaoa_one_seed` với transpile CƯỠNG BỨC bật, trong 1 tiến trình con tách biệt.

Lý do tồn tại file này: transpile ansatz QAOA nhanh hơn nhiều (~14-100x, xem `Quantum_Reporting.md`
2026-08-15) nhưng có bug FLAKY (race condition) trong Rust core qiskit-terra 2.5.2 — thỉnh thoảng
crash (`pyo3_runtime.PanicException`, segfault) không tất định, không liên quan tên biến hay số qubit.
Chạy trong subprocess riêng cho phép `solve_qaoa_one_seed_fast()` (qaoa.py) bắt được crash đó (qua
exit code) và THỬ LẠI trong tiến trình con MỚI — không đánh đổi độ chính xác, vì công thức toán giống
hệt đường không-transpile khi không crash (đã verify khớp exact nhiều lần).

Input: đường dẫn pickle chứa `{"qp": ..., "feasibility_constraints": dict | None, "kwargs": {...}}`.
Output: pickle `QaoaSeedResult` nếu thành công. Không import module này trực tiếp trong code khác
— chỉ gọi qua `subprocess` từ `qaoa.py`.

`feasibility_constraints` (nếu khác `None`) là dict THUẦN (pickle được) mô tả ràng buộc four-level
— worker tự dựng lại predicate qua `workflow.make_four_level_feasibility(constraints)` NGAY TRONG
subprocess này, thay vì nhận một callable đã pickle sẵn (closure như
`make_four_level_feasibility()` trả về KHÔNG pickle được qua ranh giới process).
"""

from __future__ import annotations

import os
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
    kwargs = dict(payload["kwargs"])

    feasibility_constraints = payload.get("feasibility_constraints")
    if feasibility_constraints is not None:
        # Dựng lại predicate TRONG worker — không pickle closure qua ranh giới process (xem
        # docstring module + qaoa.py::solve_qaoa_one_seed_fast).
        from qshield_quantum.workflow import make_four_level_feasibility

        kwargs["feasibility"] = make_four_level_feasibility(feasibility_constraints)

    # Cưỡng bức transpile bất kể ngưỡng an toàn của qaoa.py — subprocess này CHÍNH LÀ cơ chế an
    # toàn (crash ở đây không ảnh hưởng tiến trình gọi, sẽ được retry).
    _qaoa_mod._make_transpiler = _force_transpile
    result = _qaoa_mod.solve_qaoa_one_seed(qp, **kwargs)
    Path(output_path).write_bytes(pickle.dumps(result))
    return 0


if __name__ == "__main__":
    # ⚠️ PHẢI thoát bằng `os._exit()`, KHÔNG dùng `sys.exit()`.
    #
    # Đo thật 2026-09-04: worker tính xong và ghi `output.pkl` sau ~2 GIÂY ở n=8, rồi TREO VÔ HẠN
    # trong `Py_FinalizeEx` — đúng cái bẫy đã ghi ở `cli.py::_fast_exit_if_standalone`: Rust
    # `drop_glue` của `qiskit_circuit::CircuitData` (qiskit 2.5.1) có thể không bao giờ trả về.
    # Hệ quả với `sys.exit()`: `subprocess.run(timeout=...)` bên `solve_qaoa_one_seed_fast` chờ
    # hết timeout, coi như crash, rồi RETRY — đo được `runtime=600.2s` (= đúng 3 x 200s timeout)
    # cho một phép tính 2 giây, trước khi rơi về đường chậm. Fast path khi đó chẳng những không
    # nhanh hơn mà còn đắt hơn hàng trăm lần.
    #
    # `os._exit()` bỏ qua toàn bộ finalization. An toàn ở đây vì `output.pkl` đã được ghi và
    # flush xong bên trong `main()` trước khi tới dòng này — không có buffer nào cần dọn.
    _exit_code = main(sys.argv[1], sys.argv[2])
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_exit_code)
