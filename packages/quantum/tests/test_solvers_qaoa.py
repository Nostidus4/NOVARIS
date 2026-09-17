# Đỗ Ngọc Tân - solve_qaoa: chạy đủ >=10 seed (không cherry-pick), bitstring đúng độ dài.
import json
import subprocess
import sys
import textwrap

import numpy as np
import pytest
from qshield_quantum.formulation.qiskit_program import build_quadratic_program
from qshield_quantum.formulation.qubo import build_qubo
from qshield_quantum.solvers.qaoa import (
    solve_qaoa,
    solve_qaoa_one_seed,
    solve_qaoa_one_seed_fast,
)
from qshield_quantum.workflow import make_four_level_feasibility


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


@pytest.mark.slow
def test_qaoa_one_seed_fast_always_feasible_matches_plain_path() -> None:
    """P1-1: `always_feasible=True` (đường pickle-safe khi `quantum_constraints` rỗng) phải chạy
    xong qua subprocess (transpile cưỡng bức) và cho kết quả khớp `solve_qaoa_one_seed` thường
    chạy trực tiếp trong tiến trình (cùng seed, cùng công thức toán — chỉ khác cách mô phỏng
    circuit, xem `qaoa.py::solve_qaoa_one_seed_fast` docstring)."""
    n = 4
    Q = np.zeros((n, n))
    linear = np.array([-1.0, -2.0, -3.0, -4.0])
    qp = build_quadratic_program(Q, linear, 0.0, ticker_order=["A0", "A1", "B0", "B1"])

    expected = solve_qaoa_one_seed(
        qp, seed=7, shots=64, maxiter=5, feasibility=lambda _bits: True, reps=1
    )
    actual = solve_qaoa_one_seed_fast(
        qp,
        seed=7,
        shots=64,
        maxiter=5,
        always_feasible=True,
        reps=1,
        max_retries=1,
        subprocess_timeout_seconds=60.0,
    )
    assert actual.bitstring == expected.bitstring
    assert actual.feasible is True


@pytest.mark.slow
def test_qaoa_worker_rebuilds_four_level_predicate_from_constraints_dict() -> None:
    """P1-1: khi `feasibility_constraints` (dict thuần) được truyền, `_qaoa_worker.py` phải tự
    dựng lại predicate qua `make_four_level_feasibility(constraints)` NGAY TRONG subprocess và
    cho `feasible`/`bitstring` khớp hệt đường `solve_qaoa_one_seed` thường chạy với CHÍNH predicate
    đó trong tiến trình hiện tại — chứng minh worker không âm thầm bỏ qua ràng buộc."""
    n = 4  # 2 candidates x 2 bit/candidate — đúng four-level encoding
    Q = np.zeros((n, n))
    linear = np.array([-1.0, -2.0, -3.0, -4.0])
    qp = build_quadratic_program(
        Q, linear, 0.0, ticker_order=["AAA__b0", "AAA__b1", "BBB__b0", "BBB__b1"]
    )
    constraints = {"max_active_candidates": 1}
    predicate = make_four_level_feasibility(constraints)

    expected = solve_qaoa_one_seed(
        qp, seed=11, shots=64, maxiter=5, feasibility=predicate, reps=1
    )
    actual = solve_qaoa_one_seed_fast(
        qp,
        seed=11,
        shots=64,
        maxiter=5,
        feasibility_constraints=constraints,
        reps=1,
        max_retries=1,
        subprocess_timeout_seconds=60.0,
    )
    assert actual.bitstring == expected.bitstring
    assert actual.feasible == expected.feasible
    # Đối chiếu độc lập với predicate thật trên chính bitstring hội tụ — không chỉ tin field
    # `feasible` do worker tự báo cáo.
    bits = np.array([int(b) for b in actual.bitstring])
    assert actual.feasible == predicate(bits)


def test_qaoa_one_seed_fast_rejects_both_always_feasible_and_constraints() -> None:
    n = 2
    Q = np.zeros((n, n))
    linear = np.array([-1.0, -1.0])
    qp = build_quadratic_program(Q, linear, 0.0, ticker_order=["A", "B"])
    with pytest.raises(ValueError, match="at most one"):
        solve_qaoa_one_seed_fast(
            qp,
            seed=0,
            shots=8,
            maxiter=1,
            always_feasible=True,
            feasibility_constraints={"max_active_candidates": 1},
        )


