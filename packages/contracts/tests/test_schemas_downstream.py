from datetime import date

import pandas as pd
import pytest
from qshield_contracts.enums import SolverKind
from qshield_contracts.schemas.downstream import (
    ArtifactProvenance,
    CandidateOrder,
    CandidateOrderItem,
    FinalRecommendation,
    QuboModel,
    RecommendationAction,
    RiskSummary,
    SolverCandidate,
    SolverWorkflowResult,
    structured_sample_count,
    validate_bitstring,
    validate_candidate_order,
    validate_candidate_top10,
    validate_final_recommendation,
    validate_objective_samples,
    validate_qubo_model,
    validate_reranked_candidates,
    validate_risk_summary,
    validate_solver_workflow_result,
)


def _provenance() -> ArtifactProvenance:
    return ArtifactProvenance(
        run_id="run_test",
        profile_id="workflow_update_downstream",
        profile_status="NON_BASELINE_RUN",
        config_version="test-v1",
        config_hash="config-sha256",
    )


def test_generic_structured_counts_cover_provisional_and_target() -> None:
    assert structured_sample_count(16) == 137
    assert structured_sample_count(20) == 211


def test_generic_bitstring_validation() -> None:
    validate_bitstring("01" * 8, expected_bit_count=16)
    validate_bitstring("01" * 10, expected_bit_count=20)
    with pytest.raises(ValueError, match="expected 16"):
        validate_bitstring("0" * 15, expected_bit_count=16)
    with pytest.raises(ValueError, match="non-binary"):
        validate_bitstring("0" * 15 + "x", expected_bit_count=16)


def test_candidate_top10_accepts_explicit_underfilled_runtime() -> None:
    count = 8
    data = pd.DataFrame(
        {
            "run_id": ["run_test"] * count,
            "profile_id": ["workflow_update_downstream"] * count,
            "profile_status": ["NON_BASELINE_RUN"] * count,
            "config_version": ["test-v1"] * count,
            "config_hash": ["config-sha256"] * count,
            "rank": range(1, count + 1),
            "ticker": [f"T{i}" for i in range(count)],
            "current_weight": [0.1] * count,
            "eligible_status": [True] * count,
            "baseline_CVaR_contribution": [0.01] * count,
            "marginal_CVaR_reduction_10pct": [0.001] * count,
            "marginal_CVaR_reduction_20pct": [0.002] * count,
            "marginal_CVaR_reduction_30pct": [0.003] * count,
            "transaction_cost_estimate": [0.0001] * count,
            "liquidity_penalty": [0.0002] * count,
            "net_risk_score": [float(count - i) for i in range(count)],
            "selected_top10": [True] * count,
            "reason": ["ranked"] * count,
        }
    )
    assert len(validate_candidate_top10(data, expected_candidates=8)) == 8


def test_candidate_order_is_canonical_and_dimensioned() -> None:
    items = [
        CandidateOrderItem(i + 1, f"T{i}", 0.1, 0.01, 0.001, 0.002, 1.0 - i / 10)
        for i in range(8)
    ]
    order = CandidateOrder(_provenance(), items, 0.8, 8, 2, 16)
    validate_candidate_order(order)
    with pytest.raises(ValueError, match="bit dimensions"):
        validate_candidate_order(CandidateOrder(_provenance(), items, 0.8, 8, 2, 20))


def test_risk_summary_requires_loss_sign_and_matching_units() -> None:
    summary = RiskSummary(
        provenance=_provenance(),
        evaluation_date=date(2026, 8, 6),
        candidate_order_hash="order-hash",
        cvar_alpha_primary=0.95,
        scenario_count=2_000,
        loss_sign_convention="positive_is_loss",
        metrics={"CVaR_95": 0.05},
        metric_units={"CVaR_95": "fraction_of_nav"},
        target_cash_increment=0.1,
    )
    validate_risk_summary(summary)
    with pytest.raises(ValueError, match="positive_is_loss"):
        validate_risk_summary(
            RiskSummary(
                **{**summary.__dict__, "loss_sign_convention": "positive_is_return"}
            )
        )


def test_objective_samples_require_full_16_bit_structured_design() -> None:
    rows: list[dict[str, object]] = []
    zero = "0" * 16

    def add(bitstring: str, kind: str) -> None:
        rows.append(
            {
                "run_id": "run_test",
                "profile_id": "workflow_update_downstream",
                "profile_status": "NON_BASELINE_RUN",
                "config_version": "test-v1",
                "config_hash": "config-sha256",
                "candidate_order_hash": "order-hash",
                "bitstring": bitstring,
                "sample_kind": kind,
                "actions_json": "{}",
                "components_json": "{}",
                "scalar_objective": 0.0,
                "violations_json": "[]",
                "feasible": True,
                "seed": None,
                "policy_version": "policy-v1",
            }
        )

    add(zero, "intercept")
    for i in range(16):
        bits = list(zero)
        bits[i] = "1"
        add("".join(bits), "main_effect")
    for i in range(16):
        for j in range(i + 1, 16):
            bits = list(zero)
            bits[i] = bits[j] = "1"
            add("".join(bits), "pairwise_effect")

    validated = validate_objective_samples(pd.DataFrame(rows), expected_bit_count=16)
    assert len(validated) == 137


