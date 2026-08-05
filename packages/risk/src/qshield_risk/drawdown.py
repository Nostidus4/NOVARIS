"""Drawdown calculations on portfolio wealth, never directly on returns."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def drawdown_paths(
    wealth_paths: npt.ArrayLike, *, initial_nav: float = 1.0
) -> npt.NDArray[np.float64]:
    """Return scenario drawdowns after including the pre-trade initial NAV as a peak."""
    wealth = np.asarray(wealth_paths, dtype=float)
    if wealth.ndim != 2 or wealth.shape[0] == 0 or wealth.shape[1] == 0:
        raise ValueError(
            "[risk.drawdown] wealth_paths must have shape (scenario, horizon), "
            f"got {wealth.shape}."
        )
    if not np.isfinite(wealth).all():
        raise ValueError("[risk.drawdown] wealth_paths contain NaN or infinite values.")
    if not np.isfinite(initial_nav) or initial_nav <= 0.0:
        raise ValueError(f"[risk.drawdown] initial_nav must be positive, got {initial_nav!r}.")

    initial = np.full((wealth.shape[0], 1), float(initial_nav))
    with_initial = np.concatenate((initial, wealth), axis=1)
    running_peak = np.maximum.accumulate(with_initial, axis=1)
    drawdowns = with_initial / running_peak - 1.0
    return drawdowns[:, 1:]


def worst_scenario_max_drawdown(
    wealth_paths: npt.ArrayLike, *, initial_nav: float = 1.0
) -> float:
    """Return the most negative drawdown observed across all paths and dates."""
    return float(drawdown_paths(wealth_paths, initial_nav=initial_nav).min())
