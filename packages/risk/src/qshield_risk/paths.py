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
    """Compound simple returns independently for each scenario and asset."""
    cube = validate_scenario_cube(scenarios)
    return np.asarray(np.cumprod(1.0 + cube, axis=1), dtype=np.float64)


def portfolio_wealth_paths(
    scenarios: npt.ArrayLike,
    stock_amounts: npt.ArrayLike,
    cash_amount: float,
) -> FloatArray:
    """Mark a one-time-rebalanced portfolio through the horizon without daily rebalancing."""
    cube = validate_scenario_cube(scenarios)
    stocks = np.asarray(stock_amounts, dtype=float)
    if stocks.ndim != 1 or stocks.shape[0] != cube.shape[2]:
        raise ValueError(
            f"[risk.paths] stock_amounts shape={stocks.shape} does not match "
            f"asset count={cube.shape[2]}."
        )
    if not np.isfinite(stocks).all() or np.any(stocks < 0.0):
        raise ValueError("[risk.paths] stock amounts must be finite and non-negative.")
    if not np.isfinite(cash_amount) or cash_amount < 0.0:
        raise ValueError(
            f"[risk.paths] cash amount must be finite and non-negative, got {cash_amount!r}."
        )
    return np.einsum("shi,i->sh", asset_growth_paths(cube), stocks) + float(cash_amount)
