"""Read-only workflow_update artifact view; no financial calculations live here."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowArtifactView:
    profile_id: str
    profile_status: str
    config_version: str
    stage_status: dict[str, str]
    candidate_count: int
    data_manifest: dict[str, Any] | None
    universe: list[dict[str, Any]]
    data_quality: list[dict[str, Any]]
    adjusted_close_evidence: list[dict[str, Any]]
    regime_summary: dict[str, Any] | None
    scenario_manifest: dict[str, Any] | None
    candidates: list[dict[str, Any]]
    candidate_order: dict[str, Any] | None
    risk_summary: dict[str, Any] | None
    qubo_model: dict[str, Any] | None
    exact_solution: dict[str, Any] | None
    qaoa_results: dict[str, Any] | None
    workflow_benchmark: dict[str, Any] | None
    final_recommendation: dict[str, Any] | None
    true_benchmark: dict[str, Any] | None
