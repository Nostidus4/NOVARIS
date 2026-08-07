# Đỗ Ngọc Tân - Protocol RegimeRepository.
from __future__ import annotations

from typing import Protocol

from qshield_api.domain.regime.entities import RegimeCurrent, RegimeTimeline


class RegimeRepository(Protocol):
    def get_current(self) -> RegimeCurrent: ...

    def get_timeline(self) -> RegimeTimeline: ...
