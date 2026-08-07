"""Read workflow_update artifacts through ArtifactPaths; never recompute finance."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from qshield_contracts.config import Config
from qshield_contracts.enums import Stage

from qshield_api.domain.workflow.entities import WorkflowArtifactView
from qshield_api.infrastructure.persistence.artifact_reader import (
    build_paths,
    read_config_csv,
    read_config_json,
    read_csv,
    read_json,
)
from qshield_api.infrastructure.persistence.supabase_workflow_store import (
    load_workflow_snapshot,
    workflow_store_mode,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileWorkflowRepository:
    cfg: Config

    def get_summary(self) -> WorkflowArtifactView:
        paths = build_paths(self.cfg)
        data_manifest = read_config_json(
            self.cfg, "data_root", "metadata/data_manifest.json"
        )
        data_quality = read_config_csv(
            self.cfg, "reports_root", "data_quality_report.csv"
        )
        adjusted_close_evidence = read_config_csv(
            self.cfg, "reports_root", "adjusted_close_evidence_report.csv"
        )
        data_cfg = dict(self.cfg.get("data") or {})
        snapshot = str(
            data_cfg.get("snapshot_date", data_cfg.get("universe_as_of", ""))
        ).replace("-", "")
        universe = (
            read_config_csv(
                self.cfg,
                "data_root",
                f"metadata/universe_30_asof_{snapshot}.csv",
            )
            if snapshot
            else None
        )
        regime_summary = read_json(paths, Stage.REGIME, "regime_summary.json")
        scenario_manifest = read_json(paths, Stage.SCENARIOS, "scenario_manifest.json")
        candidates = read_csv(paths, Stage.RISK, "candidate_top10.csv")
        candidate_order = read_json(paths, Stage.RISK, "candidate_order.json")
        risk_summary = read_json(paths, Stage.RISK, "risk_summary.json")
        qubo_model = read_json(paths, Stage.QUBO, "qubo_model.json")
        exact_solution = read_json(paths, Stage.QUBO, "exact_solution.json")
        qaoa_results = read_json(paths, Stage.QUBO, "qaoa_results.json")
        workflow_benchmark = read_json(paths, Stage.QUBO, "workflow_benchmark.json")
        final_recommendation = read_json(paths, Stage.RISK, "final_recommendation.json")
        true_benchmark = read_json(paths, Stage.RISK, "true_benchmark.json")

        profile = dict(self.cfg.get("profile") or {})
        identity = risk_summary or candidate_order or {}
        selected_count = 0
        if candidates is not None and "selected_top10" in candidates:
            selected = candidates["selected_top10"]
            selected_count = int(
                (
                    selected.astype(str).str.lower().isin({"true", "1", "yes"})
                    | (selected == True)
                ).sum()
            )

        def records(frame) -> list[dict]:
            if frame is None:
                return []
            clean = frame.astype(object).where(frame.notna(), None)
            return clean.to_dict(orient="records")

        return WorkflowArtifactView(
            profile_id=str(identity.get("profile_id", profile.get("id", ""))),
            profile_status=str(
                identity.get("profile_status", profile.get("status", ""))
            ),
            config_version=str(
                identity.get(
                    "config_version",
                    (self.cfg.get("provenance") or {}).get("config_version", ""),
                )
            ),
            stage_status={
                "data": "READY"
                if data_manifest is not None
                and data_quality is not None
                and universe is not None
                else "MISSING",
                "regime": "READY" if regime_summary else "MISSING",
                "scenarios": (
                    str(scenario_manifest.get("gate_status", "READY"))
                    if scenario_manifest
                    else "MISSING"
                ),
                "risk_prepare": "READY"
                if risk_summary and candidate_order
                else "MISSING",
                "qubo_model": "READY" if qubo_model else "MISSING",
                "exact": "READY" if exact_solution else "MISSING",
                "qaoa": "READY" if qaoa_results else "MISSING",
                "benchmark": "READY" if workflow_benchmark else "MISSING",
                "rerank_polish": "READY" if final_recommendation else "MISSING",
                "true_benchmark": "READY" if true_benchmark else "MISSING",
            },
            candidate_count=selected_count,
            data_manifest=data_manifest,
            universe=records(universe),
            data_quality=records(data_quality),
            adjusted_close_evidence=records(adjusted_close_evidence),
            regime_summary=regime_summary,
            scenario_manifest=scenario_manifest,
            candidates=records(candidates),
            candidate_order=candidate_order,
            risk_summary=risk_summary,
            qubo_model=qubo_model,
            exact_solution=exact_solution,
            qaoa_results=qaoa_results,
            workflow_benchmark=workflow_benchmark,
            final_recommendation=final_recommendation,
            true_benchmark=true_benchmark,
        )


@dataclass(frozen=True)
class SupabaseWorkflowRepository:
    """Prefer Supabase snapshot; fall back to files if DB empty/unavailable."""

    cfg: Config
    file_repo: FileWorkflowRepository

    def get_summary(self) -> WorkflowArtifactView:
        if workflow_store_mode() == "file":
            return self.file_repo.get_summary()
        try:
            view = load_workflow_snapshot(self.cfg)
        except Exception:
            logger.exception(
                "Supabase workflow_snapshots read failed — falling back to artifact files"
            )
            return self.file_repo.get_summary()
        if view is None:
            logger.info(
                "No workflow_snapshots row for this run_key — falling back to artifact files"
            )
            return self.file_repo.get_summary()
        return view
