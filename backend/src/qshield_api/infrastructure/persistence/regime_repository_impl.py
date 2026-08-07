# Đỗ Ngọc Tân - FileRegimeRepository — implement RegimeRepository, đọc regime_daily.parquet + regime_summary.json thật.
from __future__ import annotations

from dataclasses import dataclass

from qshield_contracts.config import Config
from qshield_contracts.enums import Stage

from qshield_api.domain.regime.entities import (
    RegimeCurrent,
    RegimeSnapshot,
    RegimeTimeline,
)
from qshield_api.infrastructure.persistence.artifact_reader import (
    build_paths,
    read_json,
    read_parquet,
)


class RegimeArtifactMissingError(RuntimeError):
    """`regime_daily.parquet`/`regime_summary.json` chưa tồn tại — chạy `qshield-ai regime` trước."""


@dataclass(frozen=True)
class FileRegimeRepository:
    cfg: Config

    def _snapshots(self) -> list[RegimeSnapshot]:
        paths = build_paths(self.cfg)
        frame = read_parquet(paths, Stage.REGIME, "regime_daily.parquet")
        if frame is None:
            raise RegimeArtifactMissingError(
                "regime_daily.parquet chưa có — chạy `qshield-ai regime` trước."
            )
        frame = frame.sort_values("date")
        return [
            RegimeSnapshot(
                date=str(row.date.date() if hasattr(row.date, "date") else row.date),
                regime=str(row.regime),
                prob_normal=float(row.prob_normal),
                prob_volatile=float(row.prob_volatile),
                prob_stress=float(row.prob_stress),
            )
            for row in frame.itertuples(index=False)
        ]

    def get_current(self) -> RegimeCurrent:
        paths = build_paths(self.cfg)
        summary = read_json(paths, Stage.REGIME, "regime_summary.json")
        if summary is None:
            raise RegimeArtifactMissingError(
                "regime_summary.json chưa có — chạy `qshield-ai regime` trước."
            )
        snapshots = self._snapshots()
        return RegimeCurrent(
            latest=snapshots[-1],
            gate_status=str(summary.get("gate_status", "UNKNOWN")),
            run_mode=str(summary.get("run_mode", "UNKNOWN")),
        )

    def get_timeline(self) -> RegimeTimeline:
        return RegimeTimeline(snapshots=self._snapshots())
