from typing import Any

import numpy as np
import pytest
from qshield_risk import evaluate
from qshield_risk.effects import build_effects
from qshield_risk.paths import asset_growth_paths, portfolio_wealth_paths

from .conftest import TICKERS


def test_simple_returns_compound_and_portfolio_is_buy_and_hold() -> None:
    cube = np.zeros((1, 2, 8))
    cube[0, :, 0] = [0.10, -0.10]
    growth = asset_growth_paths(cube)
    assert growth[0, -1, 0] == pytest.approx(0.99)
    wealth = portfolio_wealth_paths(cube, np.array([0.5] + [0.0] * 7), 0.5)
    np.testing.assert_allclose(wealth[0], [1.05, 0.995])


def test_true_cvar_sign_and_cost_are_applied_once(risk_config: dict[str, Any]) -> None:
    cube = np.zeros((100, 2, 8))
    cube[:, 0, :] = -0.10
    weights = {ticker: 0.125 for ticker in TICKERS}
    result = evaluate(
        [1, 1, 1, 0, 0, 0, 0, 0], cube, TICKERS, weights, 0.0, risk_config
    )
    assert result.before.cvar["0.95"] == pytest.approx(0.10)
    assert result.before.expected_horizon_return == pytest.approx(-0.10)
    # TL-008: cash transaction cost is fee+spread; liquidity remains separate.
    assert result.cost_breakdown.total == pytest.approx(0.000225)
    assert result.cost_breakdown.liquidity_penalty == pytest.approx(0.0000375)
    assert result.after.cvar["0.95"] == pytest.approx(0.092725)
    assert result.improves_primary_cvar
    assert result.recommendation_status == "improves_cvar"


def test_no_recommendation_when_net_cvar_does_not_improve(
    risk_config: dict[str, Any],
) -> None:
    result = evaluate(
        [1, 1, 1, 0, 0, 0, 0, 0],
        np.zeros((20, 2, 8)),
        TICKERS,
        {ticker: 0.125 for ticker in TICKERS},
        0.0,
        risk_config,
    )
    assert result.after.cvar["0.95"] > result.before.cvar["0.95"]
    assert result.recommendation_status == "no_improvement"


def test_g_pair_interaction_and_cost_handoff_by_hand(
    risk_config: dict[str, Any],
) -> None:
    cube = np.zeros((20, 2, 8))
    cube[:, 0, :] = -0.10
    result = build_effects(
        cube,
        TICKERS,
        {ticker: 0.125 for ticker in TICKERS},
        0.0,
        risk_config,
    )
    assert len(result.actions) == 8
    assert len(result.pairs) == 28
    assert result.actions.loc[0, "g"] == pytest.approx(0.0025)
    assert result.actions.loc[0, "c"] == pytest.approx(0.000075)
    assert result.pairs.loc[0, "C_ij"] == pytest.approx(0.0, abs=1e-15)
    assert (result.pairs["action_i"] < result.pairs["action_j"]).all()


def test_invalid_simple_return_is_rejected(risk_config: dict[str, Any]) -> None:
    cube = np.zeros((10, 2, 8))
    cube[0, 0, 0] = -1.0
    with pytest.raises(ValueError, match="must be > -1"):
        evaluate(
            [1, 1, 1, 0, 0, 0, 0, 0],
            cube,
            TICKERS,
            {ticker: 0.125 for ticker in TICKERS},
            0.0,
            risk_config,
        )
