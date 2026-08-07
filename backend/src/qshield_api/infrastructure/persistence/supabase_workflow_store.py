"""Persist / load workflow_update summary payloads in Supabase (no finance recompute)."""

from __future__ import annotations

import logging
import os
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from qshield_contracts.config import Config
from qshield_contracts.paths import ArtifactPaths

from qshield_api.domain.workflow.entities import WorkflowArtifactView
from qshield_api.infrastructure.persistence.supabase_client import get_supabase_client
from supabase import Client

logger = logging.getLogger(__name__)

TABLE = "workflow_snapshots"


def workflow_run_key(cfg: Config) -> str:
    paths = ArtifactPaths(cfg)
    profile_id = str((cfg.get("profile") or {}).get("id", "unknown"))
    return f"{paths.mode.value}:{profile_id}"


def view_to_payload(view: WorkflowArtifactView) -> dict[str, Any]:
    return asdict(view)


def payload_to_view(payload: dict[str, Any]) -> WorkflowArtifactView:
    return WorkflowArtifactView(
        profile_id=str(payload.get("profile_id", "")),
        profile_status=str(payload.get("profile_status", "")),
        config_version=str(payload.get("config_version", "")),
        stage_status=dict(payload.get("stage_status") or {}),
        candidate_count=int(payload.get("candidate_count") or 0),
        data_manifest=payload.get("data_manifest"),
        universe=list(payload.get("universe") or []),
        data_quality=list(payload.get("data_quality") or []),
        adjusted_close_evidence=list(payload.get("adjusted_close_evidence") or []),
        regime_summary=payload.get("regime_summary"),
        scenario_manifest=payload.get("scenario_manifest"),
        candidates=list(payload.get("candidates") or []),
        candidate_order=payload.get("candidate_order"),
        risk_summary=payload.get("risk_summary"),
        qubo_model=payload.get("qubo_model"),
        exact_solution=payload.get("exact_solution"),
        qaoa_results=payload.get("qaoa_results"),
        workflow_benchmark=payload.get("workflow_benchmark"),
        final_recommendation=payload.get("final_recommendation"),
        true_benchmark=payload.get("true_benchmark"),
    )


def sync_workflow_snapshot(
    cfg: Config,
    view: WorkflowArtifactView,
    *,
    client: Client | None = None,
) -> dict[str, Any]:
    """Upsert one workflow summary row. Returns metadata for the API response."""
    sb = client or get_supabase_client()
    paths = ArtifactPaths(cfg)
    run_key = workflow_run_key(cfg)
    synced_at = datetime.now(UTC).isoformat()
    row = {
        "run_key": run_key,
        "mode": paths.mode.value,
        "profile_id": view.profile_id,
        "profile_status": view.profile_status,
        "config_version": view.config_version,
        "stage_status": view.stage_status,
        "candidate_count": view.candidate_count,
        "payload": view_to_payload(view),
        "synced_at": synced_at,
    }
    result = sb.table(TABLE).upsert(row, on_conflict="run_key").execute()
    data = (result.data or [row])[0]
    return {
        "run_key": run_key,
        "profile_id": view.profile_id,
        "profile_status": view.profile_status,
        "synced_at": data.get("synced_at", synced_at),
        "candidate_count": view.candidate_count,
    }


def load_workflow_snapshot(
    cfg: Config,
    *,
    client: Client | None = None,
) -> WorkflowArtifactView | None:
    """Return latest payload for this run_key, or None if missing."""
    sb = client or get_supabase_client()
    run_key = workflow_run_key(cfg)
    result = sb.table(TABLE).select("payload").eq("run_key", run_key).limit(1).execute()
    rows = result.data or []
    if not rows:
        return None
    payload = rows[0].get("payload")
    if not isinstance(payload, dict):
        return None
    return payload_to_view(payload)


def workflow_store_mode() -> str:
    """supabase (default) | file — set QSHIELD_WORKFLOW_STORE in backend/.env."""
    raw = (os.getenv("QSHIELD_WORKFLOW_STORE") or "supabase").strip().lower()
    return raw if raw in {"supabase", "file"} else "supabase"
