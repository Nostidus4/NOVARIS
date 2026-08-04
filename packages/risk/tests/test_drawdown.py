import numpy as np
import pytest
from qshield_risk.drawdown import drawdown_paths, worst_scenario_max_drawdown


def test_drawdown_uses_running_peak_wealth_and_initial_nav() -> None:
    wealth = np.array([[1.10, 0.88, 0.99], [0.90, 0.95, 0.80]])
    drawdowns = drawdown_paths(wealth)
    np.testing.assert_allclose(drawdowns[0], [0.0, -0.20, -0.10])
    np.testing.assert_allclose(drawdowns[1], [-0.10, -0.05, -0.20])
    assert worst_scenario_max_drawdown(wealth) == pytest.approx(-0.20)


def test_drawdown_includes_immediate_transaction_cost_from_initial_nav() -> None:
    wealth = np.array([[0.999, 1.001]])
    np.testing.assert_allclose(drawdown_paths(wealth), [[-0.001, 0.0]])
