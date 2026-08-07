# Đỗ Ngọc Tân - PortfolioInputDTO/ValidationResultDTO.
from __future__ import annotations

from pydantic import BaseModel


class PortfolioInputDTO(BaseModel):
    weights: dict[str, float]
    cash_weight: float = 0.0


class ValidationResultDTO(BaseModel):
    valid: bool
    errors: list[str]
