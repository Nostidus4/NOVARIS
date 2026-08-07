# Đỗ Ngọc Tân - FileScenarioRepository — implement ScenarioRepository, đọc scenario_manifest.json + scenario_validation.csv thật.
from __future__ import annotations

from dataclasses import dataclass

from qshield_contracts.config import Config
from qshield_contracts.enums import Stage

from qshield_api.domain.scenarios.entities import (
    ScenarioSummary,
    ScenarioValidationMetric,
)
from qshield_api.infrastructure.persistence.artifact_reader import (
    build_paths,
    read_csv,
    read_json,
)


class ScenarioArtifactMissingError(RuntimeError):
    """`scenario_manifest.json` chưa tồn tại — chạy `qshield-ai scenarios` trước."""


@dataclass(frozen=True)
class FileScenarioRepository:
    cfg: Config

    def get_summary(self) -> ScenarioSummary:
        paths = build_paths(self.cfg)
        manifest = read_json(paths, Stage.SCENARIOS, "scenario_manifest.json")
        if manifest is None:
            raise ScenarioArtifactMissingError(
                "scenario_manifest.json chưa có — chạy `qshield-ai scenarios` trước."
            )
        validation_frame = read_csv(paths, Stage.SCENARIOS, "scenario_validation.csv")
        metrics = (
            [
                ScenarioValidationMetric(
                    target_regime=str(row.target_regime),
                    metric=str(row.metric),
                    scenario_value=float(row.scenario_value),
                    reference_value=float(row.reference_value),
                    statistic=float(row.statistic),
                    verdict=str(row.verdict),
                )
                for row in validation_frame.itertuples(index=False)
            ]
            if validation_frame is not None
            else []
        )
        return ScenarioSummary(
            gate_status=str(manifest.get("gate_status", "UNKNOWN")),
            target_regime=str(manifest.get("target_regime", "unknown")),
            evaluation_date=str(manifest.get("evaluation_date", "unknown")),
            num_scenarios=int(manifest.get("num_scenarios", 0)),
            horizon_days=int(manifest.get("horizon_days", 0)),
            ticker_order=list(manifest.get("ticker_order", [])),
            validation=metrics,
        )
