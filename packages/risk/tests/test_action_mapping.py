from typing import Any

import numpy as np
import pytest
from qshield_risk import evaluate
from qshield_risk.actions import apply_actions, selected_action_ids
from qshield_risk.costs import CostRates

from .conftest import TICKERS


def test_action_ids_follow_bit_positions() -> None:
    assert selected_action_ids([0, 1, 0, 0, 1, 0, 0, 1], n_assets=8) == (1, 4, 7)


def test_each_action_sells_twenty_percent_of_current_position() -> None:
    state = apply_actions(
        np.full(8, 0.125),
        0.0,
        [1, 0, 0, 0, 0, 0, 0, 0],
        reduction_pct=0.20,
        rates=CostRates(0.0, 0.0, 0.0),
        tolerance=1e-10,
    )
    assert state.stock_amounts[0] == pytest.approx(0.10)
    assert state.cash_amount == pytest.approx(0.025)


@pytest.mark.parametrize("bitstring", [[0] * 8, [1] * 8])
def test_k_mismatch_is_reported_but_true_metrics_are_returned(
    bitstring: list[int], risk_config: dict[str, Any]
) -> None:
    cube = np.zeros((10, 2, 8))
    weights = {ticker: 0.125 for ticker in TICKERS}
    result = evaluate(bitstring, cube, TICKERS, weights, 0.0, risk_config)
    assert result.before.scenario_count == result.after.scenario_count == 10
    assert result.constraint_violations
    assert "cardinality" in result.constraint_violations[0]


def test_exact_k_has_no_cardinality_violation(risk_config: dict[str, Any]) -> None:
    result = evaluate(
        [1, 1, 1, 0, 0, 0, 0, 0],
        np.zeros((10, 2, 8)),
        TICKERS,
        {ticker: 0.125 for ticker in TICKERS},
        0.0,
        risk_config,
    )
    assert result.constraint_violations == ()


def test_invalid_length_or_non_binary_bitstring_is_rejected(risk_config: dict[str, Any]) -> None:
    cube = np.zeros((10, 2, 8))
    weights = {ticker: 0.125 for ticker in TICKERS}
    with pytest.raises(ValueError, match=r"expected \(8,\)"):
        evaluate([1, 0], cube, TICKERS, weights, 0.0, risk_config)
    with pytest.raises(ValueError, match="only 0/1"):
        evaluate([2] + [0] * 7, cube, TICKERS, weights, 0.0, risk_config)
