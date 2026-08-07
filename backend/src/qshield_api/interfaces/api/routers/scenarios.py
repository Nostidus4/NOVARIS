# Đỗ Ngọc Tân - GET /scenarios/summary — đọc artifact, không tự tính.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from qshield_api.application.scenarios.dto import ScenarioSummaryDTO
from qshield_api.application.scenarios.use_cases.get_scenario_summary import (
    get_scenario_summary,
)
from qshield_api.deps import get_scenario_repository
from qshield_api.domain.scenarios.repository import ScenarioRepository
from qshield_api.infrastructure.persistence.scenario_repository_impl import (
    ScenarioArtifactMissingError,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/summary", response_model=ScenarioSummaryDTO)
def get_summary_endpoint(
    repo: ScenarioRepository = Depends(get_scenario_repository),
) -> ScenarioSummaryDTO:
    try:
        return get_scenario_summary(repo)
    except ScenarioArtifactMissingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
