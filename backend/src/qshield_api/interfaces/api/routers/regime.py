# Đỗ Ngọc Tân - GET /regime/current, /regime/timeline — đọc artifact, không tự tính.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from qshield_api.application.regime.dto import RegimeCurrentDTO, RegimeTimelineDTO
from qshield_api.application.regime.use_cases.get_current_regime import (
    get_current_regime,
)
from qshield_api.application.regime.use_cases.get_regime_timeline import (
    get_regime_timeline,
)
from qshield_api.deps import get_regime_repository
from qshield_api.domain.regime.repository import RegimeRepository
from qshield_api.infrastructure.persistence.regime_repository_impl import (
    RegimeArtifactMissingError,
)

router = APIRouter(prefix="/regime", tags=["regime"])


@router.get("/current", response_model=RegimeCurrentDTO)
def get_current_endpoint(
    repo: RegimeRepository = Depends(get_regime_repository),
) -> RegimeCurrentDTO:
    try:
        return get_current_regime(repo)
    except RegimeArtifactMissingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/timeline", response_model=RegimeTimelineDTO)
def get_timeline_endpoint(
    repo: RegimeRepository = Depends(get_regime_repository),
) -> RegimeTimelineDTO:
    try:
        return get_regime_timeline(repo)
    except RegimeArtifactMissingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
