"""Map hedge bitstrings to one-time position reductions and cash proceeds."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from qshield_risk.costs import CostBreakdown, CostRates, transaction_costs


def validate_bitstring(
    bitstring: npt.ArrayLike, *, n_assets: int
) -> npt.NDArray[np.int64]:
    """Return a binary action vector with exactly one entry per scenario asset.

    Position ``i`` always refers to position ``i`` in ``scenario_manifest.ticker_order``. This
    function validates representation only; the separate ``K=3`` cardinality rule is reported by
    :func:`qshield_risk.evaluate.evaluate` so infeasible Quantum candidates can still receive a
    true before/after risk score.
    """
    bits = np.asarray(bitstring)
    if bits.ndim != 1 or bits.shape[0] != n_assets:
        raise ValueError(
            f"[risk.actions] bitstring length/shape={bits.shape}; expected ({n_assets},)."
        )
    if not np.all(np.isin(bits, (0, 1))):
        raise ValueError(
            f"[risk.actions] bitstring must contain only 0/1, got {bits.tolist()}."
        )
    return bits.astype(np.int64, copy=False)


def selected_action_ids(bitstring: npt.ArrayLike, *, n_assets: int) -> tuple[int, ...]:
    """Return selected zero-based action ids in deterministic ticker-order sequence."""
    bits = validate_bitstring(bitstring, n_assets=n_assets)
    return tuple(int(index) for index in np.flatnonzero(bits))


@dataclass(frozen=True)
class TradeState:
    """Post-trade portfolio accounting in both amount and normalized-weight form.

    ``stock_amounts`` and ``cash_amount`` remain in pre-trade decimal-NAV units and therefore sum
    to ``nav_after``. ``stock_weights`` and ``cash_weight`` are normalized by ``nav_after`` and
    therefore sum to one. ``turnover`` is gross stock notional sold on pre-trade NAV=1.
    """

    stock_amounts: npt.NDArray[np.float64]
    cash_amount: float
    nav_after: float
    stock_weights: npt.NDArray[np.float64]
    cash_weight: float
    turnover: float
    costs: CostBreakdown


def apply_actions(
    stock_weights: npt.ArrayLike,
    cash_weight: float,
    bitstring: npt.ArrayLike,
    *,
    reduction_pct: float,
    rates: CostRates,
    tolerance: float,
) -> TradeState:
    """Execute selected sales once, before the scenario horizon, on pre-trade NAV=1.

    For each selected asset ``i``, gross sale is ``reduction_pct * current_weight_i``. Proceeds
    move to cash; fee and spread are deducted exactly once. Liquidity penalty remains a separate
    objective component under TL-008 and is not deducted from cash. The function
    does not rebalance again during the scenario horizon and never auto-normalizes invalid input.
    """
    stocks = np.asarray(stock_weights, dtype=float)
    if stocks.ndim != 1 or not np.isfinite(stocks).all() or np.any(stocks < 0.0):
        raise ValueError(
            "[risk.actions] stock_weights must be a finite non-negative 1D array."
        )
    if not np.isfinite(reduction_pct) or not 0.0 <= reduction_pct <= 1.0:
        raise ValueError(
            f"[risk.actions] reduction_pct must be in [0, 1], got {reduction_pct!r}."
        )
    bits = validate_bitstring(bitstring, n_assets=stocks.size)
    sales = stocks * float(reduction_pct) * bits
    gross_sales = float(sales.sum())
    costs = transaction_costs(gross_sales, rates)
    nav_after = 1.0 - costs.total
    cash_after = float(cash_weight + gross_sales - costs.total)
    stock_after = stocks - sales

    if nav_after <= 0.0 or cash_after < -tolerance:
        raise ValueError(
            f"[risk.actions] invalid post-trade accounting: nav_after={nav_after}, "
            f"cash_after={cash_after}, total_cost={costs.total}."
        )
    if abs(float(stock_after.sum() + cash_after) - nav_after) > tolerance:
        raise ValueError(
            "[risk.actions] stock + cash amounts do not reconcile to post-cost NAV."
        )

    normalized_stocks = stock_after / nav_after
    normalized_cash = max(cash_after, 0.0) / nav_after
    if abs(float(normalized_stocks.sum() + normalized_cash) - 1.0) > tolerance:
        raise ValueError(
            "[risk.actions] normalized post-trade weights do not sum to one."
        )

    return TradeState(
        stock_amounts=stock_after,
        cash_amount=max(cash_after, 0.0),
        nav_after=nav_after,
        stock_weights=normalized_stocks,
        cash_weight=float(normalized_cash),
        turnover=gross_sales,
        costs=costs,
    )


def apply_reductions(
    stock_weights: npt.ArrayLike,
    cash_weight: float,
    reductions: npt.ArrayLike,
    *,
    rates: CostRates,
    tolerance: float,
    maximum_reduction: float = 0.30,
) -> TradeState:
    """Apply one per-asset position reduction and reconcile final NAV.

    Reductions are fractions of each asset's current position, not percentage points of NAV.
    This is the generic accounting primitive for the four-level workflow and local polishing.
    """
    stocks = np.asarray(stock_weights, dtype=float)
    values = np.asarray(reductions, dtype=float)
    if stocks.ndim != 1 or not np.isfinite(stocks).all() or np.any(stocks < 0.0):
        raise ValueError(
            "[risk.actions] stock_weights must be a finite non-negative 1D array."
        )
    if values.shape != stocks.shape or not np.isfinite(values).all():
        raise ValueError(
            f"[risk.actions] reductions shape={values.shape}; expected finite {stocks.shape}."
        )
    if (
        not np.isfinite(maximum_reduction)
        or maximum_reduction < 0.0
        or np.any(values < 0.0)
        or np.any(values > maximum_reduction + max(tolerance, 1e-15))
    ):
        raise ValueError(
            "[risk.actions] reductions must be within "
            f"[0, {maximum_reduction}], got {values.tolist()}."
        )
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("[risk.actions] tolerance must be finite and non-negative.")

    sales = stocks * values
    gross_sales = float(sales.sum())
    costs = transaction_costs(gross_sales, rates)
    nav_after = 1.0 - costs.total
    cash_after = float(cash_weight + gross_sales - costs.total)
    stock_after = stocks - sales
    if nav_after <= 0.0 or cash_after < -tolerance:
        raise ValueError(
            f"[risk.actions] invalid post-trade accounting: nav_after={nav_after}, "
            f"cash_after={cash_after}, total_cost={costs.total}."
        )
    if abs(float(stock_after.sum() + cash_after) - nav_after) > tolerance:
        raise ValueError(
            "[risk.actions] stock + cash amounts do not reconcile to post-cost NAV."
        )

    normalized_stocks = stock_after / nav_after
    normalized_cash = max(cash_after, 0.0) / nav_after
    if abs(float(normalized_stocks.sum() + normalized_cash) - 1.0) > tolerance:
        raise ValueError(
            "[risk.actions] normalized post-trade weights do not sum to one."
        )
    return TradeState(
        stock_amounts=stock_after,
        cash_amount=max(cash_after, 0.0),
        nav_after=nav_after,
        stock_weights=normalized_stocks,
        cash_weight=float(normalized_cash),
        turnover=gross_sales,
        costs=costs,
    )
