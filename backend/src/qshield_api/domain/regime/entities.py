# Đỗ Ngọc Tân - RegimeSnapshot/RegimeTimeline — đọc lại regime_daily.parquet + regime_summary.json.
"""Không chứa công thức HMM (đó là `packages/ai`) — chỉ mô tả hình dạng dữ liệu đã tính sẵn."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeSnapshot:
    """Một ngày trong `regime_daily.parquet`."""

    date: str
    regime: (
        str  # normal | volatile | stress (CLAUDE.md quy tắc 7 — đã gán theo thống kê)
    )
    prob_normal: float
    prob_volatile: float
    prob_stress: float


@dataclass(frozen=True)
class RegimeCurrent:
    """Nhãn regime mới nhất + trạng thái gate — đúng field `regime_summary.json` đang có thật."""

    latest: RegimeSnapshot
    gate_status: str
    run_mode: str  # "NON_BASELINE_RUN" | ... — không tự diễn giải, in nguyên


@dataclass(frozen=True)
class RegimeTimeline:
    snapshots: list[RegimeSnapshot]
