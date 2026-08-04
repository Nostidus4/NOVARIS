"""Gross CVaR action and pair effects for the QUBO handoff."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd  # type: ignore[import-untyped]

from qshield_risk.actions import apply_actions
from qshield_risk.costs import CostRates, transaction_costs
from qshield_risk.evaluate import confidence_levels, required_float
from qshield_risk.metrics import RiskMetrics, alpha_key, risk_metrics_from_wealth
from qshield_risk.paths import portfolio_wealth_paths, validate_scenario_cube
from qshield_risk.portfolio import align_portfolio_weights, validate_ticker_order


@dataclass(frozen=True)
class EffectsResult:
    """Pure Risk-stage result before artifact serialization.

    ``actions`` contains canonical columns ``action_id,ticker,g,c`` and ``pairs`` contains one
    ``action_i,action_j,C_ij`` row for each ``i < j``. Values are raw decimal-NAV units.
    """
    baseline: RiskMetrics
    actions: pd.DataFrame
    pairs: pd.DataFrame


def build_effects(
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
) -> EffectsResult:
    """Compute the baseline and raw ``g_i``, ``C_ij``, ``c_i`` QUBO handoff.

    ``g_i = CVaR_0 - CVaR_i_gross`` and ``R_ij = CVaR_0 - CVaR_ij_gross`` are calculated after
    moving sale proceeds to cash but before deducting transaction costs. Pair interaction is
    ``C_ij = g_i + g_j - R_ij``. Cost ``c_i`` is emitted separately so Quantum can weight it once;
    the final candidate must still be re-evaluated by :func:`qshield_risk.evaluate.evaluate`.

    No component scaling or composite financial objective is applied in Risk v1.
    """
    tickers = validate_ticker_order(ticker_order)
    cube = validate_scenario_cube(
        scenarios,
        expected_horizon=int(config.get("horizon_days", 20)),
        expected_assets=len(tickers),
    )
    tolerance = required_float(config, "weight_sum_tolerance")
    aligned = align_portfolio_weights(weights, tickers, cash_weight, tolerance=tolerance)
    reduction_pct = required_float(config, "action_reduction_pct")
    levels = confidence_levels(config)
    primary_key = alpha_key(required_float(config, "cvar_alpha"))
    cost_rates = CostRates.from_config(config)
    zero_rates = CostRates(0.0, 0.0, 0.0)

    baseline = risk_metrics_from_wealth(
        portfolio_wealth_paths(cube, aligned, cash_weight), levels
    )
    cvar_0 = baseline.cvar[primary_key]
    gains: dict[int, float] = {}
    action_rows: list[dict[str, Any]] = []

    for action_id, ticker in enumerate(tickers):
        bits = np.zeros(len(tickers), dtype=int)
        bits[action_id] = 1
        gross_trade = apply_actions(
            aligned,
            cash_weight,
            bits,
            reduction_pct=reduction_pct,
            rates=zero_rates,
            tolerance=tolerance,
        )
        metrics = risk_metrics_from_wealth(
            portfolio_wealth_paths(
                cube, gross_trade.stock_amounts, gross_trade.cash_amount
            ),
            levels,
        )
        gain = cvar_0 - metrics.cvar[primary_key]
        gains[action_id] = gain
        gross_sale = float(aligned[action_id] * reduction_pct)
        action_rows.append(
            {
                "action_id": action_id,
                "ticker": ticker,
                "g": gain,
                "c": transaction_costs(gross_sale, cost_rates).total,
            }
        )

    pair_rows: list[dict[str, Any]] = []
    for action_i, action_j in combinations(range(len(tickers)), 2):
        bits = np.zeros(len(tickers), dtype=int)
        bits[[action_i, action_j]] = 1
        gross_trade = apply_actions(
            aligned,
            cash_weight,
            bits,
            reduction_pct=reduction_pct,
            rates=zero_rates,
            tolerance=tolerance,
        )
        metrics = risk_metrics_from_wealth(
            portfolio_wealth_paths(
                cube, gross_trade.stock_amounts, gross_trade.cash_amount
            ),
            levels,
        )
        pair_reduction = cvar_0 - metrics.cvar[primary_key]
        pair_rows.append(
            {
                "action_i": action_i,
                "action_j": action_j,
                "C_ij": gains[action_i] + gains[action_j] - pair_reduction,
            }
        )

    return EffectsResult(
        baseline=baseline,
        actions=pd.DataFrame(action_rows),
        pairs=pd.DataFrame(pair_rows),
    )
