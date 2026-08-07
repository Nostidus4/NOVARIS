# Đỗ Ngọc Tân - Protocol OptimizeJobRepository — job tracking, KHÔNG phải artifact pipeline.
from __future__ import annotations

from typing import Protocol

from qshield_api.domain.optimize.entities import OptimizeJob


class OptimizeJobRepository(Protocol):
    def save(self, job: OptimizeJob) -> None: ...

    def get(self, job_id: str) -> OptimizeJob | None: ...

    def list(self) -> list[OptimizeJob]: ...
