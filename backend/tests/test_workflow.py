from fastapi.testclient import TestClient

from qshield_api.deps import get_file_workflow_repository, get_workflow_repository
from qshield_api.domain.workflow.entities import WorkflowArtifactView
from qshield_api.main import app


class _FakeWorkflowRepository:
    def get_summary(self) -> WorkflowArtifactView:
        return WorkflowArtifactView(
            profile_id="workflow_update_downstream",
            profile_status="NON_BASELINE_RUN",
            config_version="test-v1",
            stage_status={"risk_prepare": "READY", "qaoa": "MISSING"},
            candidate_count=10,
            data_manifest={"data_version": "v1"},
            universe=[{"ticker": "FPT"}],
            data_quality=[{"check_id": "DQ-005", "status": "PASS"}],
            adjusted_close_evidence=[{"ticker": "FPT", "baseline_ok": False}],
            regime_summary={"champion_seed": 303},
            scenario_manifest={"num_scenarios": 5000},
            candidates=[{"ticker": "FPT", "selected_top10": True}],
            candidate_order={"candidate_count": 10},
            risk_summary={"scenario_count": 5000},
            qubo_model=None,
            exact_solution=None,
            qaoa_results=None,
            workflow_benchmark=None,
            final_recommendation=None,
            true_benchmark=None,
        )


def test_workflow_summary_exposes_partial_artifacts_without_recomputation() -> None:
    app.dependency_overrides[get_workflow_repository] = _FakeWorkflowRepository
    try:
        response = TestClient(app).get("/workflow/summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_status"] == "NON_BASELINE_RUN"
    assert payload["candidate_count"] == 10
    assert payload["stage_status"]["qaoa"] == "MISSING"
    assert payload["risk_summary"]["scenario_count"] == 5000
    assert payload["universe"][0]["ticker"] == "FPT"
    assert payload["scenario_manifest"]["num_scenarios"] == 5000


def test_workflow_sync_endpoint_uses_file_repo_and_returns_meta(monkeypatch) -> None:
    from qshield_api.interfaces.api.routers import workflow as workflow_router

    def _fake_sync(cfg, repo):
        assert repo is not None
        return {
            "run_key": "dev:workflow_update",
            "profile_id": "workflow_update",
            "profile_status": "NON_BASELINE_RUN",
            "synced_at": "2026-08-07T00:00:00+00:00",
            "candidate_count": 10,
        }

    monkeypatch.setattr(workflow_router, "sync_workflow_to_supabase", _fake_sync)
    app.dependency_overrides[get_file_workflow_repository] = _FakeWorkflowRepository
    try:
        response = TestClient(app).post("/workflow/sync")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["run_key"] == "dev:workflow_update"
    assert body["candidate_count"] == 10
