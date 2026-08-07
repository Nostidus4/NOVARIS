# Đỗ Ngọc Tân - POST /optimize/jobs → 202 + job_id ; GET .../{id} — chạy nền vì exact+QAOA có thể chậm.
"""`BackgroundTasks` (FastAPI) chỉ xuất hiện ở ĐÂY — `application/optimize/use_cases/submit_job.py`
không biết FastAPI tồn tại, đúng chiều phụ thuộc (`interfaces` → `application`, không ngược lại).
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from qshield_api.application.optimize.dto import (
    OptimizeJobDTO,
    OptimizeJobRequestDTO,
    SubmitJobResponseDTO,
)
from qshield_api.application.optimize.use_cases.get_job_status import get_job_status
from qshield_api.application.optimize.use_cases.submit_job import run_job, submit_job
from qshield_api.deps import get_optimize_job_repository, get_optimize_runner
from qshield_api.domain.optimize.repository import OptimizeJobRepository
from qshield_api.domain.optimize.runner import OptimizeRunner

router = APIRouter(prefix="/optimize", tags=["optimize"])


@router.post("/jobs", response_model=SubmitJobResponseDTO, status_code=202)
def submit_job_endpoint(
    request: OptimizeJobRequestDTO,
    background_tasks: BackgroundTasks,
    job_repo: OptimizeJobRepository = Depends(get_optimize_job_repository),
    runner: OptimizeRunner = Depends(get_optimize_runner),
) -> SubmitJobResponseDTO:
    response = submit_job(request, job_repo)
    background_tasks.add_task(run_job, response.job_id, job_repo, runner)
    return response


@router.get("/jobs/{job_id}", response_model=OptimizeJobDTO)
def get_job_endpoint(
    job_id: str,
    job_repo: OptimizeJobRepository = Depends(get_optimize_job_repository),
) -> OptimizeJobDTO:
    dto = get_job_status(job_id, job_repo)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' không tồn tại.")
    return dto
