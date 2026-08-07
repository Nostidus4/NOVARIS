# Đỗ Ngọc Tân - FileRunRepository — implement RunRepository, đọc config.json/metrics.json/logs.txt thật.
from __future__ import annotations

from dataclasses import dataclass

from qshield_contracts.config import Config
from qshield_contracts.enums import ArtifactMode
from qshield_contracts.paths import ArtifactPaths

from qshield_api.domain.runs.entities import RunDetail, RunSummary
from qshield_api.infrastructure.persistence.artifact_reader import (
    build_paths,
    read_run_root_json,
    read_run_root_text_tail,
    run_root_exists,
)


@dataclass(frozen=True)
class FileRunRepository:
    """`mode: dev` chỉ có ĐÚNG MỘT run_root cố định (`artifacts/dev/`) — `list_runs()` trả về 1
    phần tử duy nhất (`run_id="dev"`) nếu đã có run nào ghi vào đó. `mode: runs` quét
    `artifacts/runs/*/` — mỗi thư mục con là một run_id thật."""

    cfg: Config

    def _mode(self) -> ArtifactMode:
        return ArtifactMode(str(self.cfg.get("artifacts", {}).get("mode", "dev")))

    def list_runs(self) -> list[RunSummary]:
        if self._mode() == ArtifactMode.DEV:
            detail = self.get_run("dev")
            return [] if detail is None else [self._detail_to_summary(detail)]

        paths = build_paths(self.cfg)
        runs_root = paths.artifacts_root / "runs"
        if not runs_root.exists():
            return []
        summaries = []
        for entry in sorted(runs_root.iterdir()):
            if not entry.is_dir():
                continue
            detail = self.get_run(entry.name)
            if detail is not None:
                summaries.append(self._detail_to_summary(detail))
        return summaries

    def get_run(self, run_id: str) -> RunDetail | None:
        mode = self._mode()
        run_id_for_paths = None if mode == ArtifactMode.DEV else run_id
        cfg_for_run = dict(self.cfg)
        paths = ArtifactPaths(cfg_for_run, run_id=run_id_for_paths)
        if not run_root_exists(paths):
            return None
        config_snapshot = read_run_root_json(paths, "config.json")
        metrics = read_run_root_json(paths, "metrics.json")
        logs_tail = read_run_root_text_tail(paths, "logs.txt")
        return RunDetail(
            run_id=run_id,
            mode=str(mode),
            config_snapshot=config_snapshot,
            metrics=metrics,
            logs_tail=logs_tail,
        )

    @staticmethod
    def _detail_to_summary(detail: RunDetail) -> RunSummary:
        return RunSummary(
            run_id=detail.run_id,
            mode=detail.mode,
            has_config_snapshot=detail.config_snapshot is not None,
            has_metrics=detail.metrics is not None,
            has_logs=bool(detail.logs_tail),
        )
