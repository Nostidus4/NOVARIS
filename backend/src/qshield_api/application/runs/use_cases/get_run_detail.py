# Đỗ Ngọc Tân - use case: chi tiết 1 run. Trả None nếu không tồn tại — router tự quyết định 404.
from __future__ import annotations

from qshield_api.application.runs.dto import RunDetailDTO
from qshield_api.domain.runs.repository import RunRepository


def get_run_detail(run_id: str, repo: RunRepository) -> RunDetailDTO | None:
    detail = repo.get_run(run_id)
    if detail is None:
        return None
    return RunDetailDTO(
        run_id=detail.run_id,
        mode=detail.mode,
        config_snapshot=detail.config_snapshot,
        metrics=detail.metrics,
        logs_tail=detail.logs_tail,
    )
