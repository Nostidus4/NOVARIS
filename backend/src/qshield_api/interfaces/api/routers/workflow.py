"""Read-only workflow_update status and artifact handoff endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from qshield_api.application.workflow.dto import WorkflowSummaryDTO, WorkflowSyncDTO
from qshield_api.application.workflow.use_cases.get_workflow_summary import (
    get_workflow_summary,
)
from qshield_api.application.workflow.use_cases.sync_workflow import (
    sync_workflow_to_supabase,
)
from qshield_api.config import get_config
from qshield_api.deps import get_file_workflow_repository, get_workflow_repository
from qshield_api.domain.workflow.repository import WorkflowRepository
from qshield_api.infrastructure.persistence.workflow_repository_impl import (
    FileWorkflowRepository,
)

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.get("/summary", response_model=WorkflowSummaryDTO)
def get_workflow_summary_endpoint(
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowSummaryDTO:
    return get_workflow_summary(repo)


@router.post("/sync", response_model=WorkflowSyncDTO)
def sync_workflow_endpoint(
    file_repo: FileWorkflowRepository = Depends(get_file_workflow_repository),
) -> WorkflowSyncDTO:
    """Push current on-disk artifacts into Supabase `workflow_snapshots`."""
    try:
        meta = sync_workflow_to_supabase(get_config(), file_repo)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Supabase sync failed. Ensure migration "
                "backend/supabase/migrations/001_workflow_snapshots.sql "
                f"has been applied. Underlying error: {exc}"
            ),
        ) from exc
    return WorkflowSyncDTO(**meta)
