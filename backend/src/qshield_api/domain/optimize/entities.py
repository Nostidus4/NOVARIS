# Đỗ Ngọc Tân - OptimizeJob + OptimizeJobRequest + OptimizeResult.
"""`OptimizeResult` là bản domain-level của `qshield_contracts.schemas.optimization.QaoaResult`
(dataclass, không phải pydantic — domain không biết pydantic tồn tại). `application/optimize/
mapper.py` chuyển dict thô đọc từ `qaoa_result.json` → `OptimizeResult` → `QaoaResultView` (DTO).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OptimizeJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class OptimizeJobRequest:
    """Riêng cho `optimize` — xem ghi chú trong `domain/portfolio/entities.py::PortfolioInput`."""

    weights: dict[str, float]
    cash_weight: float


@dataclass(frozen=True)
class OptimizeResult:
    """Bản domain của `QaoaResult` (`qshield_contracts.schemas.optimization`) — field giữ nguyên
    tên/kiểu, chỉ đổi `dict[int, float]` thành `dict[str, float]` cho `qaoa_energy_by_seed` vì khoá
    JSON luôn là chuỗi."""

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


@dataclass(frozen=True)
class OptimizeJob:
    job_id: str
    status: OptimizeJobStatus
    created_at: datetime
    finished_at: datetime | None
    result: OptimizeResult | None
    error: str | None
