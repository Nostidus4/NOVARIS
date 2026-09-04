# Đỗ Ngọc Tân - verify_consistency: PASS trên fixtures, FAIL rõ ràng khi 1 trong 3 đường công thức lệch.
import time

import numpy as np
import pytest
import qshield_quantum.verify.consistency as consistency_mod
from qshield_quantum import fixtures
from qshield_quantum.formulation.qiskit_program import build_quadratic_program, to_qubo
from qshield_quantum.formulation.surrogate import (
    QuadraticSurrogate,
    quadratic_feature_count,
)
from qshield_quantum.verify.consistency import (
    ConsistencyError,
    _batch_energy,
    _qp_energy_arrays,
    all_bitstrings,
    bitstring_chunks,
    verify_consistency,
    verify_quadratic_consistency,
)


def test_all_bitstrings_shape_and_count() -> None:
    Z = all_bitstrings(4)
    assert Z.shape == (16, 4)
    assert set(Z.sum(axis=1)) == {0, 1, 2, 3, 4}


def test_verify_consistency_passes_on_fixtures_data() -> None:
    tickers = ["ACB", "CTG", "VCB", "HPG"]
    g, C, c, _baseline = fixtures.generate_arrays(tickers, seed=42, alpha=0.95)

    verify_consistency(
        g,
        C,
        c,
        lambda_1=1.0,
        lambda_2=1.0,
        penalty=10.0,
        k_actions=2,
        ticker_order=tickers,
    )  # không raise = PASS


def test_verify_consistency_raises_when_qiskit_program_is_wrong(monkeypatch) -> None:
    tickers = ["ACB", "CTG", "VCB", "HPG"]
    g, C, c, _baseline = fixtures.generate_arrays(tickers, seed=42, alpha=0.95)

    real_builder = consistency_mod.build_quadratic_program

    def _broken_builder(Q, linear, constant, *, ticker_order):
        # Cố ý làm lệch: cộng thêm hằng số vào constant để mô phỏng lỗi convert.
        return real_builder(Q, linear, constant + 100.0, ticker_order=ticker_order)

    monkeypatch.setattr(consistency_mod, "build_quadratic_program", _broken_builder)

    with pytest.raises(ConsistencyError, match="lệch với QuadraticProgram"):
        verify_consistency(
            g,
            C,
            c,
            lambda_1=1.0,
            lambda_2=1.0,
            penalty=10.0,
            k_actions=2,
            ticker_order=tickers,
        )


def _random_generic_model(n: int, seed: int) -> QuadraticSurrogate:
    rng = np.random.default_rng(seed)
    Q = rng.normal(size=(n, n))
    Q = (Q + Q.T) / 2.0
    np.fill_diagonal(Q, 0.0)
    linear = rng.normal(size=n)
    constant = float(rng.normal())
    feature_count = quadratic_feature_count(n)
    return QuadraticSurrogate(
        Q=Q,
        linear=linear,
        constant=constant,
        residual_sum_squares=0.0,
        rank=feature_count,
        sample_count=feature_count,
    )


@pytest.mark.parametrize("n", [8, 10, 12])
def test_batch_energy_matches_qiskit_objective_evaluate_per_row(n: int) -> None:
    """P1-4: đường vectorised (`_qp_energy_arrays` + `_batch_energy`, NumPy cho cả batch) phải cho
    ra energy Y HỆT đường cũ (gọi `objective.evaluate(z)` cho từng bitstring một trong vòng lặp
    Python) — trên cả `QuadraticProgram` lẫn `QUBO` sau convert. n<=12 (<=4096 states) đủ rẻ để
    duyệt hết bằng vòng lặp Python "cũ" làm reference độc lập."""
    model = _random_generic_model(n, seed=n * 1000 + 7)
    names = [f"x{i}" for i in range(n)]
    qp = build_quadratic_program(
        model.Q, model.linear, model.constant, ticker_order=names
    )
    qubo = to_qubo(qp)
    Z = np.concatenate(list(bitstring_chunks(n, chunk_size=1 << n)))

    for program in (qp, qubo):
        old_reference = np.array(
            [program.objective.evaluate(z) for z in Z], dtype=float
        )
        quadratic, linear, constant = _qp_energy_arrays(program)
        vectorised = _batch_energy(quadratic, linear, constant, Z)
        np.testing.assert_allclose(vectorised, old_reference, atol=1e-9)


@pytest.mark.slow
def test_verify_quadratic_consistency_full_2_20_states_under_60_seconds() -> None:
    """CLAUDE.md quy tắc 15 — cổng chặn PHẢI chạy FULL 2^20 (không sampled) trước khi tin QAOA.
    Trước P1-4, `cli.py` phải hạ xuống `verify_sample_size=4096` (0.39% không gian) vì đường
    Python-loop (`objective.evaluate(z)` từng bitstring) không xong trong thời gian chấp nhận
    được. Sau khi vectorise, full 2^20 phải xong dưới 60 giây."""
    n = 20
    feature_count = quadratic_feature_count(n)
    model = QuadraticSurrogate(
        Q=np.zeros((n, n)),
        linear=-np.arange(1, n + 1, dtype=float),
        constant=3.0,
        residual_sum_squares=0.0,
        rank=feature_count,
        sample_count=feature_count,
    )
    names = [f"x{i}" for i in range(n)]

    t0 = time.perf_counter()
    meta = verify_quadratic_consistency(model, variable_names=names, chunk_size=65_536)
    elapsed = time.perf_counter() - t0

    assert meta["checked_states"] == 1_048_576
    assert meta["total_states"] == 1_048_576
    assert meta["sampled"] is False
    assert elapsed < 60.0, (
        f"verify_quadratic_consistency full 2^20 took {elapsed:.1f}s (budget: 60s)."
    )
