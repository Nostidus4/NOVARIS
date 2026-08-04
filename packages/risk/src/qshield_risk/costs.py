"""Transaction-cost rates and decimal-NAV cost accounting."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CostRates:
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
        return self.fee + self.spread + self.liquidity_penalty

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
    gross_sales: float
    fee: float
    spread: float
    liquidity_penalty: float
    total: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def transaction_costs(gross_sales: float, rates: CostRates) -> CostBreakdown:
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
        total=fee + spread + liquidity,
    )
