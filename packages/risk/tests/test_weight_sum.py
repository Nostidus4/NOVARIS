from typing import Any

import numpy as np
import pytest
from qshield_risk.actions import apply_actions
from qshield_risk.costs import CostRates
from qshield_risk.portfolio import align_portfolio_weights

from .conftest import TICKERS


def test_post_trade_accounting_and_normalized_weights(risk_config: dict[str, Any]) -> None:
    stocks = np.full(8, 0.125)
    state = apply_actions(
        stocks,
        0.0,
        [1, 1, 1, 0, 0, 0, 0, 0],
        reduction_pct=0.20,
        rates=CostRates.from_config(risk_config),
        tolerance=1e-10,
    )
    assert state.turnover == pytest.approx(0.075)
    assert state.costs.total == pytest.approx(0.0002625)
    assert state.nav_after == pytest.approx(0.9997375)
    assert state.cash_amount == pytest.approx(0.0747375)
    assert state.stock_amounts.sum() + state.cash_amount == pytest.approx(state.nav_after)
    assert state.stock_weights.sum() + state.cash_weight == pytest.approx(1.0)


def test_invalid_input_portfolio_is_not_auto_normalized() -> None:
    weights = {ticker: 0.12 for ticker in TICKERS}
    with pytest.raises(ValueError, match="not auto-normalized"):
        align_portfolio_weights(weights, TICKERS, 0.0, tolerance=1e-10)


def test_weights_are_aligned_by_ticker_not_mapping_insertion_order() -> None:
    reversed_weights = {ticker: weight for ticker, weight in zip(reversed(TICKERS), range(1, 9))}
    total = float(sum(reversed_weights.values()))
    normalized = {ticker: weight / total for ticker, weight in reversed_weights.items()}
    aligned = align_portfolio_weights(normalized, TICKERS, 0.0, tolerance=1e-10)
    assert aligned[0] == pytest.approx(normalized["ACB"])
    assert aligned[-1] == pytest.approx(normalized["FPT"])
