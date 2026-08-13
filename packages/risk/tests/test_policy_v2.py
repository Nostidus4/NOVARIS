from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from qshield_risk.objective import COMPONENT_NAMES, financial_objective
from qshield_risk.policy import RiskPolicy


def _config(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "cvar_alpha": 0.95,
        "robustness_confidence_levels": [],
        "horizon_days": 1,
        "weight_sum_tolerance": 1e-10,
        "maximum_reduction": 0.30,
        "target_cash_increment": 0.10,
        "transaction_cost": {
            "fee": 0.001,
            "spread": 0.001,
            "liquidity_penalty": 0.0005,
        },
        "financial_objective": {
            "components": {
                name: {"weight": 1.0 if name == "cvar" else 0.0, "scale": 1.0}
                for name in COMPONENT_NAMES
            }
        },
        "risk_policy": policy,
    }


def _policy(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "policy_version": "risk-policy-test-v1",
        "status": "PROVISIONAL_TEST",
        "risk_appetite": "balanced",
        "cash_min": 0.0,
        "cash_max": 0.5,
        "cvar_budget": 0.5,
        "max_turnover": 0.5,
        "do_not_sell": [],
        "per_asset_reduction_caps": {},
    }
    values.update(overrides)
    return values


def test_no_action_is_feasible_when_baseline_is_inside_policy() -> None:
    cube = np.zeros((40, 1, 2))
    result = financial_objective(
        [0.0, 0.0],
        cube,
        ("AAA", "BBB"),
        {"AAA": 0.5, "BBB": 0.5},
        0.0,
        _config(_policy()),
    )
    assert result.status == "FEASIBLE"
    assert result.constraint_violations == ()
    assert result.constraint_details == ()
    assert result.components["cash_budget_deviation"].raw == pytest.approx(0.0)
    assert result.policy_metadata is not None


def test_policy_violations_are_structured_and_separate_from_objective() -> None:
    cube = np.zeros((40, 1, 2))
    policy = _policy(
        cash_max=0.05,
        max_turnover=0.05,
        do_not_sell=["AAA"],
        per_asset_reduction_caps={"AAA": 0.10},
        per_asset_liquidity_caps={"AAA": 0.05},
        minimum_trade_value=0.2,
    )
    result = financial_objective(
        [0.20, 0.0],
        cube,
        ("AAA", "BBB"),
        {"AAA": 0.5, "BBB": 0.5},
        0.0,
        _config(policy),
    )
    codes = {item.code for item in result.constraint_details}
    assert {
        "CASH_ABOVE_MAX",
        "TURNOVER_LIMIT",
        "DO_NOT_SELL",
        "PER_ASSET_CAP",
        "PER_ASSET_LIQUIDITY_CAP",
        "MINIMUM_TRADE_VALUE",
    } <= codes
    assert result.status == "INFEASIBLE_POLICY"
    assert result.value == pytest.approx(result.components["cvar"].contribution)
    assert all(isinstance(value, str) for value in result.constraint_violations)


def test_cvar_budget_violation_is_reported() -> None:
    cube = np.full((40, 1, 2), -0.10)
    result = financial_objective(
        [0.0, 0.0],
        cube,
        ("AAA", "BBB"),
        {"AAA": 0.5, "BBB": 0.5},
        0.0,
        _config(_policy(cvar_budget=0.05)),
    )
    assert "CVAR_BUDGET" in {item.code for item in result.constraint_details}


def test_policy_validation_rejects_invalid_band_or_posterior() -> None:
    with pytest.raises(ValueError, match="cash band"):
        RiskPolicy.from_config({"risk_policy": _policy(cash_min=0.6, cash_max=0.5)})
    with pytest.raises(ValueError, match="regime_posterior"):
        RiskPolicy.from_config(
            {"risk_policy": _policy(regime_posterior={"normal": 0.8, "stress": 0.8})}
        )
