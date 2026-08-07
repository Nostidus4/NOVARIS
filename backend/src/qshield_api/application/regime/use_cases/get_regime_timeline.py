# Đỗ Ngọc Tân - use case: toàn bộ regime_daily.parquet.
from __future__ import annotations

from qshield_api.application.regime.dto import RegimeSnapshotDTO, RegimeTimelineDTO
from qshield_api.domain.regime.repository import RegimeRepository


def get_regime_timeline(repo: RegimeRepository) -> RegimeTimelineDTO:
    timeline = repo.get_timeline()
    return RegimeTimelineDTO(
        snapshots=[
            RegimeSnapshotDTO(
                date=s.date,
                regime=s.regime,
                prob_normal=s.prob_normal,
                prob_volatile=s.prob_volatile,
                prob_stress=s.prob_stress,
            )
            for s in timeline.snapshots
        ]
    )
