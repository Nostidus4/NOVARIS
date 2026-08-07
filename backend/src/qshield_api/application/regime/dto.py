# Đỗ Ngọc Tân - RegimeCurrentDTO/RegimeTimelineDTO.
from __future__ import annotations

from pydantic import BaseModel


class RegimeSnapshotDTO(BaseModel):
    date: str
    regime: str
    prob_normal: float
    prob_volatile: float
    prob_stress: float


class RegimeCurrentDTO(BaseModel):
    latest: RegimeSnapshotDTO
    gate_status: str
    run_mode: str


class RegimeTimelineDTO(BaseModel):
    snapshots: list[RegimeSnapshotDTO]
