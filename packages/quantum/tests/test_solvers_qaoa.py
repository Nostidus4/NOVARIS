# Đỗ Ngọc Tân - solve_qaoa: chạy đủ >=10 seed (không cherry-pick), bitstring đúng độ dài.
import json
import subprocess
import sys
import textwrap

import pytest
from qshield_quantum.formulation.qiskit_program import build_quadratic_program
from qshield_quantum.formulation.qubo import build_qubo
from qshield_quantum.solvers.qaoa import solve_qaoa


def test_solve_qaoa_rejects_fewer_than_10_seeds() -> None:
    import numpy as np

    n = 3
    g = np.ones(n)
    C = np.zeros((n, n))
    c = np.zeros(n)
    Q, linear, constant = build_qubo(
        g, C, c, lambda_1=1.0, lambda_2=1.0, penalty=5.0, k_actions=1
    )
    qp = build_quadratic_program(Q, linear, constant, ticker_order=["A", "B", "C"])

    with pytest.raises(ValueError, match="tối thiểu 10"):
        solve_qaoa(qp, seeds=[1, 2, 3], shots=32, maxiter=5, k_actions=1)


# Chạy qua SUBPROCESS + os._exit(0) riêng, không gọi solve_qaoa trực tiếp trong tiến trình pytest.
#
# ⚠️ Lý do (đã verify bằng `sample <pid>`, không suy đoán): qiskit 2.5.1 (Rust `CircuitData`
# trong `_accelerate.abi3.so`) có thể khiến `Py_FinalizeEx` treo VÔ HẠN sau khi tạo/hủy nhiều đối
# tượng circuit qua 10 seed QAOA liên tiếp. `gc.disable()` trong `solve_qaoa` (xem
# `solvers/qaoa.py`) giảm tần suất nhưng không loại bỏ hoàn toàn — cách duy nhất verify được là
# tránh treo tuyệt đối là `os._exit()`, không dùng được nếu gọi trực tiếp trong tiến trình pytest
# (sẽ không có cách nào assert được kết quả sau khi tiến trình đã bị hạ). Cô lập trong subprocess
# + `timeout=` để: (1) vẫn assert được kết quả qua JSON in ra stdout, (2) không có rủi ro treo
# chính pytest nếu máy chạy CI dính lại bug này.
_SCRIPT = textwrap.dedent(
    """
    import json, os, sys
    import numpy as np
    from qshield_quantum.formulation.qiskit_program import build_quadratic_program
    from qshield_quantum.formulation.qubo import build_qubo
    from qshield_quantum.solvers.qaoa import solve_qaoa

    n = 3
    g = np.array([1.0, 5.0, 2.0])
    C = np.zeros((n, n))
    c = np.zeros(n)
    Q, linear, constant = build_qubo(g, C, c, lambda_1=1.0, lambda_2=1.0, penalty=20.0, k_actions=1)
    qp = build_quadratic_program(Q, linear, constant, ticker_order=["A", "B", "C"])

    seeds = list(range(10))
    results = solve_qaoa(qp, seeds=seeds, shots=64, maxiter=10, k_actions=1, reference_bitstring="010")

    payload = {
        seed: {
            "bitstring": r.bitstring,
            "feasibility_rate": r.feasibility_rate,
            "success_prob": r.success_prob,
        }
        for seed, r in results.items()
    }
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()
    os._exit(0)
    """
)


@pytest.mark.slow
def test_solve_qaoa_runs_all_registered_seeds() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    results = json.loads(result.stdout)
    seeds = list(range(10))
    assert {int(s) for s in results} == set(seeds)
    for payload in results.values():
        assert len(payload["bitstring"]) == 3
        assert 0.0 <= payload["feasibility_rate"] <= 1.0
        assert 0.0 <= payload["success_prob"] <= 1.0
