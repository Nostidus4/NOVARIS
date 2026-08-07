# Đỗ Ngọc Tân - domain OptimizeJob → DTO.
from __future__ import annotations

from qshield_api.application.optimize.dto import (
    OptimizeJobDTO,
    WorkflowOptimizeResultDTO,
)
from qshield_api.domain.optimize.entities import OptimizeJob


def optimize_job_to_dto(job: OptimizeJob) -> OptimizeJobDTO:
    result_dto = (
        WorkflowOptimizeResultDTO(
            bitstring=job.result.bitstring,
            requested_solver=job.result.requested_solver,
            actual_solver=job.result.actual_solver,
            exact_energy=job.result.exact_energy,
            classical_energy=job.result.classical_energy,
            optimality_gap=job.result.optimality_gap,
            qaoa_beats_classical=job.result.qaoa_beats_classical,
            runtime_seconds=job.result.runtime_seconds,
            shots=job.result.shots,
            backend=job.result.backend,
            fallback_reason=job.result.fallback_reason,
            profile_id=job.result.profile_id,
            qubo_hash=job.result.qubo_hash,
            true_cvar_before=job.result.true_cvar_before,
            true_cvar_after=job.result.true_cvar_after,
            source_artifact=job.result.source_artifact,
        )
        if job.result is not None
        else None
    )
    return OptimizeJobDTO(
        job_id=job.job_id,
        status=str(job.status),
        created_at=job.created_at.isoformat(),
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        result=result_dto,
        error=job.error,
    )
