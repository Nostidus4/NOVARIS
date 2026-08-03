# Đỗ Ngọc Tân - ArtifactPaths — nơi DUY NHẤT sinh đường dẫn artifact cho cả hai mode dev/runs.
"""`ArtifactPaths` — nơi DUY NHẤT trong repo sinh đường dẫn `artifacts/...`.

Không cover `data/`, `reports/` — hai thư mục đó do `qshield_data`/CLI riêng của từng package tự
quản (không version theo run, xem CLAUDE.md quy tắc 8 và `docs/Structure.md` §3).

Hai chế độ (`configs/base.yaml` → `artifacts.mode`):
- `dev`  → `artifacts/dev/{stage}/{filename}` (đường dẫn cố định, lặp nhanh)
- `runs` → `artifacts/runs/{run_id}/outputs/{stage}/{filename}` (có version, bắt buộc từ ngày 4 sprint)

`Stage.QUBO` và `Stage.SOLVE` dùng chung thư mục `"optimization"` — khớp
`docs/architecture/data_contracts.md` (`artifacts/.../optimization/qaoa_result.json`, một file cho
cả hai chặng QUBO-formulation và solve).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qshield_contracts.enums import ArtifactMode, Stage

_STAGE_DIR: dict[Stage, str] = {
    Stage.REGIME: "regime",
    Stage.SCENARIOS: "scenarios",
    Stage.RISK: "risk",
    Stage.QUBO: "optimization",
    Stage.SOLVE: "optimization",
}


class ArtifactPaths:
    """Sinh đường dẫn artifact theo `artifacts.mode` trong config đã load (`Config`/`dict`)."""

    def __init__(self, config: dict[str, Any], run_id: str | None = None) -> None:
        artifacts_cfg = config.get("artifacts", {}) or {}
        self.mode = ArtifactMode(artifacts_cfg.get("mode", "dev"))
        self.artifacts_root = Path(artifacts_cfg.get("root", "artifacts"))
        self.run_id = run_id

        if self.mode == ArtifactMode.RUNS and not self.run_id:
            raise ValueError(
                "artifacts.mode='runs' cần run_id (sinh từ RunContext) — không được để trống."
            )

    @property
    def run_root(self) -> Path:
        """Thư mục gốc của run hiện tại — nơi `RunContext` ghi `config.json`/`logs.txt`/..."""
        if self.mode == ArtifactMode.DEV:
            return self.artifacts_root / "dev"
        return self.artifacts_root / "runs" / str(self.run_id)

    def stage_dir(self, stage: Stage) -> Path:
        """Thư mục chứa artifact của một `stage` — chưa tạo trên đĩa, dùng `ensure()` để tạo."""
        if self.mode == ArtifactMode.DEV:
            return self.artifacts_root / "dev" / _STAGE_DIR[stage]
        return (
            self.artifacts_root
            / "runs"
            / str(self.run_id)
            / "outputs"
            / _STAGE_DIR[stage]
        )

    def for_stage(self, stage: Stage, filename: str) -> Path:
        """Đường dẫn đầy đủ tới một file artifact — ví dụ:
        `for_stage(Stage.REGIME, "regime_daily.parquet")`.
        """
        return self.stage_dir(stage) / filename

    def ensure(self, stage: Stage) -> None:
        """`mkdir -p` cho thư mục của `stage` đó (và `run_root`, để `RunContext` ghi được ngay)."""
        self.run_root.mkdir(parents=True, exist_ok=True)
        self.stage_dir(stage).mkdir(parents=True, exist_ok=True)
