"""Transaction-cost rates and decimal-NAV cost accounting."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CostRates:
    """Approved non-negative cost rates applied to absolute gross sold notional.

    Rates are decimal fractions, not percentages. Production values must come from Config; this
    class deliberately provides no financial defaults.
    """

    fee: float
    spread: float
    liquidity_penalty: float

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(
                    f"[risk.costs] {name} must be finite and non-negative, got {value!r}."
                )

    @property
    def total_rate(self) -> float:
        """Cash transaction-cost rate (fee + spread). Liquidity is not included (TL-008)."""
        return self.fee + self.spread

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> CostRates:
        raw = config.get("transaction_cost")
        if not isinstance(raw, Mapping):
            raise TypeError("[risk.config] transaction_cost must be a mapping.")
        values: dict[str, float] = {}
        for key in ("fee", "spread", "liquidity_penalty"):
            value = raw.get(key)
            if value is None:
                raise ValueError(
                    f"[risk.config] transaction_cost.{key}=null; official Risk run requires "
                    "an approved explicit value."
                )
            values[key] = float(value)
        return cls(**values)


@dataclass(frozen=True)
class CostBreakdown:
    """Fee, spread (cash txn cost) and liquidity penalty in pre-trade NAV units.

    ``total`` is fee+spread only (TL-008). ``liquidity_penalty`` stays separate for objective
    scoring and must not be deducted again as if it were a second cash cost.
    """

    gross_sales: float
    fee: float
    spread: float
    liquidity_penalty: float
    total: float

    @property
    def cash_cost(self) -> float:
        return self.total

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def transaction_costs(gross_sales: float, rates: CostRates) -> CostBreakdown:
    """Calculate additive cost components for gross sales measured on pre-trade NAV=1."""
    if not np.isfinite(gross_sales) or gross_sales < 0.0:
        raise ValueError(
            f"[risk.costs] gross_sales must be finite and non-negative, got {gross_sales!r}."
        )
    fee = float(gross_sales * rates.fee)
    spread = float(gross_sales * rates.spread)
    liquidity = float(gross_sales * rates.liquidity_penalty)
    return CostBreakdown(
        gross_sales=float(gross_sales),
        fee=fee,
        spread=spread,
        liquidity_penalty=liquidity,
        total=fee + spread,
    )
