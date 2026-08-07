# Đỗ Ngọc Tân - use case: tóm tắt kịch bản + kết quả validation gate.
from __future__ import annotations

from qshield_api.application.scenarios.dto import (
    ScenarioSummaryDTO,
    ScenarioValidationMetricDTO,
)
from qshield_api.domain.scenarios.repository import ScenarioRepository


def get_scenario_summary(repo: ScenarioRepository) -> ScenarioSummaryDTO:
    summary = repo.get_summary()
    metrics = [
        ScenarioValidationMetricDTO(
            target_regime=m.target_regime,
            metric=m.metric,
            scenario_value=m.scenario_value,
            reference_value=m.reference_value,
            statistic=m.statistic,
            verdict=m.verdict,
        )
        for m in summary.validation
    ]
    return ScenarioSummaryDTO(
        gate_status=summary.gate_status,
        target_regime=summary.target_regime,
        evaluation_date=summary.evaluation_date,
        num_scenarios=summary.num_scenarios,
        horizon_days=summary.horizon_days,
        ticker_order=summary.ticker_order,
        validation=metrics,
        n_fail=sum(1 for m in metrics if m.verdict != "PASS"),
    )
