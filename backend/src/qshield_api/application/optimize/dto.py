# Đỗ Ngọc Tân - Optimize DTOs (workflow_update).
from __future__ import annotations

from pydantic import BaseModel


class OptimizeJobRequestDTO(BaseModel):
    """Job luôn chạy trên handoff Risk có sẵn trên đĩa — KHÔNG re-price theo `weights` này (đó là
    việc của `packages/risk`, ngoài phạm vi backend). `weights`/`cash_weight` chỉ được dùng để đối
    chiếu với handoff và trả về `personalization_status` trung thực trong kết quả job (P0-5).
    """

    weights: dict[str, float]
    cash_weight: float = 0.0


class SubmitJobResponseDTO(BaseModel):
    job_id: str


class WorkflowOptimizeResultDTO(BaseModel):
    bitstring: str
    requested_solver: str
    actual_solver: str
    exact_energy: float
    classical_energy: float | None = None
    optimality_gap: float | None = None
    qaoa_beats_classical: bool = False
    runtime_seconds: float
    shots: int | None = None
    backend: str
    fallback_reason: str | None = None
    profile_id: str | None = None
    qubo_hash: str | None = None
    true_cvar_before: float | None = None
    true_cvar_after: float | None = None
    source_artifact: str
    personalization_status: str
    personalization_note: str | None = None
    requested_portfolio_hash: str
    evaluated_portfolio_hash: str


class OptimizeJobDTO(BaseModel):
    job_id: str
    status: str
    created_at: str
    finished_at: str | None
    result: WorkflowOptimizeResultDTO | None
    error: str | None