def test_qubo_and_solver_use_runtime_bit_count_and_hash() -> None:
    model = QuboModel(
        provenance=_provenance(),
        qubo_hash="qubo-hash",
        candidate_order_hash="order-hash",
        bit_count=16,
        constant=0.0,
        linear=[0.0] * 16,
        quadratic=[[0.0] * 16 for _ in range(16)],
        scales={"cvar": 1.0},
        penalties={"cash": 2.0},
        validation_metrics={"rank_correlation": 0.9},
        validation_passed=True,
    )
    validate_qubo_model(model)

    result = SolverWorkflowResult(
        provenance=_provenance(),
        qubo_hash=model.qubo_hash,
        solver=SolverKind.EXACT,
        solver_config={"method": "enumeration"},
        candidates=[SolverCandidate("0" * 16, 0.0, True, None)],
        bit_count=16,
        runtime_seconds=1.0,
        status="completed",
    )
    validate_solver_workflow_result(result)


def test_reranked_candidates_accept_generic_16_bit_rows() -> None:
    data = pd.DataFrame(
        {
            "run_id": ["run_test", "run_test"],
            "profile_id": ["workflow_update_downstream"] * 2,
            "profile_status": ["NON_BASELINE_RUN"] * 2,
            "config_version": ["test-v1"] * 2,
            "config_hash": ["config-sha256"] * 2,
            "qubo_hash": ["qubo-hash"] * 2,
            "rank": [1, 2],
            "bitstring": ["0" * 16, "1" + "0" * 15],
            "source_solver": ["exact", "qaoa"],
            "qubo_energy": [0.0, 0.1],
            "true_cvar": [0.04, 0.041],
            "transaction_cost": [0.0, 0.001],
            "turnover": [0.0, 0.01],
            "feasible": [True, True],
            "violations_json": ["[]", "[]"],
        }
    )
    assert len(validate_reranked_candidates(data, expected_bit_count=16)) == 2


def test_final_recommendation_enforces_mapping_zero_lock_and_weight_sum() -> None:
    actions = [
        RecommendationAction(
            ticker=f"T{i}",
            bits="00",
            quantum_reduction=0.0,
            polished_reduction=0.0,
            current_weight=0.1,
            sell_value=0.0,
            final_weight=0.1,
        )
        for i in range(8)
    ]
    recommendation = FinalRecommendation(
        provenance=_provenance(),
        requested_solver=SolverKind.QAOA,
        actual_solver=SolverKind.EXACT,
        evaluation_date=date(2026, 8, 6),
        candidate_order_hash="order-hash",
        qubo_hash="qubo-hash",
        actions=actions,
        candidate_count=8,
        bits_per_candidate=2,
        cash_before=0.1,
        cash_after=0.1,
        unchanged_weight_total=0.1,
        cvar_before={"0.95": 0.05},
        cvar_after={"0.95": 0.04},
        expected_return_before=0.01,
        expected_return_after=0.009,
        transaction_cost=0.0,
        turnover=0.0,
        constraints_passed=True,
        true_cvar_relative_reduction=0.20,
        materiality_met=True,
        improvement_claim_allowed=True,
    )
    validate_final_recommendation(recommendation)

    broken_actions = actions.copy()
    broken_actions[0] = RecommendationAction(
        ticker="T0",
        bits="00",
        quantum_reduction=0.0,
        polished_reduction=0.01,
        current_weight=0.1,
        sell_value=0.0,
        final_weight=0.1,
    )
    with pytest.raises(ValueError, match="Zero-action lock"):
        validate_final_recommendation(
            FinalRecommendation(
                **{
                    **recommendation.__dict__,
                    "actions": broken_actions,
                }
            )
        )

    with pytest.raises(ValueError, match="improvement_claim_allowed"):
        validate_final_recommendation(
            FinalRecommendation(
                **{
                    **recommendation.__dict__,
                    "true_cvar_relative_reduction": 0.005,
                    "materiality_met": False,
                    "improvement_claim_allowed": True,
                }
            )
        )


def test_gate_verdict_and_benchmark_report() -> None:
    from qshield_contracts.schemas.downstream import (
        BenchmarkReport,
        GateVerdict,
        SolverManifest,
        validate_benchmark_report,
        validate_gate_verdict,
        validate_transaction_cost_excludes_liquidity,
    )

    validate_gate_verdict(
        GateVerdict(
            gate_id="surrogate_gate",
            status="WARN",
            owner="Do Ngoc Tan",
            metrics={"mae": 0.01},
            notes=["provisional thresholds"],
        )
    )
    with pytest.raises(ValueError, match="exception_disclosure"):
        validate_gate_verdict(
            GateVerdict(gate_id="scenario_gate", status="EXCEPTION", owner="Phuc")
        )

    report = BenchmarkReport(
        provenance=_provenance(),
        qubo_hash="qubo-hash",
        candidate_order_hash="order-hash",
        solver_manifest=SolverManifest(
            shots=1024,
            registered_seeds=[101, 202],
            reps=1,
            optimizer="COBYLA",
            maxiter=200,
            backend="StatevectorSampler",
            package_versions={"qiskit": "2.0"},
            warm_start=True,
            seed_status={"101": "completed"},
            NON_FINAL_CONFIG=False,
        ),
        requested_solver="qaoa",
        actual_solver="exact",
        exact_best_energy=-1.0,
        qaoa_best_energy=None,
        classical_best_energy=-0.9,
        fallback_reason="QAOA timeout",
        runtime_seconds={"exact": 1.0, "qaoa": 0.0, "classical": 0.5},
    )
    validate_benchmark_report(report)

    with pytest.raises(ValueError, match="fallback_reason"):
        validate_benchmark_report(
            BenchmarkReport(
                **{**report.__dict__, "fallback_reason": None},
            )
        )

    validate_transaction_cost_excludes_liquidity(
        {
            "transaction_cost": {
                "fee": 0.0015,
                "spread": 0.001,
                "liquidity_penalty": 0.0005,
            },
            "financial_objective": {
                "components": {
                    "transaction_cost": {"weight": 0.25},
                    "liquidity_penalty": {"weight": 0.25},
                }
            },
        }
    )
