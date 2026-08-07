# Đỗ Ngọc Tân - use case: đọc trạng thái job. Trả None nếu không tồn tại — router tự quyết 404.
from __future__ import annotations

from qshield_api.application.optimize.dto import OptimizeJobDTO
from qshield_api.application.optimize.mapper import optimize_job_to_dto
from qshield_api.domain.optimize.repository import OptimizeJobRepository


def get_job_status(
    job_id: str, job_repo: OptimizeJobRepository
) -> OptimizeJobDTO | None:
    job = job_repo.get(job_id)
    if job is None:
        return None
    return optimize_job_to_dto(job)
