# Đỗ Ngọc Tân - OptimizeJobRequestDTO/QaoaResultViewDTO/OptimizeJobDTO.
from __future__ import annotations

from pydantic import BaseModel


class OptimizeJobRequestDTO(BaseModel):
    """Riêng cho `optimize` — KHÔNG dùng chung `PortfolioInputDTO` của feature `portfolio` (quyết
    định đã chốt, xem docs/architecture/backend_hexagonal_design.md §6.2)."""

    weights: dict[str, float]
    cash_weight: float = 0.0


class SubmitJobResponseDTO(BaseModel):
    job_id: str


class QaoaResultViewDTO(BaseModel):
    bitstring: str
    k_actions: int
    chosen_actions: list[int]
    requested_solver: str
    actual_solver: str
    exact_energy: float
    qaoa_energy_by_seed: dict[str, float]
    optimality_gap: float
    feasibility_rate: float
    true_cvar_before: float
    true_cvar_after: float
    shots: int
    backend: str
    runtime_seconds: float


class OptimizeJobDTO(BaseModel):
    job_id: str
    status: str
    created_at: str
    finished_at: str | None
    result: QaoaResultViewDTO | None
    error: str | None
