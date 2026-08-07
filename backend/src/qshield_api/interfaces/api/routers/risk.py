# Đỗ Ngọc Tân - POST /risk/cvar — gọi qshield_risk, không tính CVaR trực tiếp trong router.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from qshield_api.application.risk.dto import BaselineRiskDTO, ComputeCvarRequestDTO
from qshield_api.application.risk.use_cases.compute_cvar import compute_cvar
from qshield_api.deps import get_risk_calculator
from qshield_api.domain.risk.repository import RiskCalculator
from qshield_api.infrastructure.calculation.qshield_risk_calculator import (
    ScenarioCubeMissingError,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/cvar", response_model=BaselineRiskDTO)
def compute_cvar_endpoint(
    request: ComputeCvarRequestDTO,
    calculator: RiskCalculator = Depends(get_risk_calculator),
) -> BaselineRiskDTO:
    try:
        return compute_cvar(
            request.portfolio.weights, request.portfolio.cash_weight, calculator
        )
    except ScenarioCubeMissingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        # align_portfolio_weights / required_float raise ValueError cho input sai hình dạng — 422
        raise HTTPException(status_code=422, detail=str(exc)) from exc
