# Đỗ Ngọc Tân - use case: liệt kê run.
from __future__ import annotations

from qshield_api.application.runs.dto import RunSummaryDTO
from qshield_api.domain.runs.repository import RunRepository


def list_runs(repo: RunRepository) -> list[RunSummaryDTO]:
    return [
        RunSummaryDTO(
            run_id=run.run_id,
            mode=run.mode,
            has_config_snapshot=run.has_config_snapshot,
            has_metrics=run.has_metrics,
            has_logs=run.has_logs,
        )
        for run in repo.list_runs()
    ]
