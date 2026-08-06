# Đỗ Ngọc Tân - định nghĩa 6 chặng: data → regime → scenarios → risk → qubo → solve.
"""Thứ tự chặng đã khóa theo Pipeline một chiều của CLAUDE.md:

    Data → Regime → Scenarios → Risk → QUBO → Exact/QAOA → CVaR after hedge

`QUBO` và `SOLVE` gộp thành MỘT lời gọi `uv run qshield-quantum solve` (khớp `ArtifactPaths`:
`Stage.QUBO`/`Stage.SOLVE` dùng chung thư mục `optimization/`, xem `qshield_contracts.paths`) —
nên `run.py` thực thi 5 bước lệnh, không phải 6 chặng khái niệm.
"""

from __future__ import annotations

STAGE_ORDER: tuple[str, ...] = ("data", "regime", "scenarios", "risk", "optimize")

STAGE_LABELS: dict[str, str] = {
    "data": "Data (qshield-data build)",
    "regime": "Regime (qshield-ai regime)",
    "scenarios": "Scenarios (qshield-ai scenarios)",
    "risk": "Risk (qshield-risk effects)",
    "optimize": "Optimize (qshield-quantum solve — QUBO + Exact/QAOA gộp)",
}
