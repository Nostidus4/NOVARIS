# Đỗ Ngọc Tân - ScenarioSummaryDTO.
from __future__ import annotations

from pydantic import BaseModel


class ScenarioValidationMetricDTO(BaseModel):
    target_regime: str
    metric: str
    scenario_value: float
    reference_value: float
    statistic: float
    verdict: str


class ScenarioSummaryDTO(BaseModel):
    gate_status: str
    target_regime: str
    evaluation_date: str
    num_scenarios: int
    horizon_days: int
    ticker_order: list[str]
    validation: list[ScenarioValidationMetricDTO]
    n_fail: int
