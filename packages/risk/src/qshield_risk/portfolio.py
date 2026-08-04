"""Portfolio boundary validation and ticker-order alignment."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import numpy.typing as npt


def validate_ticker_order(ticker_order: Sequence[str], *, expected_assets: int = 8) -> tuple[str, ...]:
    tickers = tuple(str(ticker) for ticker in ticker_order)
    if len(tickers) != expected_assets:
        raise ValueError(
            f"[risk.portfolio] ticker_order has {len(tickers)} entries; expected {expected_assets}."
        )
    if any(not ticker for ticker in tickers) or len(set(tickers)) != len(tickers):
        raise ValueError("[risk.portfolio] ticker_order must contain unique, non-empty tickers.")
    return tickers


def align_portfolio_weights(
    weights: Mapping[str, float],
    ticker_order: Sequence[str],
    cash_weight: float,
    *,
    tolerance: float,
) -> npt.NDArray[np.float64]:
    """Align a ticker-keyed portfolio to the cube order without normalizing it."""
    tickers = tuple(str(ticker) for ticker in ticker_order)
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError(
            f"[risk.portfolio] weight_sum_tolerance must be finite and non-negative, got {tolerance!r}."
        )
    missing = sorted(set(tickers) - set(weights))
    extra = sorted(set(weights) - set(tickers))
    if missing or extra:
        raise ValueError(
            f"[risk.portfolio] ticker mapping mismatch: missing={missing}, extra={extra}."
        )
    aligned = np.asarray([weights[ticker] for ticker in tickers], dtype=float)
    if not np.isfinite(aligned).all() or np.any(aligned < 0.0):
        raise ValueError("[risk.portfolio] stock weights must be finite and non-negative.")
    if not np.isfinite(cash_weight) or cash_weight < 0.0:
        raise ValueError(
            f"[risk.portfolio] cash_weight must be finite and non-negative, got {cash_weight!r}."
        )
    total = float(aligned.sum() + cash_weight)
    if abs(total - 1.0) > tolerance:
        raise ValueError(
            f"[risk.portfolio] stock weights + cash={total:.16g}; expected 1 within "
            f"tolerance={tolerance}. Input is not auto-normalized."
        )
    return aligned
