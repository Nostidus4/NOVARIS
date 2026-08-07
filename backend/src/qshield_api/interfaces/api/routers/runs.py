# Đỗ Ngọc Tân - GET /runs, /runs/{run_id}.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from qshield_api.application.runs.dto import RunDetailDTO, RunSummaryDTO
from qshield_api.application.runs.use_cases.get_run_detail import get_run_detail
from qshield_api.application.runs.use_cases.list_runs import list_runs
from qshield_api.deps import get_run_repository
from qshield_api.domain.runs.repository import RunRepository

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunSummaryDTO])
def list_runs_endpoint(
    repo: RunRepository = Depends(get_run_repository),
) -> list[RunSummaryDTO]:
    return list_runs(repo)


@router.get("/{run_id}", response_model=RunDetailDTO)
def get_run_endpoint(
    run_id: str, repo: RunRepository = Depends(get_run_repository)
) -> RunDetailDTO:
    detail = get_run_detail(run_id, repo)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' không tồn tại.")
    return detail
