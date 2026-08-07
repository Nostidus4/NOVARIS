"""Public true-risk evaluator used by the Quantum package."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from qshield_risk.actions import apply_actions, selected_action_ids
from qshield_risk.costs import CostBreakdown, CostRates
from qshield_risk.metrics import RiskMetrics, alpha_key, risk_metrics_from_wealth
from qshield_risk.paths import portfolio_wealth_paths, validate_scenario_cube
from qshield_risk.portfolio import align_portfolio_weights, validate_ticker_order


def required_float(config: Mapping[str, Any], key: str) -> float:
    """Read one mandatory finite numeric config value without inventing a default."""
    value = config.get(key)
    if value is None:
        raise ValueError(
            f"[risk.config] {key}=null; an approved explicit value is required."
        )
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"[risk.config] {key} must be finite, got {value!r}.")
    return result


def confidence_levels(config: Mapping[str, Any]) -> tuple[float, ...]:
    """Return primary CVaR alpha followed by unique robustness confidence levels."""
    primary = required_float(config, "cvar_alpha")
    robustness = config.get("robustness_confidence_levels", ()) or ()
    return tuple(dict.fromkeys((primary, *(float(level) for level in robustness))))


@dataclass(frozen=True)
class RiskEvaluation:
    """True net-risk result for one hedge bitstring.

    Before/after metrics use decimal pre-trade NAV units. Post-trade normalized weights sum to one,
    while ``nav_after`` records the NAV reduction caused by costs. Constraint violations are
    reported independently from financial metrics, allowing Quantum to inspect infeasible
    candidates without treating a penalty score as true risk.
    """

    before: RiskMetrics
    after: RiskMetrics
    selected_action_ids: tuple[int, ...]
    selected_tickers: tuple[str, ...]
    turnover: float
    cost_breakdown: CostBreakdown
    nav_after: float
    stock_weights_after: dict[str, float]
    cash_weight_after: float
    constraint_violations: tuple[str, ...]
    recommendation_status: str

    @property
    def improves_primary_cvar(self) -> bool:
        return self.recommendation_status == "improves_cvar"

    def to_dict(self) -> dict[str, Any]:
        return {
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "selected_action_ids": list(self.selected_action_ids),
            "selected_tickers": list(self.selected_tickers),
            "turnover": self.turnover,
            "cost_breakdown": self.cost_breakdown.to_dict(),
            "nav_after": self.nav_after,
            "stock_weights_after": self.stock_weights_after,
            "cash_weight_after": self.cash_weight_after,
            "constraint_violations": list(self.constraint_violations),
            "recommendation_status": self.recommendation_status,
        }


def evaluate(
    bitstring: Sequence[int],
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
) -> RiskEvaluation:
    """Evaluate true before/after portfolio risk for a length-eight hedge bitstring.

    Parameters
    ----------
    bitstring:
        One binary decision per ticker in ``ticker_order``. A selected bit sells
        ``action_reduction_pct`` of that asset's current position.
    scenarios:
        Simple daily return cube with shape ``(scenario, horizon, 8)``. Returns must be finite and
        greater than ``-1``. Asset axis order must match ``ticker_order``.
    ticker_order:
        Eight unique ticker symbols copied from the Scenario manifest.
    weights, cash_weight:
        Pre-trade portfolio in decimal NAV units. Stock plus cash weights must already sum to one;
        invalid portfolios are rejected rather than normalized.
    config:
        Merged Config containing horizon, CVaR levels, 20% action size, transaction-cost rates,
        weight tolerance and ``k_actions``.

    Notes
    -----
    The hedge is executed once before the scenario horizon, then held without daily rebalancing.
    Costs reduce cash and NAV exactly once. Loss is ``1 - terminal_wealth`` (equivalently negative
    horizon portfolio return). A cardinality mismatch is returned in ``constraint_violations``;
    invalid bitstring shape or values still raise ``ValueError``.
    """
    tickers = validate_ticker_order(ticker_order)
    cube = validate_scenario_cube(
        scenarios,
        expected_horizon=int(config.get("horizon_days", 20)),
        expected_assets=len(tickers),
    )
    tolerance = required_float(config, "weight_sum_tolerance")
    aligned = align_portfolio_weights(
        weights, tickers, cash_weight, tolerance=tolerance
    )
    levels = confidence_levels(config)
    alpha = required_float(config, "cvar_alpha")
    reduction_pct = required_float(config, "action_reduction_pct")
    rates = CostRates.from_config(config)

    action_ids = selected_action_ids(bitstring, n_assets=len(tickers))
    bits = np.zeros(len(tickers), dtype=int)
    bits[list(action_ids)] = 1
    trade = apply_actions(
        aligned,
        cash_weight,
        bits,
        reduction_pct=reduction_pct,
        rates=rates,
        tolerance=tolerance,
    )
    before = risk_metrics_from_wealth(
        portfolio_wealth_paths(cube, aligned, cash_weight), levels
    )
    after = risk_metrics_from_wealth(
        portfolio_wealth_paths(cube, trade.stock_amounts, trade.cash_amount), levels
    )

    expected_k = int(config.get("k_actions", 3))
    violations: list[str] = []
    if len(action_ids) != expected_k:
        violations.append(
            f"cardinality: selected {len(action_ids)} actions; expected K={expected_k}"
        )
    primary_key = alpha_key(alpha)
    improves = after.cvar[primary_key] < before.cvar[primary_key]
    return RiskEvaluation(
        before=before,
        after=after,
        selected_action_ids=action_ids,
        selected_tickers=tuple(tickers[index] for index in action_ids),
        turnover=trade.turnover,
        cost_breakdown=trade.costs,
        nav_after=trade.nav_after,
        stock_weights_after={
            ticker: float(trade.stock_weights[index])
            for index, ticker in enumerate(tickers)
        },
        cash_weight_after=trade.cash_weight,
        constraint_violations=tuple(violations),
        recommendation_status="improves_cvar" if improves else "no_improvement",
    )
