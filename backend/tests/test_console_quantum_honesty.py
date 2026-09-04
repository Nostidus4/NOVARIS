# Đỗ Ngọc Tân - P0-6/P2-2/P2-3/P2-4: quantum page phải nói thật về solver và ràng buộc.
from __future__ import annotations

from qshield_api.application.console.assemble import assemble_quantum
from qshield_api.domain.workflow.entities import WorkflowArtifactView


def _view(
    *, risk_policy, quantum_constraints, final_recommendation
) -> WorkflowArtifactView:
    return WorkflowArtifactView(
        profile_id="workflow_update",
        profile_status="NON_BASELINE_RUN",
        config_version="test-v1",
        stage_status={},
        candidate_count=10,
        data_manifest=None,
        universe=[],
        data_quality=[],
        adjusted_close_evidence=[],
        regime_summary=None,
        scenario_manifest=None,
        candidates=[],
        candidate_order=None,
        risk_summary={
            "risk_policy": risk_policy,
            "quantum_constraints": quantum_constraints,
        },
        qubo_model=None,
        exact_solution=None,
        qaoa_results=None,
        workflow_benchmark={
            "actual_solver": "exact",
            "fallback_reason": "QAOA skipped/timeout in NON_FINAL_CONFIG",
        },
        final_recommendation=final_recommendation,
        true_benchmark=None,
    )


def test_constraints_not_evaluated_when_no_policy_or_constraints() -> None:
    view = _view(
        risk_policy=None,
        quantum_constraints={},
        final_recommendation={"constraints_passed": True},
    )
    dto = assemble_quantum(view)
    assert dto.constraints_evaluated is False
    # constraints_passed vẫn được truyền nguyên trạng — frontend chịu trách nhiệm không đọc nó
    # như PASS khi constraints_evaluated=False.
    assert dto.constraints_passed is True


def test_constraints_evaluated_true_when_policy_and_constraints_present() -> None:
    view = _view(
        risk_policy={"max_single_name": 0.1},
        quantum_constraints={"budget": {"k": 10}},
        final_recommendation={"constraints_passed": True},
    )
    dto = assemble_quantum(view)
    assert dto.constraints_evaluated is True


def test_fallback_reason_flows_through_to_dto() -> None:
    view = _view(
        risk_policy=None,
        quantum_constraints={},
        final_recommendation={"actual_solver": "exact"},
    )
    dto = assemble_quantum(view)
    assert dto.fallback_reason == "QAOA skipped/timeout in NON_FINAL_CONFIG"


def test_polishing_dependency_flows_through_to_dto() -> None:
    view = _view(
        risk_policy=None,
        quantum_constraints={},
        final_recommendation={"polishing_dependency": 0.83},
    )
    dto = assemble_quantum(view)
    assert dto.polishing_dependency == 0.83


def test_polishing_dependency_none_when_absent() -> None:
    view = _view(risk_policy=None, quantum_constraints={}, final_recommendation={})
    dto = assemble_quantum(view)
    assert dto.polishing_dependency is None


def test_assemble_quantum_offline_defaults() -> None:
    dto = assemble_quantum(None)
    assert dto.online is False
    assert dto.constraints_evaluated is False
    assert dto.fallback_reason is None
    assert dto.polishing_dependency is None
