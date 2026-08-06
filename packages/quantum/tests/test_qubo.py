# Đỗ Ngọc Tân - build_qubo phải cho energy khớp objective.objective TUYỆT ĐỐI trên toàn bộ bitstring.
import itertools

import numpy as np
from qshield_quantum.formulation.objective import objective
from qshield_quantum.formulation.penalty import penalty_terms, suggest_penalty
from qshield_quantum.formulation.qubo import build_qubo


def _all_bitstrings(n: int) -> list[np.ndarray]:
    return [np.array(bits) for bits in itertools.product([0, 1], repeat=n)]


def test_build_qubo_matches_objective_on_all_bitstrings() -> None:
    rng = np.random.default_rng(1)
    n = 5
    g = rng.normal(size=n)
    raw = rng.normal(size=(n, n))
    C = (raw + raw.T) / 2
    np.fill_diagonal(C, 0.0)
    c = np.abs(rng.normal(size=n))
    lambda_1, lambda_2, penalty, k_actions = 0.8, 1.2, 7.0, 2

    Q, linear, constant = build_qubo(
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )

    for z in _all_bitstrings(n):
        expected = objective(
            z,
            g,
            C,
            c,
            lambda_1=lambda_1,
            lambda_2=lambda_2,
            penalty=penalty,
            k_actions=k_actions,
        )
        actual = float(z @ Q @ z + linear @ z + constant)
        assert abs(actual - expected) < 1e-9, (
            f"z={z}: qubo={actual} objective={expected}"
        )


def test_penalty_terms_reproduce_penalty_formula() -> None:
    n, k_actions, penalty = 4, 2, 3.0
    Q, linear, constant = penalty_terms(n, k_actions, penalty)
    for z in _all_bitstrings(n):
        expected = penalty * (z.sum() - k_actions) ** 2
        actual = float(z @ Q @ z + linear @ z + constant)
        assert abs(actual - expected) < 1e-9


def test_suggest_penalty_makes_infeasible_never_beat_best_feasible() -> None:
    rng = np.random.default_rng(2)
    n, k_actions = 6, 3
    g = rng.normal(size=n)
    raw = rng.normal(size=(n, n))
    C = (raw + raw.T) / 2
    np.fill_diagonal(C, 0.0)
    c = np.abs(rng.normal(size=n))
    lambda_1, lambda_2 = 1.0, 1.0

    penalty = suggest_penalty(g, C, c, lambda_1=lambda_1, lambda_2=lambda_2)

    energies = [
        (
            objective(
                z,
                g,
                C,
                c,
                lambda_1=lambda_1,
                lambda_2=lambda_2,
                penalty=penalty,
                k_actions=k_actions,
            ),
            int(z.sum()) == k_actions,
        )
        for z in _all_bitstrings(n)
    ]
    best_feasible = min(e for e, feasible in energies if feasible)
    best_infeasible = min(
        (e for e, feasible in energies if not feasible), default=float("inf")
    )
    assert best_feasible < best_infeasible
