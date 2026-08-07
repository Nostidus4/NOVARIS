# Đỗ Ngọc Tân - use case: tạo job (đồng bộ) + chạy job (nền, do router lên lịch qua BackgroundTasks).
"""`submit_job()` chỉ làm phần ĐỒNG BỘ: sinh `job_id`, lưu `status=queued`, trả ngay cho router
(202). `run_job()` là phần NỀN thật sự — router lên lịch qua `BackgroundTasks.add_task(run_job,
...)` (FastAPI-specific, thuộc `interfaces/`, KHÔNG import ở đây — application không được biết
FastAPI tồn tại, giữ đúng chiều phụ thuộc)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from qshield_api.application.optimize.dto import (
    OptimizeJobRequestDTO,
    SubmitJobResponseDTO,
)
from qshield_api.domain.optimize.entities import OptimizeJob, OptimizeJobStatus
from qshield_api.domain.optimize.repository import OptimizeJobRepository
from qshield_api.domain.optimize.runner import OptimizeRunner


def submit_job(
    request: OptimizeJobRequestDTO, job_repo: OptimizeJobRepository
) -> SubmitJobResponseDTO:
    job_id = uuid.uuid4().hex
    job_repo.save(
        OptimizeJob(
            job_id=job_id,
            status=OptimizeJobStatus.QUEUED,
            created_at=datetime.now(UTC),
            finished_at=None,
            result=None,
            error=None,
        )
    )
    return SubmitJobResponseDTO(job_id=job_id)


def run_job(
    job_id: str,
    job_repo: OptimizeJobRepository,
    runner: OptimizeRunner,
) -> None:
    """Chạy nền — gọi từ `BackgroundTasks` của router `optimize.py`.

    ⚠️ `OptimizeJobRequestDTO.weights` chưa re-price Risk theo danh mục request. Job hiện gọi
    `qshield-quantum workflow --exact-only` trên handoff packages (`candidate_top10` /
    `qubo_objective_samples` / `risk_summary`) đã có trên đĩa. Muốn optimize đúng danh mục user
    gửi lên cần thêm bước prepare-workflow theo weights — mở rộng sau.
    """
    job = job_repo.get(job_id)
    if job is None:
        return
    job_repo.save(
        OptimizeJob(
            job_id=job_id,
            status=OptimizeJobStatus.RUNNING,
            created_at=job.created_at,
            finished_at=None,
            result=None,
            error=None,
        )
    )
    try:
        result = runner.run(job_id)
    except Exception as exc:  # noqa: BLE001 - job nền, phải bắt hết để ghi lại lỗi, không để mất job
        job_repo.save(
            OptimizeJob(
                job_id=job_id,
                status=OptimizeJobStatus.FAILED,
                created_at=job.created_at,
                finished_at=datetime.now(UTC),
                result=None,
                error=str(exc),
            )
        )
        return
    job_repo.save(
        OptimizeJob(
            job_id=job_id,
            status=OptimizeJobStatus.DONE,
            created_at=job.created_at,
            finished_at=datetime.now(UTC),
            result=result,
            error=None,
        )
    )
