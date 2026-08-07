# Đỗ Ngọc Tân - Protocol ScenarioRepository.
from __future__ import annotations

from typing import Protocol

from qshield_api.domain.scenarios.entities import ScenarioSummary


class ScenarioRepository(Protocol):
    def get_summary(self) -> ScenarioSummary: ...
