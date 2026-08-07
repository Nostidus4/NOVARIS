# Đỗ Ngọc Tân - BaselineRiskDTO — khớp qshield_contracts.schemas.risk.BaselineRisk + robustness levels.
from __future__ import annotations

from pydantic import BaseModel

from qshield_api.application.portfolio.dto import PortfolioInputDTO


class ComputeCvarRequestDTO(BaseModel):
    portfolio: PortfolioInputDTO


class BaselineRiskDTO(BaseModel):
    alpha_primary: str
    var: dict[str, float]
    cvar: dict[str, float]
    expected_horizon_return: float
    worst_scenario_max_drawdown: float
    scenario_count: int
