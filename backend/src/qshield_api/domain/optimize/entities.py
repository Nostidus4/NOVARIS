# Đỗ Ngọc Tân - OptimizeJob + OptimizeJobRequest + OptimizeResult (workflow_update).
"""`OptimizeResult` map từ artifact `workflow_benchmark.json` (+ optional true_benchmark),
không phụ thuộc schema legacy `qaoa_result.json` đơn lẻ.
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
    weights: dict[str, float]
    cash_weight: float


@dataclass(frozen=True)
class OptimizeResult:
    """Kết quả job optimize gắn packages `qshield-quantum workflow` (thường `--exact-only`)."""

    bitstring: str
    requested_solver: str
    actual_solver: str
    exact_energy: float
    classical_energy: float | None
    optimality_gap: float | None
    qaoa_beats_classical: bool
    runtime_seconds: float
    shots: int | None
    backend: str
    fallback_reason: str | None
    profile_id: str | None
    qubo_hash: str | None
    true_cvar_before: float | None
    true_cvar_after: float | None
    source_artifact: str
    # Personalization honesty (P0-5): job luôn chạy trên handoff Risk trên đĩa, KHÔNG re-price
    # theo `weights` request. Ba trường dưới đây nói rõ liệu handoff đó có khớp danh mục người
    # dùng gửi lên hay không — xem `infrastructure/runner/subprocess_optimize_runner.py`.
    personalization_status: str
    personalization_note: str | None
    requested_portfolio_hash: str
    evaluated_portfolio_hash: str


@dataclass(frozen=True)
class OptimizeJob:
    job_id: str
    status: OptimizeJobStatus
    created_at: datetime
    finished_at: datetime | None
    request: OptimizeJobRequest
    result: OptimizeResult | None
    error: str | None
