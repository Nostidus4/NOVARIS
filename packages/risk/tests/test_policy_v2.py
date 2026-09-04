from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from qshield_risk.objective import COMPONENT_NAMES, financial_objective
from qshield_risk.policy import RiskPolicy, policy_to_quantum_constraints


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


def test_quantum_constraints_none_when_policy_missing_reports_status() -> None:
    quantum, encoding = policy_to_quantum_constraints(
        None, {}, candidate_weights={"AAA": 0.1}, cash_weight_before=0.0
    )
    assert quantum == {}
    assert encoding == {
        "status": "NONE_ENCODED",
        "reason": "risk_policy is null",
        "enforced_at_rerank_only": encoding["enforced_at_rerank_only"],
    }
    assert "CVAR_BUDGET" in encoding["enforced_at_rerank_only"]


def test_quantum_constraints_translate_cash_band_and_turnover_by_hand() -> None:
    """Hand-computed: total_action_pct bounds use max/min candidate weight, not a 1:1 map."""
    policy_dict = _policy(cash_min=0.10, cash_max=0.20, max_turnover=0.50)
    config = {
        "transaction_cost": {"fee": 0.001, "spread": 0.001, "liquidity_penalty": 0.0005}
    }
    policy = RiskPolicy.from_config({"risk_policy": policy_dict})
    candidate_weights = {"A": 0.05, "B": 0.10, "C": 0.02}
    cash_weight_before = 0.05

    quantum, encoding = policy_to_quantum_constraints(
        policy,
        config,
        candidate_weights=candidate_weights,
        cash_weight_before=cash_weight_before,
    )

    total_cost_rate = 0.002
    required_min_sales = (0.10 - 0.05) / (1.0 - total_cost_rate)
    expected_min = (
        100.0 * required_min_sales / 0.10
    )  # divide by MAX weight (0.10, ticker B)
    allowed_max_sales = min((0.20 - 0.05) / (1.0 - total_cost_rate), 0.50)
    expected_max = (
        100.0 * allowed_max_sales / 0.02
    )  # divide by MIN weight (0.02, ticker C)

    assert quantum["min_total_action_pct"] == pytest.approx(expected_min)
    assert quantum["max_total_action_pct"] == pytest.approx(expected_max)
    assert encoding["status"] == "PARTIAL_ENCODED"
    assert set(encoding["encoded_in_quantum_predicate"]) == {
        "min_total_action_pct",
        "max_total_action_pct",
    }
    assert "min_active_candidates" in encoding["not_derivable_from_policy"]
    assert "CVAR_BUDGET" in encoding["enforced_at_rerank_only"]
    assert "DO_NOT_SELL" in encoding["enforced_at_rerank_only"]


def test_quantum_constraints_pin_max_bound_to_zero_when_already_over_budget() -> None:
    policy = RiskPolicy.from_config(
        {"risk_policy": _policy(cash_min=0.0, cash_max=0.10, max_turnover=0.50)}
    )
    quantum, encoding = policy_to_quantum_constraints(
        policy,
        {"transaction_cost": {"fee": 0.0, "spread": 0.0, "liquidity_penalty": 0.0}},
        candidate_weights={"A": 0.10},
        cash_weight_before=0.30,  # already above cash_max before any action
    )
    assert quantum["max_total_action_pct"] == pytest.approx(0.0)
    assert any("already exceeds cash_max" in note for note in encoding["notes"])
