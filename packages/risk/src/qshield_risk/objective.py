"""Canonical financial objective for four-level actions and downstream re-evaluation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from qshield_risk.actions import TradeState, apply_reductions
from qshield_risk.costs import CostRates
from qshield_risk.evaluate import confidence_levels, required_float
from qshield_risk.metrics import RiskMetrics, alpha_key, risk_metrics_from_wealth
from qshield_risk.paths import portfolio_wealth_paths, validate_scenario_cube
from qshield_risk.portfolio import align_portfolio_weights, validate_ticker_order

COMPONENT_NAMES = (
    "cvar",
    "return_sacrifice",
    "transaction_cost",
    "turnover",
    "liquidity_penalty",
    "cash_budget_deviation",
)


@dataclass(frozen=True)
class ObjectiveComponent:
    """One auditable objective term in raw and configured scaled units."""

    raw: float
    scaled: float
    weight: float
    contribution: float


@dataclass(frozen=True)
class FinancialObjective:
    """True financial objective plus metrics and accounting used to produce it."""

    value: float
    components: dict[str, ObjectiveComponent]
    before: RiskMetrics
    after: RiskMetrics
    reductions: tuple[float, ...]
    trade: TradeState
    constraint_violations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "components": {
                name: asdict(component) for name, component in self.components.items()
            },
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "reductions": list(self.reductions),
            "turnover": self.trade.turnover,
            "cost_breakdown": self.trade.costs.to_dict(),
            "nav_after": self.trade.nav_after,
            "stock_weights_after": self.trade.stock_weights.tolist(),
            "cash_weight_after": self.trade.cash_weight,
            "constraint_violations": list(self.constraint_violations),
        }


def _objective_specs(config: Mapping[str, Any]) -> dict[str, tuple[float, float]]:
    raw = config.get("financial_objective")
    if not isinstance(raw, Mapping):
        raise TypeError(
            "[risk.objective] financial_objective mapping is required; "
            "weights/scales must be approved explicitly."
        )
    raw_components = raw.get("components")
    if not isinstance(raw_components, Mapping):
        raise TypeError(
            "[risk.objective] financial_objective.components must be a mapping."
        )

    specs: dict[str, tuple[float, float]] = {}
    for name in COMPONENT_NAMES:
        item = raw_components.get(name)
        if not isinstance(item, Mapping):
            raise TypeError(
                f"[risk.objective] financial_objective.components.{name} is required."
            )
        if item.get("weight") is None or item.get("scale") is None:
            raise ValueError(
                f"[risk.objective] {name} requires explicit finite weight and scale."
            )
        weight = float(item["weight"])
        scale = float(item["scale"])
        if not np.isfinite(weight) or weight < 0.0:
            raise ValueError(
                f"[risk.objective] {name}.weight must be finite and non-negative."
            )
        if not np.isfinite(scale) or scale <= 0.0:
            raise ValueError(
                f"[risk.objective] {name}.scale must be finite and positive."
            )
        specs[name] = (weight, scale)
    return specs


def financial_objective(
    reductions: npt.ArrayLike,
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
) -> FinancialObjective:
    """Evaluate the single minimization objective used by sampling, reranking and polishing."""
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
    values = np.asarray(reductions, dtype=float)
    if values.shape != (len(tickers),):
        raise ValueError(
            f"[risk.objective] reductions shape={values.shape}; expected ({len(tickers)},)."
        )

    specs = _objective_specs(config)
    rates = CostRates.from_config(config)
    maximum = required_float(config, "maximum_reduction")
    target_cash = required_float(config, "target_cash_increment")
    if maximum > 1.0 or maximum < 0.0:
        raise ValueError("[risk.objective] maximum_reduction must be in [0, 1].")
    if target_cash < 0.0:
        raise ValueError("[risk.objective] target_cash_increment must be non-negative.")
    trade = apply_reductions(
        aligned,
        cash_weight,
        values,
        rates=rates,
        tolerance=tolerance,
        maximum_reduction=maximum,
    )
    levels = confidence_levels(config)
    before = risk_metrics_from_wealth(
        portfolio_wealth_paths(cube, aligned, cash_weight), levels
    )
    after = risk_metrics_from_wealth(
        portfolio_wealth_paths(cube, trade.stock_amounts, trade.cash_amount), levels
    )
    primary_key = alpha_key(required_float(config, "cvar_alpha"))
    cash_increment = trade.cash_amount - float(cash_weight)
    raw_values = {
        "cvar": after.cvar[primary_key],
        "return_sacrifice": max(
            0.0, before.expected_horizon_return - after.expected_horizon_return
        ),
        "transaction_cost": trade.costs.total,
        "turnover": trade.turnover,
        "liquidity_penalty": trade.costs.liquidity_penalty,
        "cash_budget_deviation": abs(cash_increment - target_cash),
    }
    components: dict[str, ObjectiveComponent] = {}
    for name in COMPONENT_NAMES:
        weight, scale = specs[name]
        raw_value = float(raw_values[name])
        scaled = raw_value / scale
        components[name] = ObjectiveComponent(
            raw=raw_value,
            scaled=scaled,
            weight=weight,
            contribution=weight * scaled,
        )
    value = float(sum(component.contribution for component in components.values()))
    if not np.isfinite(value):
        raise ValueError("[risk.objective] objective is not finite.")
    return FinancialObjective(
        value=value,
        components=components,
        before=before,
        after=after,
        reductions=tuple(float(value) for value in values),
        trade=trade,
    )
