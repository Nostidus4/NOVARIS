# Đỗ Ngọc Tân - đọc artifact thật qua ArtifactPaths — hàm tiện ích dùng chung, KHÔNG phải Protocol.
"""Nơi DUY NHẤT trong `backend/` gọi `qshield_contracts.paths.ArtifactPaths` trực tiếp (CLAUDE.md
quy tắc 8: đường dẫn artifact chỉ sinh từ đây). Các `*_repository_impl.py` khác gọi hàm ở đây, tự
mình không nối chuỗi path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from qshield_contracts.config import Config
from qshield_contracts.enums import Stage
from qshield_contracts.paths import ArtifactPaths


def build_paths(cfg: Config) -> ArtifactPaths:
    """`run_id=None` — đọc lại đường dẫn hiện tại của `artifacts.mode` trong config (thường
    `dev`); backend không tự sinh run_id mới khi chỉ ĐỌC (chỉ `optimize` mới tạo run_id riêng cho
    mỗi job, xem `infrastructure/runner/subprocess_optimize_runner.py`)."""
    return ArtifactPaths(cfg, run_id=None)


def read_json(
    paths: ArtifactPaths, stage: Stage, filename: str
) -> dict[str, Any] | None:
    path = paths.for_stage(stage, filename)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(paths: ArtifactPaths, stage: Stage, filename: str) -> pd.DataFrame | None:
    path = paths.for_stage(stage, filename)
    if not path.exists():
        return None
    return pd.read_csv(path)


def read_parquet(
    paths: ArtifactPaths, stage: Stage, filename: str
) -> pd.DataFrame | None:
    path = paths.for_stage(stage, filename)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def read_run_root_json(paths: ArtifactPaths, filename: str) -> dict[str, Any] | None:
    """`config.json`/`metrics.json` sống ở `run_root`, không phải thư mục 1 stage cụ thể (do
    `RunContext.write_config_snapshot`/`write_metrics` ghi — CLAUDE.md quy tắc 13)."""
    path = paths.run_root / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_run_root_text_tail(
    paths: ArtifactPaths, filename: str, n_lines: int = 20
) -> list[str]:
    path = paths.run_root / filename
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[-n_lines:]


def run_root_exists(paths: ArtifactPaths) -> bool:
    return Path(paths.run_root).exists()


def read_scenario_cube(paths: ArtifactPaths) -> tuple[np.ndarray, list[str]] | None:
    """Đọc `stress_scenarios.npz` + `ticker_order` (từ `scenario_manifest.json`) — dùng bởi
    `qshield_risk_calculator.py` và test. Trả `None` nếu chưa có (chưa chạy `qshield-ai
    scenarios`)."""
    cube_path = paths.for_stage(Stage.SCENARIOS, "stress_scenarios.npz")
    manifest = read_json(paths, Stage.SCENARIOS, "scenario_manifest.json")
    if not cube_path.exists() or manifest is None:
        return None
    with np.load(cube_path, allow_pickle=False) as data:
        cube = np.asarray(data["scenarios"], dtype=float)
    return cube, list(manifest.get("ticker_order", []))


def read_config_json(
    cfg: Config, root_key: str, relative_path: str
) -> dict[str, Any] | None:
    """Read a non-versioned Data/Report JSON path rooted in ``config.paths``."""
    root = Path((cfg.get("paths") or {}).get(root_key, ""))
    path = root / relative_path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_config_csv(
    cfg: Config, root_key: str, relative_path: str
) -> pd.DataFrame | None:
    """Read a non-versioned Data/Report CSV path rooted in ``config.paths``."""
    root = Path((cfg.get("paths") or {}).get(root_key, ""))
    path = root / relative_path
    if not path.exists():
        return None
    return pd.read_csv(path)
