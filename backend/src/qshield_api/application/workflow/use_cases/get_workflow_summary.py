"""Map persisted workflow artifacts to the API DTO without recomputing finance."""

from __future__ import annotations

from qshield_api.application.workflow.dto import WorkflowSummaryDTO
from qshield_api.domain.workflow.repository import WorkflowRepository


def get_workflow_summary(repo: WorkflowRepository) -> WorkflowSummaryDTO:
    view = repo.get_summary()
    return WorkflowSummaryDTO(
        profile_id=view.profile_id,
        profile_status=view.profile_status,
        config_version=view.config_version,
        stage_status=view.stage_status,
        candidate_count=view.candidate_count,
        data_manifest=view.data_manifest,
        universe=view.universe,
        data_quality=view.data_quality,
        adjusted_close_evidence=view.adjusted_close_evidence,
        regime_summary=view.regime_summary,
        scenario_manifest=view.scenario_manifest,
        candidates=view.candidates,
        candidate_order=view.candidate_order,
        risk_summary=view.risk_summary,
        qubo_model=view.qubo_model,
        exact_solution=view.exact_solution,
        qaoa_results=view.qaoa_results,
        workflow_benchmark=view.workflow_benchmark,
        final_recommendation=view.final_recommendation,
        true_benchmark=view.true_benchmark,
    )