def test_worker_module_exits_without_interpreter_finalization() -> None:
    """P1-1 regression: worker PHẢI thoát bằng `os._exit`, không phải `sys.exit`.

    Bug đã đo 2026-09-04: worker tính xong và ghi `output.pkl` sau ~2 giây ở n=8, rồi treo vô hạn
    trong `Py_FinalizeEx` (Rust `drop_glue` của `qiskit_circuit::CircuitData`, qiskit 2.5.1 — cùng
    bẫy đã ghi ở `cli.py::_fast_exit_if_standalone`). Với `sys.exit()`, `subprocess.run(timeout=)`
    bên `solve_qaoa_one_seed_fast` chờ hết timeout, coi là crash rồi RETRY: đo được 600.2s (đúng
    3 x 200s) cho một phép tính 2 giây. Sau khi đổi sang `os._exit()`: 1.4s.

    Test đọc source thay vì chạy worker thật vì cái treo đó chỉ xuất hiện sau khi qiskit đã dựng
    mạch — quá đắt cho unit test, và bản thân việc "treo" không thể assert nhanh được.
    """
    from pathlib import Path

    import qshield_quantum.solvers._qaoa_worker as worker_mod

    source = Path(worker_mod.__file__).read_text(encoding="utf-8")
    entrypoint = source.split('if __name__ == "__main__":')[-1]
    # Bỏ comment: chính comment giải thích bug có chứa chuỗi "sys.exit()", tìm thô sẽ bắt nhầm.
    code_only = "\n".join(
        line for line in entrypoint.splitlines() if not line.strip().startswith("#")
    )

    assert "os._exit(" in code_only, (
        "worker phải thoát bằng os._exit() — sys.exit() chạy Py_FinalizeEx và treo vô hạn"
    )
    assert "sys.exit(" not in code_only, (
        "sys.exit() trong entrypoint sẽ làm subprocess treo và fast path mất hàng trăm lần chi phí"
    )
    # output.pkl phải được ghi TRƯỚC khi thoát, nếu không os._exit() sẽ làm mất kết quả.
    assert "write_bytes" in source
    assert source.index("write_bytes") < source.index('if __name__ == "__main__":')


def test_same_seed_reproduces_the_same_qaoa_result() -> None:
    """Cùng `seed` PHẢI cho cùng bitstring/energy — nếu không, mọi số trong benchmark vô nghĩa.

    Bug đã đo 2026-09-04: `seed` chỉ được truyền cho `StatevectorSampler` (seed việc LẤY MẪU),
    còn `QAOA(initial_point=None)` bốc điểm khởi tạo qua `algorithm_globals.random` — một RNG
    TOÀN CỤC không liên quan `seed`. Ba lần chạy cùng seed=101 cho hai kết quả khác nhau
    (`00111011` vs `00111111`). Hệ quả: `optimality_gap`, `winning_bitstring`, `success_prob`
    trong `workflow_benchmark.json` không tái tạo được dù artifact có đủ `registered_seeds` và
    `qubo_hash` — ký duyệt trên một run hash cụ thể (docs/decisions/2026-08-31-phan-hoi-bao-cao-15-08.md G3) sẽ vô nghĩa.
    """
    from qshield_quantum.formulation.qiskit_program import build_quadratic_program
    from qshield_quantum.formulation.surrogate import (
        QuadraticSurrogate,
        quadratic_feature_count,
    )
    from qshield_quantum.solvers.qaoa import _always_feasible, solve_qaoa_one_seed

    n = 6
    rng = np.random.default_rng(n)
    Q = rng.normal(0, 0.02, size=(n, n))
    Q = (Q + Q.T) / 2
    np.fill_diagonal(Q, 0.0)
    model = QuadraticSurrogate(
        Q=Q,
        linear=rng.normal(0, 0.05, size=n),
        constant=0.0,
        residual_sum_squares=0.0,
        rank=quadratic_feature_count(n),
        sample_count=quadratic_feature_count(n),
    )
    qp = build_quadratic_program(
        model.Q, model.linear, model.constant, ticker_order=[f"b{i}" for i in range(n)]
    )

    def _run(seed: int):
        result = solve_qaoa_one_seed(
            qp,
            seed=seed,
            shots=64,
            maxiter=5,
            feasibility=_always_feasible,
            reps=1,
            warm_start=False,
            candidate_pool_size=2,
        )
        return result.bitstring, round(result.energy, 10)

    first, second = _run(101), _run(101)
    assert first == second, f"cùng seed cho kết quả khác nhau: {first} vs {second}"

    # Seed vẫn phải CÓ tác dụng: khoá cứng một initial_point sẽ làm mọi seed giống nhau, biến
    # "10 seed" thành một seed lặp 10 lần và vô hiệu hoá quy tắc không-cherry-pick (CLAUDE.md 18).
    other = _run(202)
    assert isinstance(other[0], str) and len(other[0]) == n
    assert _run(202) == other, "seed 202 cũng phải tái lập được"
