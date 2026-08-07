"""Repository boundary for workflow_update handoff artifacts."""

from __future__ import annotations

from typing import Protocol

from qshield_api.domain.workflow.entities import WorkflowArtifactView


class WorkflowRepository(Protocol):
    def get_summary(self) -> WorkflowArtifactView: ...
