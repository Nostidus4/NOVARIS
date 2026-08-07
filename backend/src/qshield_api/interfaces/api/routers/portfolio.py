# Đỗ Ngọc Tân - POST /portfolio/validate — không chứa công thức tài chính, chỉ validate & gọi package risk.
from __future__ import annotations

from fastapi import APIRouter, Depends

from qshield_api.application.portfolio.dto import PortfolioInputDTO, ValidationResultDTO
from qshield_api.application.portfolio.use_cases.validate_portfolio import (
    validate_portfolio,
)
from qshield_api.deps import get_universe_tickers, get_weight_sum_tolerance

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/validate", response_model=ValidationResultDTO)
def validate_portfolio_endpoint(
    portfolio: PortfolioInputDTO,
    valid_tickers: list[str] = Depends(get_universe_tickers),
    tolerance: float = Depends(get_weight_sum_tolerance),
) -> ValidationResultDTO:
    return validate_portfolio(
        portfolio, valid_tickers=valid_tickers, tolerance=tolerance
    )
