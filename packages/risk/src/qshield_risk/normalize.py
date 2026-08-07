"""Risk v1 deliberately hands QUBO raw decimal-NAV effects without scaling."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def raw_decimal_nav(values: npt.ArrayLike) -> npt.NDArray[np.float64]:
    """Return a finite float copy and make the no-normalization v1 policy explicit."""
    result = np.asarray(values, dtype=float)
    if not np.isfinite(result).all():
        raise ValueError(
            "[risk.normalize] effect values contain NaN or infinite values."
        )
    return result.copy()
