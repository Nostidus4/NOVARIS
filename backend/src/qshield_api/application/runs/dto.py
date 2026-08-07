# Đỗ Ngọc Tân - RunSummaryDTO/RunDetailDTO — pydantic, trả qua API.
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RunSummaryDTO(BaseModel):
    run_id: str
    mode: str
    has_config_snapshot: bool
    has_metrics: bool
    has_logs: bool


class RunDetailDTO(BaseModel):
    run_id: str
    mode: str
    config_snapshot: dict[str, Any] | None
    metrics: dict[str, Any] | None
    logs_tail: list[str]
