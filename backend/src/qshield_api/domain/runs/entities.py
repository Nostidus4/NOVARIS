# Đỗ Ngọc Tân - RunSummary/RunDetail — khái niệm trình bày, không phải artifact tài chính.
"""Domain entity cho feature `runs`. KHÔNG chứa công thức tài chính (CLAUDE.md quy tắc 9) — chỉ
mô tả "một lần chạy trông như thế nào" khi đọc lại `config.json`/`metrics.json`/`logs.txt` do
`qshield_contracts.runs.RunContext` đã ghi (CLAUDE.md quy tắc 13).

Lưu ý đã biết: mỗi chặng (`regime`/`scenarios`/`risk`/`optimize`) ghi `metrics.json` vào CÙNG
`run_root` — đè lên nhau. `metrics` ở đây vì vậy chỉ phản ánh chặng CUỐI CÙNG đã chạy trong run đó,
không phải tổng hợp toàn bộ 5 chặng. Đây là giới hạn thật của `RunContext` hiện tại, không phải bug
ở lớp domain này — ghi rõ trong `RunDetail.metrics` để người đọc API không hiểu nhầm.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunSummary:
    """Một dòng trong danh sách run — đủ để hiển thị bảng, không có chi tiết đầy đủ."""

    run_id: str
    mode: str  # "dev" | "runs"
    has_config_snapshot: bool
    has_metrics: bool
    has_logs: bool


@dataclass(frozen=True)
class RunDetail:
    """Chi tiết một run — nội dung thật của `config.json`/`metrics.json`, không diễn giải thêm."""

    run_id: str
    mode: str
    config_snapshot: dict[str, Any] | None
    metrics: dict[str, Any] | None
    logs_tail: list[
        str
    ]  # vài dòng cuối logs.txt, không trả nguyên file (có thể rất dài)
