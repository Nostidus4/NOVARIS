"""VaR, CVaR and portfolio-level risk summaries.

All tail metrics operate on loss in decimal NAV units: positive values mean losses.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def _validated_losses(losses: npt.ArrayLike) -> FloatArray:
    values = np.asarray(losses, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError(
            f"[risk.metrics] losses must be a non-empty 1D array, got shape={values.shape}."
        )
    if not np.isfinite(values).all():
        raise ValueError("[risk.metrics] losses contain NaN or infinite values.")
    return values


def validate_alpha(alpha: float) -> float:
    """Return a finite confidence level strictly inside the open interval ``(0, 1)``."""
    value = float(alpha)
    if not np.isfinite(value) or not 0.0 < value < 1.0:
        raise ValueError(f"[risk.metrics] alpha must be finite and in (0, 1), got {alpha!r}.")
    return value


def value_at_risk(losses: npt.ArrayLike, alpha: float) -> float:
    """Return the empirical loss quantile at confidence level ``alpha``."""
    values = _validated_losses(losses)
    level = validate_alpha(alpha)
    return float(np.quantile(values, level))


def conditional_value_at_risk(
    losses: npt.ArrayLike, alpha: float
) -> tuple[float, float, int]:
    """Return ``(VaR, CVaR, tail_count)`` using every loss tied at or above VaR."""
    values = _validated_losses(losses)
    var = value_at_risk(values, alpha)
    tail = values[values >= var]
    if tail.size == 0:  # Defensive: mathematically impossible for a finite non-empty sample.
        raise ValueError(f"[risk.metrics] no tail observations found at alpha={alpha}.")
    return var, float(tail.mean()), int(tail.size)


def alpha_key(alpha: float) -> str:
    """Stable JSON key for confidence levels such as 0.95, 0.975 and 0.99."""
    return format(validate_alpha(alpha), ".10g")


@dataclass(frozen=True)
class RiskMetrics:
    """Scenario-distribution risk summary in decimal pre-trade NAV units.

    VaR, CVaR and tail counts are keyed by stable confidence-level strings such as ``"0.95"``.
    ``worst_scenario_max_drawdown`` is the most negative running-peak drawdown across every path,
    and ``expected_horizon_return`` is the mean terminal simple return across scenarios.
    """
    expected_horizon_return: float
    worst_scenario_max_drawdown: float
    var: dict[str, float]
    cvar: dict[str, float]
    tail_counts: dict[str, int]
    scenario_count: int
    units: str = "decimal_nav"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def risk_metrics_from_wealth(
    wealth_paths: npt.ArrayLike,
    confidence_levels: Sequence[float],
    *,
    initial_nav: float = 1.0,
) -> RiskMetrics:
    """Compute horizon return, drawdown and loss-tail metrics from scenario wealth paths.

    Terminal simple return is ``terminal_wealth / initial_nav - 1`` and loss is its negative.
    Drawdown is calculated on wealth relative to a running peak that includes ``initial_nav``;
    it is never calculated directly from a return series.
    """
    from qshield_risk.drawdown import worst_scenario_max_drawdown

    wealth = np.asarray(wealth_paths, dtype=float)
    if wealth.ndim != 2 or wealth.shape[0] == 0 or wealth.shape[1] == 0:
        raise ValueError(
            "[risk.metrics] wealth_paths must have shape (scenario, horizon), "
            f"got {wealth.shape}."
        )
    if not np.isfinite(wealth).all():
        raise ValueError("[risk.metrics] wealth_paths contain NaN or infinite values.")
    if not np.isfinite(initial_nav) or initial_nav <= 0.0:
        raise ValueError(f"[risk.metrics] initial_nav must be positive, got {initial_nav!r}.")

    levels = tuple(dict.fromkeys(validate_alpha(level) for level in confidence_levels))
    if not levels:
        raise ValueError("[risk.metrics] at least one confidence level is required.")

    terminal_returns = wealth[:, -1] / initial_nav - 1.0
    losses = -terminal_returns
    var_by_level: dict[str, float] = {}
    cvar_by_level: dict[str, float] = {}
    counts: dict[str, int] = {}
    for level in levels:
        var, cvar, count = conditional_value_at_risk(losses, level)
        key = alpha_key(level)
        var_by_level[key] = var
        cvar_by_level[key] = cvar
        counts[key] = count

    return RiskMetrics(
        expected_horizon_return=float(terminal_returns.mean()),
        worst_scenario_max_drawdown=worst_scenario_max_drawdown(
            wealth, initial_nav=initial_nav
        ),
        var=var_by_level,
        cvar=cvar_by_level,
        tail_counts=counts,
        scenario_count=int(wealth.shape[0]),
    )
