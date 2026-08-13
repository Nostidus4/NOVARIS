"""Versioned Risk V2 policy parsing and structured portfolio constraints."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from qshield_risk.actions import TradeState
from qshield_risk.metrics import RiskMetrics, alpha_key


@dataclass(frozen=True)
class ConstraintViolation:
    """One machine-readable policy violation kept separate from objective value."""

    code: str
    field: str
    observed: Any
    limit: Any
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finite_number(raw: Mapping[str, Any], key: str) -> float:
    value = raw.get(key)
    if value is None or not np.isfinite(float(value)):
        raise ValueError(f"[risk.policy] risk_policy.{key} must be explicit and finite.")
    return float(value)


@dataclass(frozen=True)
class RiskPolicy:
    """Approved or provisional portfolio constraints consumed by Risk V2."""

    policy_version: str
    status: str
    risk_appetite: str
    cash_min: float
    cash_max: float
    cvar_budget: float
    max_turnover: float
    do_not_sell: tuple[str, ...] = ()
    per_asset_reduction_caps: dict[str, float] | None = None
    per_asset_liquidity_caps: dict[str, float] | None = None
    minimum_trade_value: float | None = None
    p_stress: float | None = None
    regime_posterior: dict[str, float] | None = None

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> RiskPolicy | None:
        """Return ``None`` for compatibility configs without a Risk V2 policy."""
        raw = config.get("risk_policy")
        if raw is None:
            return None
        if not isinstance(raw, Mapping):
            raise TypeError("[risk.policy] risk_policy must be a mapping.")
        text_values = {}
        for key in ("policy_version", "status", "risk_appetite"):
            value = str(raw.get(key, "")).strip()
            if not value:
                raise ValueError(f"[risk.policy] risk_policy.{key} is required.")
            text_values[key] = value
        cash_min = _finite_number(raw, "cash_min")
        cash_max = _finite_number(raw, "cash_max")
        cvar_budget = _finite_number(raw, "cvar_budget")
        max_turnover = _finite_number(raw, "max_turnover")
        if not 0.0 <= cash_min <= cash_max <= 1.0:
            raise ValueError("[risk.policy] cash band must satisfy 0 <= min <= max <= 1.")
        if cvar_budget < 0.0:
            raise ValueError("[risk.policy] cvar_budget must be non-negative.")
        if not 0.0 <= max_turnover <= 1.0:
            raise ValueError("[risk.policy] max_turnover must be in [0, 1].")

        caps_raw = raw.get("per_asset_reduction_caps", {}) or {}
        if not isinstance(caps_raw, Mapping):
            raise TypeError("[risk.policy] per_asset_reduction_caps must be a mapping.")
        caps = {str(ticker): float(value) for ticker, value in caps_raw.items()}
        if any(not np.isfinite(value) or not 0.0 <= value <= 1.0 for value in caps.values()):
            raise ValueError("[risk.policy] per-asset caps must be finite and in [0, 1].")
        liquidity_raw = raw.get("per_asset_liquidity_caps", {}) or {}
        if not isinstance(liquidity_raw, Mapping):
            raise TypeError("[risk.policy] per_asset_liquidity_caps must be a mapping.")
        liquidity_caps = {
            str(ticker): float(value) for ticker, value in liquidity_raw.items()
        }
        if any(
            not np.isfinite(value) or not 0.0 <= value <= 1.0
            for value in liquidity_caps.values()
        ):
            raise ValueError(
                "[risk.policy] per-asset liquidity caps must be finite decimal-NAV values in [0, 1]."
            )

        minimum_raw = raw.get("minimum_trade_value")
        minimum = None if minimum_raw is None else float(minimum_raw)
        if minimum is not None and (not np.isfinite(minimum) or minimum < 0.0):
            raise ValueError("[risk.policy] minimum_trade_value must be non-negative.")
        p_stress_raw = raw.get("p_stress")
        p_stress = None if p_stress_raw is None else float(p_stress_raw)
        if p_stress is not None and (not np.isfinite(p_stress) or not 0.0 <= p_stress <= 1.0):
            raise ValueError("[risk.policy] p_stress must be in [0, 1].")
        posterior_raw = raw.get("regime_posterior")
        posterior = None
        if posterior_raw is not None:
            if not isinstance(posterior_raw, Mapping):
                raise TypeError("[risk.policy] regime_posterior must be a mapping.")
            posterior = {str(name): float(value) for name, value in posterior_raw.items()}
            if (
                not posterior
                or any(not np.isfinite(value) or value < 0.0 for value in posterior.values())
                or not np.isclose(sum(posterior.values()), 1.0, atol=1e-8)
            ):
                raise ValueError("[risk.policy] regime_posterior must be non-negative and sum to 1.")
        return cls(
            **text_values,
            cash_min=cash_min,
            cash_max=cash_max,
            cvar_budget=cvar_budget,
            max_turnover=max_turnover,
            do_not_sell=tuple(str(ticker) for ticker in (raw.get("do_not_sell", ()) or ())),
            per_asset_reduction_caps=caps,
            per_asset_liquidity_caps=liquidity_caps,
            minimum_trade_value=minimum,
            p_stress=p_stress,
            regime_posterior=posterior,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def cash_band_deviation(self, cash_weight_after: float) -> float:
        """Distance to the nearest cash-band boundary, or zero inside the band."""
        if cash_weight_after < self.cash_min:
            return self.cash_min - cash_weight_after
        if cash_weight_after > self.cash_max:
            return cash_weight_after - self.cash_max
        return 0.0


def evaluate_policy_constraints(
    policy: RiskPolicy,
    *,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    reductions: npt.ArrayLike,
    trade: TradeState,
    after: RiskMetrics,
    primary_alpha: float,
    tolerance: float,
) -> tuple[ConstraintViolation, ...]:
    """Evaluate V2 hard/risk constraints without changing the objective or portfolio."""
    tickers = tuple(str(ticker) for ticker in ticker_order)
    values = np.asarray(reductions, dtype=float)
    violations: list[ConstraintViolation] = []

    def add(code: str, field: str, observed: Any, limit: Any, message: str) -> None:
        violations.append(ConstraintViolation(code, field, observed, limit, message))

    amount_total = float(trade.stock_amounts.sum() + trade.cash_amount)
    if abs(amount_total - trade.nav_after) > tolerance:
        add("ACCOUNTING_MISMATCH", "nav_after", amount_total, trade.nav_after, "Stock and cash amounts do not reconcile to NAV.")
    weight_total = float(trade.stock_weights.sum() + trade.cash_weight)
    if abs(weight_total - 1.0) > tolerance:
        add("WEIGHT_SUM", "weights_after", weight_total, 1.0, "Post-trade weights do not sum to one.")
    if trade.cash_weight < policy.cash_min - tolerance:
        add("CASH_BELOW_MIN", "cash_weight_after", trade.cash_weight, policy.cash_min, "Cash weight is below the policy floor.")
    if trade.cash_weight > policy.cash_max + tolerance:
        add("CASH_ABOVE_MAX", "cash_weight_after", trade.cash_weight, policy.cash_max, "Cash weight is above the policy ceiling.")
    if trade.turnover > policy.max_turnover + tolerance:
        add("TURNOVER_LIMIT", "turnover", trade.turnover, policy.max_turnover, "Turnover exceeds the policy maximum.")

    do_not_sell = set(policy.do_not_sell)
    caps = policy.per_asset_reduction_caps or {}
    liquidity_caps = policy.per_asset_liquidity_caps or {}
    for index, ticker in enumerate(tickers):
        reduction = float(values[index])
        if ticker in do_not_sell and reduction > tolerance:
            add("DO_NOT_SELL", ticker, reduction, 0.0, f"{ticker} is protected by do-not-sell policy.")
        cap = caps.get(ticker)
        if cap is not None and reduction > cap + tolerance:
            add("PER_ASSET_CAP", ticker, reduction, cap, f"{ticker} reduction exceeds its approved cap.")
        sale = float(weights[ticker]) * reduction
        liquidity_cap = liquidity_caps.get(ticker)
        if liquidity_cap is not None and sale > liquidity_cap + tolerance:
            add(
                "PER_ASSET_LIQUIDITY_CAP",
                ticker,
                sale,
                liquidity_cap,
                f"{ticker} sale exceeds its point-in-time liquidity capacity.",
            )
        if policy.minimum_trade_value is not None and tolerance < sale < policy.minimum_trade_value - tolerance:
            add("MINIMUM_TRADE_VALUE", ticker, sale, policy.minimum_trade_value, f"{ticker} sale is below the minimum trade value.")

    primary_key = alpha_key(primary_alpha)
    cvar_after = after.cvar[primary_key]
    if cvar_after > policy.cvar_budget + tolerance:
        add("CVAR_BUDGET", "cvar_after", cvar_after, policy.cvar_budget, "Post-trade CVaR exceeds the policy budget.")
    return tuple(violations)
