"""Sync local workflow artifacts into Supabase (no finance recompute)."""

from __future__ import annotations

from typing import Any

from qshield_contracts.config import Config

from qshield_api.domain.workflow.repository import WorkflowRepository
from qshield_api.infrastructure.persistence.supabase_workflow_store import (
    sync_workflow_snapshot,
)


def sync_workflow_to_supabase(
    cfg: Config,
    repo: WorkflowRepository,
) -> dict[str, Any]:
    """Read current summary (from file-backed repo) and upsert into Supabase."""
    view = repo.get_summary()
    return sync_workflow_snapshot(cfg, view)
