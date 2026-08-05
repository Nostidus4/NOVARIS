import pytest
from qshield_risk.costs import CostRates, transaction_costs


def test_transaction_cost_breakdown_by_hand() -> None:
    rates = CostRates(fee=0.001, spread=0.002, liquidity_penalty=0.0005)
    costs = transaction_costs(0.25, rates)
    assert costs.fee == pytest.approx(0.00025)
    assert costs.spread == pytest.approx(0.0005)
    assert costs.liquidity_penalty == pytest.approx(0.000125)
    assert costs.total == pytest.approx(0.000875)


def test_negative_rate_or_notional_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        CostRates(fee=-0.001, spread=0.0, liquidity_penalty=0.0)
    with pytest.raises(ValueError, match="gross_sales"):
        transaction_costs(-0.1, CostRates(0.0, 0.0, 0.0))


def test_null_cost_config_fails_instead_of_inventing_assumptions() -> None:
    config = {
        "transaction_cost": {"fee": None, "spread": 0.0, "liquidity_penalty": 0.0}
    }
    with pytest.raises(ValueError, match="fee=null"):
        CostRates.from_config(config)
