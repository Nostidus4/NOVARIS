# Đỗ Ngọc Tân - build_quadratic_program phải khớp build_qubo TUYỆT ĐỐI (quy ước hệ số quadratic khác nhau).
import itertools

import numpy as np
from qshield_quantum.formulation.qiskit_program import build_quadratic_program, to_qubo
from qshield_quantum.formulation.qubo import build_qubo


def _all_bitstrings(n: int) -> list[np.ndarray]:
    return [np.array(bits) for bits in itertools.product([0, 1], repeat=n)]


def test_quadratic_program_matches_qubo_matrix_form() -> None:
    rng = np.random.default_rng(3)
    n = 4
    tickers = [f"T{i}" for i in range(n)]
    g = rng.normal(size=n)
    raw = rng.normal(size=(n, n))
    C = (raw + raw.T) / 2
    np.fill_diagonal(C, 0.0)
    c = np.abs(rng.normal(size=n))
    lambda_1, lambda_2, penalty, k_actions = 1.0, 1.0, 4.0, 2

    Q, linear, constant = build_qubo(
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )
    qp = build_quadratic_program(Q, linear, constant, ticker_order=tickers)

    for z in _all_bitstrings(n):
        expected = float(z @ Q @ z + linear @ z + constant)
        actual = qp.objective.evaluate(z)
        assert abs(actual - expected) < 1e-9, f"z={z}: qp={actual} qubo={expected}"


def test_to_qubo_does_not_change_energy_without_constraints() -> None:
    rng = np.random.default_rng(4)
    n = 3
    tickers = [f"T{i}" for i in range(n)]
    g = rng.normal(size=n)
    raw = rng.normal(size=(n, n))
    C = (raw + raw.T) / 2
    np.fill_diagonal(C, 0.0)
    c = np.abs(rng.normal(size=n))

    Q, linear, constant = build_qubo(
        g, C, c, lambda_1=1.0, lambda_2=1.0, penalty=5.0, k_actions=1
    )
    qp = build_quadratic_program(Q, linear, constant, ticker_order=tickers)
    qubo = to_qubo(qp)

    for z in _all_bitstrings(n):
        assert abs(qp.objective.evaluate(z) - qubo.objective.evaluate(z)) < 1e-9
