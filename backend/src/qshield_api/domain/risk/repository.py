# Đỗ Ngọc Tân - Protocol RiskCalculator — port gọi qshield_risk (đồng bộ, an toàn — xem §3 design doc).
from __future__ import annotations

from typing import Protocol

from qshield_api.domain.risk.entities import BaselineRiskView, RiskPortfolioInput


class RiskCalculator(Protocol):
    def compute(self, portfolio: RiskPortfolioInput) -> BaselineRiskView: ...
