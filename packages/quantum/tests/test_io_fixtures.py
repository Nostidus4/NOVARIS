# Đỗ Ngọc Tân - io.py <-> fixtures.py round-trip: DataFrame đúng schema, chuyển ngược lại đúng mảng gốc.
import numpy as np
import pytest
from qshield_quantum import fixtures
from qshield_quantum.io import action_effects_to_arrays, pairwise_to_matrix


def test_fixtures_generate_frames_round_trip_to_same_arrays() -> None:
    tickers = ["ACB", "CTG", "VCB", "HPG"]
    g, C, c, baseline = fixtures.generate_arrays(tickers, seed=7, alpha=0.95)
    action_effects_df, pairwise_effects_df, baseline2 = fixtures.generate_frames(
        tickers, seed=7, alpha=0.95
    )

    g2, c2 = action_effects_to_arrays(action_effects_df, tickers)
    C2 = pairwise_to_matrix(pairwise_effects_df, tickers)

    assert np.allclose(g, g2)
    assert np.allclose(c, c2)
    assert np.allclose(C, C2)
    assert (
        baseline == baseline2
    )  # cùng seed -> cùng baseline (dataclass so bằng giá trị)


def test_pairwise_to_matrix_is_symmetric_with_zero_diagonal() -> None:
    tickers = ["A", "B", "C"]
    _g, C, _c, _ = fixtures.generate_arrays(tickers, seed=1, alpha=0.95)
    pairwise_df = fixtures.pairwise_effects_frame(C)

    rebuilt = pairwise_to_matrix(pairwise_df, tickers)
    assert np.allclose(rebuilt, rebuilt.T)
    assert np.allclose(np.diag(rebuilt), 0.0)


def test_action_effects_to_arrays_raises_on_ticker_order_mismatch() -> None:
    tickers = ["A", "B", "C"]
    action_effects_df, _pairwise_df, _baseline = fixtures.generate_frames(
        tickers, seed=1, alpha=0.95
    )
    with pytest.raises(ValueError, match="Thứ tự ticker"):
        action_effects_to_arrays(action_effects_df, ["B", "A", "C"])


def test_baseline_risk_weights_sum_to_one() -> None:
    tickers = ["A", "B", "C", "D"]
    _, _, _, baseline = fixtures.generate_arrays(tickers, seed=9, alpha=0.95)
    assert sum(baseline.portfolio_weights.values()) == pytest.approx(1.0)
    assert baseline.cvar_0 > baseline.var_0 > 0
