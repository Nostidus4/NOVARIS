# Đỗ Ngọc Tân - BaselineRiskView (domain, dataclass) → BaselineRiskDTO (pydantic).
from __future__ import annotations

from qshield_api.application.risk.dto import BaselineRiskDTO
from qshield_api.domain.risk.entities import BaselineRiskView


def baseline_risk_to_dto(view: BaselineRiskView) -> BaselineRiskDTO:
    return BaselineRiskDTO(
        alpha_primary=view.alpha_primary,
        var=view.var,
        cvar=view.cvar,
        expected_horizon_return=view.expected_horizon_return,
        worst_scenario_max_drawdown=view.worst_scenario_max_drawdown,
        scenario_count=view.scenario_count,
    )
