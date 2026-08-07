# Đỗ Ngọc Tân - Protocol RunRepository — port, implement thật ở infrastructure/persistence.
from __future__ import annotations

from typing import Protocol

from qshield_api.domain.runs.entities import RunDetail, RunSummary


class RunRepository(Protocol):
    def list_runs(self) -> list[RunSummary]: ...

    def get_run(self, run_id: str) -> RunDetail | None: ...
