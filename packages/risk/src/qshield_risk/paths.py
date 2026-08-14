"""Scenario validation and buy-and-hold wealth paths for simple daily returns."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def validate_scenario_cube(
    scenarios: npt.ArrayLike,
    *,
    expected_horizon: int | None = None,
    expected_assets: int | None = None,
) -> FloatArray:
    """Validate and return a simple-return cube in ``(scenario, horizon, asset)`` order.

    ``expected_horizon`` and ``expected_assets`` enforce the locked Risk boundary when supplied.
    A simple return equal to or below ``-1`` is rejected because cumulative wealth would become
    non-positive and no longer represent the long-only cash-transfer action model.
    """
    cube = np.asarray(scenarios, dtype=float)
    if cube.ndim != 3 or 0 in cube.shape:
        raise ValueError(
            "[risk.paths] scenarios must have shape (scenario, horizon, asset), "
            f"got {cube.shape}."
        )
    if expected_horizon is not None and cube.shape[1] != expected_horizon:
        raise ValueError(
            f"[risk.paths] scenario horizon={cube.shape[1]} != expected {expected_horizon}."
        )
    if expected_assets is not None and cube.shape[2] != expected_assets:
        raise ValueError(
            f"[risk.paths] scenario assets={cube.shape[2]} != expected {expected_assets}."
        )
    if not np.isfinite(cube).all():
        raise ValueError("[risk.paths] scenarios contain NaN or infinite values.")
    invalid = np.argwhere(cube <= -1.0)
    if invalid.size:
        index = tuple(int(value) for value in invalid[0])
        raise ValueError(
            f"[risk.paths] simple return at index={index} is {cube[index]!r}; must be > -1."
        )
    return cube


def asset_growth_paths(scenarios: npt.ArrayLike) -> FloatArray:
    """Compound simple daily returns as ``cumprod(1 + r)`` for each asset path."""
    cube = validate_scenario_cube(scenarios)
    return np.asarray(np.cumprod(1.0 + cube, axis=1), dtype=np.float64)


def portfolio_wealth_paths(
    scenarios: npt.ArrayLike,
    stock_amounts: npt.ArrayLike,
    cash_amount: float,
) -> FloatArray:
    """Mark a one-time-rebalanced portfolio without daily rebalancing.

    ``stock_amounts`` and ``cash_amount`` are actual decimal-NAV amounts after the hedge, not
    normalized post-cost weights. Cash has zero return in Risk v1. The result has shape
    ``(scenario, horizon)`` and remains measured against pre-trade NAV=1.
    """
    cube = validate_scenario_cube(scenarios)
    return portfolio_wealth_from_growth(
        asset_growth_paths(cube), stock_amounts, cash_amount
    )


def portfolio_wealth_from_growth(
    growth_paths: npt.ArrayLike,
    stock_amounts: npt.ArrayLike,
    cash_amount: float,
) -> FloatArray:
    """Mark portfolio wealth from precomputed asset growth paths."""
    growth = np.asarray(growth_paths, dtype=float)
    if growth.ndim != 3 or 0 in growth.shape or not np.isfinite(growth).all():
        raise ValueError(
            "[risk.paths] growth_paths must be a finite non-empty 3D array."
        )
    stocks = np.asarray(stock_amounts, dtype=float)
    if stocks.ndim != 1 or stocks.shape[0] != growth.shape[2]:
        raise ValueError(
            f"[risk.paths] stock_amounts shape={stocks.shape} does not match "
            f"asset count={growth.shape[2]}."
        )
    if not np.isfinite(stocks).all() or np.any(stocks < 0.0):
        raise ValueError("[risk.paths] stock amounts must be finite and non-negative.")
    if not np.isfinite(cash_amount) or cash_amount < 0.0:
        raise ValueError(
            f"[risk.paths] cash amount must be finite and non-negative, got {cash_amount!r}."
        )
    return np.einsum("shi,i->sh", growth, stocks) + float(cash_amount)
