# Đỗ Ngọc Tân - use case: nhãn regime mới nhất.
from __future__ import annotations

from qshield_api.application.regime.dto import RegimeCurrentDTO, RegimeSnapshotDTO
from qshield_api.domain.regime.repository import RegimeRepository


def get_current_regime(repo: RegimeRepository) -> RegimeCurrentDTO:
    current = repo.get_current()
    return RegimeCurrentDTO(
        latest=RegimeSnapshotDTO(
            date=current.latest.date,
            regime=current.latest.regime,
            prob_normal=current.latest.prob_normal,
            prob_volatile=current.latest.prob_volatile,
            prob_stress=current.latest.prob_stress,
        ),
        gate_status=current.gate_status,
        run_mode=current.run_mode,
    )
