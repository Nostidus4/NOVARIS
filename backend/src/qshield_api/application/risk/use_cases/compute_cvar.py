# Đỗ Ngọc Tân - use case: chấm CVaR cho MỘT danh mục người dùng nhập — gọi RiskCalculator (port).
from __future__ import annotations

from qshield_api.application.risk.dto import BaselineRiskDTO
from qshield_api.application.risk.mapper import baseline_risk_to_dto
from qshield_api.domain.risk.entities import RiskPortfolioInput
from qshield_api.domain.risk.repository import RiskCalculator


def compute_cvar(
    weights: dict[str, float], cash_weight: float, calculator: RiskCalculator
) -> BaselineRiskDTO:
    portfolio = RiskPortfolioInput(weights=weights, cash_weight=cash_weight)
    view = calculator.compute(portfolio)
    return baseline_risk_to_dto(view)
