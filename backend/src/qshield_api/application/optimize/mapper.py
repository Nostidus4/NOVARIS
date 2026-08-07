# Đỗ Ngọc Tân - domain OptimizeJob → DTO (trả qua API).
"""Chuyển "dict thô (qaoa_result.json) → domain `OptimizeResult`" KHÔNG nằm ở đây — đó là việc của
`infrastructure/runner/subprocess_optimize_runner.py` (infrastructure dịch dữ liệu ngoài thành
domain, application không được biết tới hình dạng file JSON thô — giữ đúng chiều phụ thuộc: chỉ
`infrastructure` được phép phụ thuộc `domain`, `application` không phụ thuộc `infrastructure`)."""

from __future__ import annotations

from qshield_api.application.optimize.dto import OptimizeJobDTO, QaoaResultViewDTO
from qshield_api.domain.optimize.entities import OptimizeJob


def optimize_job_to_dto(job: OptimizeJob) -> OptimizeJobDTO:
    result_dto = (
        QaoaResultViewDTO(
            bitstring=job.result.bitstring,
            k_actions=job.result.k_actions,
            chosen_actions=job.result.chosen_actions,
            requested_solver=job.result.requested_solver,
            actual_solver=job.result.actual_solver,
            exact_energy=job.result.exact_energy,
            qaoa_energy_by_seed=job.result.qaoa_energy_by_seed,
            optimality_gap=job.result.optimality_gap,
            feasibility_rate=job.result.feasibility_rate,
            true_cvar_before=job.result.true_cvar_before,
            true_cvar_after=job.result.true_cvar_after,
            shots=job.result.shots,
            backend=job.result.backend,
            runtime_seconds=job.result.runtime_seconds,
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
