# Đỗ Ngọc Tân - ScenarioSummary — đọc lại scenario_manifest.json + scenario_validation.csv.
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioValidationMetric:
    """Một dòng `scenario_validation.csv` — CLAUDE.md quy tắc 15: không tin cube nếu chưa PASS."""

    target_regime: str
    metric: str
    scenario_value: float
    reference_value: float
    statistic: float
    verdict: str  # PASS | FAIL


@dataclass(frozen=True)
class ScenarioSummary:
    gate_status: str
    target_regime: str
    evaluation_date: str
    num_scenarios: int
    horizon_days: int
    ticker_order: list[str]
    validation: list[ScenarioValidationMetric]
