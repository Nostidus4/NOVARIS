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

    ⚠️ Chưa dùng `OptimizeJobRequestDTO.weights` để tính lại risk cho danh mục tuỳ ý — hiện
    `qshield-quantum solve` đọc `action_effects.csv`/`pairwise_effects.csv` đã có sẵn trên đĩa
    (từ lần `qshield-risk effects` gần nhất, danh mục mẫu trong `configs/universe.yaml`), CHƯA
    re-price theo danh mục người dùng gửi lên trong request. Muốn làm đủ (validate portfolio →
    risk effects → quantum solve theo ĐÚNG danh mục request) là việc mở rộng sau, không phải thiếu
    sót ở bước này — ghi rõ để không hiểu nhầm request `weights` hiện có tác dụng.
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
