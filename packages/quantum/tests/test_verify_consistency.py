# Đỗ Ngọc Tân - verify_consistency: PASS trên fixtures, FAIL rõ ràng khi 1 trong 3 đường công thức lệch.
import pytest
import qshield_quantum.verify.consistency as consistency_mod
from qshield_quantum import fixtures
from qshield_quantum.verify.consistency import (
    ConsistencyError,
    all_bitstrings,
    verify_consistency,
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
