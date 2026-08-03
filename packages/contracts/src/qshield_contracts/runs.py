# Đỗ Ngọc Tân - RunContext — tạo run_id, ghi config.json/data_version.json/metrics.json/logs.txt. Module tính toán khác không được tự ghi các file này.
"""`RunContext` — nơi DUY NHẤT trong repo ghi `config.json`, `data_version.json`, `metrics.json`,
`logs.txt` (CLAUDE.md quy tắc 13). Module tính toán (`packages/ai`, `risk`, `quantum`, ...) chỉ trả
về dữ liệu thuần; `pipeline`/CLI của từng package gọi `RunContext` để ghi metadata.

`run_id` luôn được sinh (kể cả ở `artifacts.mode: dev`) để dùng làm nhãn nhất quán trong
`logs.txt`/`metrics.json` — nhưng chỉ `mode: runs` mới tạo THƯ MỤC riêng theo `run_id`
(plan-contracts.md §6 câu 5).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from qshield_contracts.paths import ArtifactPaths


def _new_run_id() -> str:
    return f"run_{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}"


class RunContext:
    """Vòng đời một lần chạy pipeline: run_id + logger + ghi 4 file metadata chuẩn."""

    def __init__(self, config: dict[str, Any], artifact_paths: ArtifactPaths) -> None:
        self.config = config
        self.artifact_paths = artifact_paths
        self._run_id = artifact_paths.run_id or _new_run_id()
        self.artifact_paths.run_root.mkdir(parents=True, exist_ok=True)
        self._logger: logging.Logger | None = None

    @property
    def run_id(self) -> str:
        return self._run_id

    def logger(self, name: str) -> logging.Logger:
        """Logger ghi ra `{run_root}/logs.txt` (append) kèm console handler — tạo một lần, tái dùng
        cho các lần gọi sau trong cùng `RunContext`."""
        logger = logging.getLogger(f"qshield.{self.run_id}.{name}")
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            log_path = self.artifact_paths.run_root / "logs.txt"
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            formatter = logging.Formatter(
                "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.addHandler(logging.StreamHandler())
        return logger

    def write_config_snapshot(self) -> Path:
        """Ghi `config.json` — snapshot config đã dùng để chạy, để truy lại được run này sinh ra từ
        tham số nào (CLAUDE.md: "mọi số lên slide phải truy được về một run_id")."""
        out_path = self.artifact_paths.run_root / "config.json"
        out_path.write_text(
            json.dumps(dict(self.config), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return out_path

    def write_data_version(self, data_version: str) -> Path:
        out_path = self.artifact_paths.run_root / "data_version.json"
        out_path.write_text(
            json.dumps(
                {"run_id": self.run_id, "data_version": data_version},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return out_path

    def write_metrics(self, metrics: dict[str, Any]) -> Path:
        out_path = self.artifact_paths.run_root / "metrics.json"
        out_path.write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return out_path
