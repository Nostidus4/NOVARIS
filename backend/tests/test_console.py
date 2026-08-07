from fastapi.testclient import TestClient

from qshield_api.application.console.dto import (
    ConsoleOverviewDTO,
    ConsoleShellDTO,
    PipelineStageDTO,
)
from qshield_api.deps import get_workflow_repository
from qshield_api.domain.workflow.entities import WorkflowArtifactView
from qshield_api.main import app


class _FakeWorkflowRepository:
    def get_summary(self) -> WorkflowArtifactView:
        return WorkflowArtifactView(
            profile_id="workflow_update_downstream",
            profile_status="NON_BASELINE_RUN",
            config_version="test-v1",
            stage_status={
                "data": "READY",
                "regime": "READY",
                "scenarios": "PASS",
                "risk_prepare": "READY",
                "qubo_model": "READY",
                "rerank_polish": "READY",
            },
            candidate_count=10,
            data_manifest={"data_version": "v1"},
            universe=[{"ticker": "FPT", "company_name": "FPT Corp"}],
            data_quality=[
                {"check_id": "DQ-001", "check_name": "dup", "status": "PASS"}
            ],
            adjusted_close_evidence=[{"ticker": "FPT"}],
            regime_summary={"champion": {"seed": 303}, "label_map": {"0": "stress"}},
            scenario_manifest={
                "num_scenarios": 5000,
                "primary": {"num_scenarios": 5000, "n_assets": 30},
            },
            candidates=[
                {
                    "rank": 1,
                    "ticker": "MWG",
                    "selected_top10": True,
                    "eligible_status": True,
                    "net_risk_score": 0.01,
                    "baseline_CVaR_contribution": 0.005,
                    "transaction_cost_estimate": 0.0001,
                    "liquidity_penalty": 0.0,
                    "reason": "eligible",
                    "current_weight": 0.03,
                }
            ],
            candidate_order={"candidate_count": 10},
            risk_summary={"scenario_count": 5000},
            qubo_model=None,
            exact_solution=None,
            qaoa_results=None,
            workflow_benchmark={
                "actual_solver": "exact",
                "exact_best_energy": -1.2,
                "mean_feasibility_rate": 1.0,
                "caveat": "exact is ground truth",
            },
            final_recommendation={
                "actual_solver": "exact",
                "true_cvar_before": 0.07,
                "true_cvar_after": 0.06,
                "true_cvar_relative_reduction": 0.14,
                "materiality_met": True,
                "transaction_cost": 0.0002,
                "turnover": 0.1,
                "constraints_passed": True,
                "warnings": ["NON_BASELINE_RUN"],
                "actions": [
                    {
                        "ticker": "MWG",
                        "bits": "11",
                        "polished_reduction": 0.3,
                        "quantum_reduction": 0.3,
                        "current_weight": 0.03,
                        "final_weight": 0.021,
                        "sell_value": 0.009,
                    }
                ],
            },
            true_benchmark=None,
        )


def test_console_shell_and_overview_map_workflow_fields() -> None:
    app.dependency_overrides[get_workflow_repository] = _FakeWorkflowRepository
    try:
        client = TestClient(app)
        shell = client.get("/console/shell")
        overview = client.get("/console/overview")
        risk = client.get("/console/risk")
        quantum = client.get("/console/quantum")
        data = client.get("/console/data")
    finally:
        app.dependency_overrides.clear()

    assert shell.status_code == 200
    shell_body = ConsoleShellDTO.model_validate(shell.json())
    assert shell_body.online is True
    assert shell_body.scenario_count == 5000
    assert shell_body.candidate_count == 10

    assert overview.status_code == 200
    overview_body = ConsoleOverviewDTO.model_validate(overview.json())
    assert overview_body.true_cvar_after == 0.06
    assert overview_body.top_actions[0].ticker == "MWG"
    assert len(overview_body.pipeline) == 6
    assert isinstance(overview_body.pipeline[0], PipelineStageDTO)

    assert risk.status_code == 200
    assert risk.json()["candidates"][0]["ticker"] == "MWG"
    assert quantum.status_code == 200
    assert quantum.json()["actual_solver"] == "exact"
    assert data.status_code == 200
    assert data.json()["checks_passed"] == 1
    assert data.json()["universe"][0]["ticker"] == "FPT"
