# Đỗ Ngọc Tân - contracts cho workflow bốn mức từ candidate selection đến recommendation.
"""Schemas for the profile-aware downstream four-level workflow.

These contracts deliberately parameterize candidate and bit counts. The provisional development
path is 8 candidates / 16 bits / 137 structured samples; the baseline target is 10 / 20 / 211.
Financial values are passed through from Risk outputs. This module validates shape, provenance,
ordering, and sign-neutral consistency only; it does not duplicate financial formulas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd
import pandera.pandas as pandera

from qshield_contracts.enums import SolverKind

_PROFILE_STATUSES = {"NON_BASELINE_RUN", "BASELINE_TARGET"}
_SOLVER_STATUSES = {"completed", "failed", "timeout"}
_SAMPLE_KINDS = {"intercept", "main_effect", "pairwise_effect", "validation", "random"}
_GATE_IDS = {
    "data_gate",
    "scenario_gate",
    "product_gate",
    "surrogate_gate",
    "solver_gate",
}
_GATE_STATUSES = {"PASS", "WARN", "FAIL", "PENDING", "EXCEPTION"}
_BENCHMARK_SOLVERS = {"exact", "qaoa", "classical"}


@dataclass(frozen=True)
class ArtifactProvenance:
    """Identity required on every downstream JSON artifact."""

    run_id: str
    profile_id: str
    profile_status: str
    config_version: str
    config_hash: str


def validate_provenance(provenance: ArtifactProvenance) -> None:
    """Reject missing or unsupported provenance before an artifact crosses a module boundary."""
    values = {
        "run_id": provenance.run_id,
        "profile_id": provenance.profile_id,
        "config_version": provenance.config_version,
        "config_hash": provenance.config_hash,
    }
    missing = [name for name, value in values.items() if not value.strip()]
    if missing:
        raise ValueError(f"Missing provenance fields: {', '.join(missing)}.")
    if provenance.profile_status not in _PROFILE_STATUSES:
        raise ValueError(
            f"Unsupported profile_status={provenance.profile_status!r}; "
            f"expected one of {sorted(_PROFILE_STATUSES)}."
        )


def validate_bitstring(bitstring: str, *, expected_bit_count: int) -> None:
    """Validate a binary string against a runtime-supplied dimension."""
    if expected_bit_count <= 0:
        raise ValueError("expected_bit_count must be positive.")
    if len(bitstring) != expected_bit_count:
        raise ValueError(
            f"bitstring has {len(bitstring)} bits, expected {expected_bit_count}: {bitstring!r}."
        )
    invalid = sorted(set(bitstring) - {"0", "1"})
    if invalid:
        raise ValueError(
            f"bitstring contains non-binary characters {invalid}: {bitstring!r}."
        )


CandidateTop10Schema = pandera.DataFrameSchema(
    {
        "run_id": pandera.Column(str),
        "profile_id": pandera.Column(str),
        "profile_status": pandera.Column(
            str, pandera.Check.isin(sorted(_PROFILE_STATUSES))
        ),
        "config_version": pandera.Column(str),
        "config_hash": pandera.Column(str),
        "rank": pandera.Column(int, pandera.Check.ge(1)),
        "ticker": pandera.Column(str),
        "current_weight": pandera.Column(float, pandera.Check.in_range(0.0, 1.0)),
        "eligible_status": pandera.Column(bool),
        "baseline_CVaR_contribution": pandera.Column(float),
        "marginal_CVaR_reduction_10pct": pandera.Column(float),
        "marginal_CVaR_reduction_20pct": pandera.Column(float),
        "marginal_CVaR_reduction_30pct": pandera.Column(float),
        "transaction_cost_estimate": pandera.Column(float, pandera.Check.ge(0.0)),
        "liquidity_penalty": pandera.Column(float, pandera.Check.ge(0.0)),
        "net_risk_score": pandera.Column(float),
        "selected_top10": pandera.Column(bool),
        "reason": pandera.Column(str),
    },
    unique=["run_id", "ticker"],
    coerce=True,
)


def validate_candidate_top10(
    data: pd.DataFrame, *, expected_candidates: int
) -> pd.DataFrame:
    """Validate selected candidate rows and deterministic contiguous ranking.

    The historical filename remains ``candidate_top10.csv``. During an explicitly provisional
    underfilled run, ``expected_candidates`` may be 8 and every selected row is still preserved.
    """
    validated = CandidateTop10Schema.validate(data, lazy=True)
    selected = validated.loc[validated["selected_top10"]]
    if len(selected) != expected_candidates:
        raise ValueError(
            f"candidate_top10 has {len(selected)} selected rows, expected {expected_candidates}."
        )
    expected_ranks = list(range(1, expected_candidates + 1))
    actual_ranks = sorted(selected["rank"].astype(int).tolist())
    if actual_ranks != expected_ranks:
        raise ValueError(
            f"Selected candidate ranks must be contiguous {expected_ranks}, got {actual_ranks}."
        )
    if not selected["eligible_status"].all():
        raise ValueError("Every selected candidate must have eligible_status=true.")
    return validated


@dataclass(frozen=True)
class CandidateOrderItem:
    rank: int
    ticker: str
    current_weight: float
    marginal_cvar_reduction: float
    transaction_cost_proxy: float
    liquidity_penalty: float
    candidate_score: float


@dataclass(frozen=True)
class CandidateOrder:
    provenance: ArtifactProvenance
    candidates: list[CandidateOrderItem]
    risk_coverage: float
    candidate_count: int
    bits_per_candidate: int
    total_decision_bits: int


def validate_candidate_order(order: CandidateOrder) -> None:
    """Validate canonical bit-decoding order without assuming 8 or 10 candidates."""
    validate_provenance(order.provenance)
    if len(order.candidates) != order.candidate_count:
        raise ValueError(
            f"candidate_order contains {len(order.candidates)} candidates, "
            f"expected {order.candidate_count}."
        )
    if order.total_decision_bits != order.candidate_count * order.bits_per_candidate:
        raise ValueError("candidate_order bit dimensions are inconsistent.")
    ranks = [candidate.rank for candidate in order.candidates]
    if ranks != list(range(1, order.candidate_count + 1)):
        raise ValueError(
            "candidate_order candidates must be stored in ascending contiguous rank."
        )
    tickers = [candidate.ticker for candidate in order.candidates]
    if len(set(tickers)) != len(tickers) or any(
        not ticker.strip() for ticker in tickers
    ):
        raise ValueError("candidate_order tickers must be non-empty and unique.")
    if not 0.0 <= order.risk_coverage <= 1.0:
        raise ValueError("candidate_order.risk_coverage must be in [0, 1].")


@dataclass(frozen=True)
class RiskSummary:
    """Risk-owned handoff; metrics retain explicit units and loss-sign convention."""

    provenance: ArtifactProvenance
    evaluation_date: date
    candidate_order_hash: str
    cvar_alpha_primary: float
    scenario_count: int
    loss_sign_convention: str
    metrics: dict[str, float]
    metric_units: dict[str, str]
    target_cash_increment: float
    warnings: list[str] = field(default_factory=list)


def validate_risk_summary(summary: RiskSummary) -> None:
    validate_provenance(summary.provenance)
    if not summary.candidate_order_hash:
        raise ValueError("risk_summary.candidate_order_hash is required.")
    if not 0.0 < summary.cvar_alpha_primary < 1.0:
        raise ValueError("risk_summary.cvar_alpha_primary must be in (0, 1).")
    if summary.scenario_count <= 0:
        raise ValueError("risk_summary.scenario_count must be positive.")
    if summary.loss_sign_convention != "positive_is_loss":
        raise ValueError(
            "risk_summary must declare loss_sign_convention='positive_is_loss'."
        )
    if set(summary.metrics) != set(summary.metric_units):
        raise ValueError(
            "risk_summary metrics and metric_units must have identical keys."
        )
    if not 0.0 <= summary.target_cash_increment <= 1.0:
        raise ValueError("risk_summary.target_cash_increment must be in [0, 1].")


ObjectiveSamplesSchema = pandera.DataFrameSchema(
    {
        "run_id": pandera.Column(str),
        "profile_id": pandera.Column(str),
        "profile_status": pandera.Column(
            str, pandera.Check.isin(sorted(_PROFILE_STATUSES))
        ),
        "config_version": pandera.Column(str),
        "config_hash": pandera.Column(str),
        "candidate_order_hash": pandera.Column(str),
        "bitstring": pandera.Column(str),
        "sample_kind": pandera.Column(str, pandera.Check.isin(sorted(_SAMPLE_KINDS))),
        "actions_json": pandera.Column(str),
        "components_json": pandera.Column(str),
        "scalar_objective": pandera.Column(float),
        "violations_json": pandera.Column(str),
        "feasible": pandera.Column(bool),
        "seed": pandera.Column(pd.Int64Dtype(), nullable=True),
        "policy_version": pandera.Column(str),
    },
    unique=["run_id", "bitstring"],
    coerce=True,
)


def structured_sample_count(bit_count: int) -> int:
    """Return intercept + all main effects + all pairwise effects."""
    if bit_count <= 0:
        raise ValueError("bit_count must be positive.")
    return 1 + bit_count + bit_count * (bit_count - 1) // 2


def validate_objective_samples(
    data: pd.DataFrame,
    *,
    expected_bit_count: int,
    require_complete_structured_set: bool = True,
) -> pd.DataFrame:
    """Validate objective rows and, by default, the complete quadratic design."""
    validated = ObjectiveSamplesSchema.validate(data, lazy=True)
    for bitstring in validated["bitstring"]:
        validate_bitstring(str(bitstring), expected_bit_count=expected_bit_count)
    if require_complete_structured_set:
        expected = {
            "intercept": 1,
            "main_effect": expected_bit_count,
            "pairwise_effect": expected_bit_count * (expected_bit_count - 1) // 2,
        }
        actual = validated["sample_kind"].value_counts().to_dict()
        for kind, count in expected.items():
            if actual.get(kind, 0) < count:
                raise ValueError(
                    f"objective samples contain {actual.get(kind, 0)} {kind} rows, "
                    f"require at least {count}."
                )
    return validated


@dataclass(frozen=True)
class QuboModel:
    provenance: ArtifactProvenance
    qubo_hash: str
    candidate_order_hash: str
    bit_count: int
    constant: float
    linear: list[float]
    quadratic: list[list[float]]
    scales: dict[str, float]
    penalties: dict[str, float]
    validation_metrics: dict[str, float]
    validation_passed: bool


def validate_qubo_model(model: QuboModel) -> None:
    validate_provenance(model.provenance)
    if not model.qubo_hash or not model.candidate_order_hash:
        raise ValueError("qubo_model hashes are required.")
    if model.bit_count <= 0 or len(model.linear) != model.bit_count:
        raise ValueError("qubo_model linear coefficients do not match bit_count.")
    if len(model.quadratic) != model.bit_count or any(
        len(row) != model.bit_count for row in model.quadratic
    ):
        raise ValueError(
            "qubo_model quadratic coefficients must be bit_count x bit_count."
        )
    if any(value < 0.0 for value in model.penalties.values()):
        raise ValueError("qubo_model penalties must be non-negative.")


@dataclass(frozen=True)
class SolverCandidate:
    bitstring: str
    qubo_energy: float
    feasible: bool
    probability_or_count: float | None


@dataclass(frozen=True)
class SolverWorkflowResult:
    provenance: ArtifactProvenance
    qubo_hash: str
    solver: SolverKind
    solver_config: dict[str, Any]
    candidates: list[SolverCandidate]
    bit_count: int
    runtime_seconds: float
    status: str


def validate_solver_workflow_result(result: SolverWorkflowResult) -> None:
    validate_provenance(result.provenance)
    if not result.qubo_hash:
        raise ValueError("solver result qubo_hash is required.")
    if result.status not in _SOLVER_STATUSES:
        raise ValueError(f"Unsupported solver status {result.status!r}.")
    if result.runtime_seconds < 0.0:
        raise ValueError("solver runtime_seconds must be non-negative.")
    if result.status == "completed" and not result.candidates:
        raise ValueError("Completed solver result must contain at least one candidate.")
    seen: set[str] = set()
    for candidate in result.candidates:
        validate_bitstring(candidate.bitstring, expected_bit_count=result.bit_count)
        if candidate.bitstring in seen:
            raise ValueError(
                f"Duplicate solver candidate bitstring {candidate.bitstring!r}."
            )
        seen.add(candidate.bitstring)
        if (
            candidate.probability_or_count is not None
            and candidate.probability_or_count < 0.0
        ):
            raise ValueError("probability_or_count must be non-negative when present.")


RerankedCandidatesSchema = pandera.DataFrameSchema(
    {
        "run_id": pandera.Column(str),
        "profile_id": pandera.Column(str),
        "profile_status": pandera.Column(
            str, pandera.Check.isin(sorted(_PROFILE_STATUSES))
        ),
        "config_version": pandera.Column(str),
        "config_hash": pandera.Column(str),
        "qubo_hash": pandera.Column(str),
        "rank": pandera.Column(int, pandera.Check.ge(1)),
        "bitstring": pandera.Column(str),
        "source_solver": pandera.Column(str),
        "qubo_energy": pandera.Column(float),
        "true_cvar": pandera.Column(float),
        "transaction_cost": pandera.Column(float, pandera.Check.ge(0.0)),
        "turnover": pandera.Column(float, pandera.Check.ge(0.0)),
        "feasible": pandera.Column(bool),
        "violations_json": pandera.Column(str),
    },
    unique=["run_id", "bitstring"],
    coerce=True,
)


def validate_reranked_candidates(
    data: pd.DataFrame, *, expected_bit_count: int
) -> pd.DataFrame:
    """Validate true-CVaR reranking output and deterministic rank order."""
    validated = RerankedCandidatesSchema.validate(data, lazy=True)
    for bitstring in validated["bitstring"]:
        validate_bitstring(str(bitstring), expected_bit_count=expected_bit_count)
    ranks = sorted(validated["rank"].astype(int).tolist())
    if ranks != list(range(1, len(validated) + 1)):
        raise ValueError("reranked candidate ranks must be contiguous from 1.")
    return validated


@dataclass(frozen=True)
class RecommendationAction:
    ticker: str
    bits: str
    quantum_reduction: float
    polished_reduction: float
    current_weight: float
    sell_value: float
    final_weight: float


@dataclass(frozen=True)
class FinalRecommendation:
    provenance: ArtifactProvenance
    requested_solver: SolverKind
    actual_solver: SolverKind
    evaluation_date: date
    candidate_order_hash: str
    qubo_hash: str
    actions: list[RecommendationAction]
    candidate_count: int
    bits_per_candidate: int
    cash_before: float
    cash_after: float
    unchanged_weight_total: float
    cvar_before: dict[str, float]
    cvar_after: dict[str, float]
    expected_return_before: float
    expected_return_after: float
    transaction_cost: float
    turnover: float
    constraints_passed: bool
    warnings: list[str] = field(default_factory=list)
    # TL-018 — materiality of true-CVaR improvement after cost
    materiality_threshold: float = 0.01
    true_cvar_relative_reduction: float | None = None
    materiality_met: bool | None = None
    improvement_claim_allowed: bool | None = None


def validate_final_recommendation(recommendation: FinalRecommendation) -> None:
    """Validate provenance, action encoding, and portfolio accounting boundaries."""
    validate_provenance(recommendation.provenance)
    if not recommendation.candidate_order_hash or not recommendation.qubo_hash:
        raise ValueError("final recommendation hashes are required.")
    if len(recommendation.actions) != recommendation.candidate_count:
        raise ValueError(
            "final recommendation action count does not match candidate_count."
        )
    tickers = [action.ticker for action in recommendation.actions]
    if len(set(tickers)) != len(tickers) or any(
        not ticker.strip() for ticker in tickers
    ):
        raise ValueError("final recommendation tickers must be non-empty and unique.")
    reduction_by_bits = {"00": 0.0, "10": 0.1, "01": 0.2, "11": 0.3}
    for action in recommendation.actions:
        validate_bitstring(
            action.bits, expected_bit_count=recommendation.bits_per_candidate
        )
        expected_reduction = reduction_by_bits.get(action.bits)
        if expected_reduction is None or action.quantum_reduction != expected_reduction:
            raise ValueError(
                "quantum_reduction does not match four-level bit mapping "
                "00/10/01/11 -> 0/10/20/30%."
            )
        if not 0.0 <= action.polished_reduction <= 0.3:
            raise ValueError("polished_reduction must be in [0, 0.3].")
        if abs(action.polished_reduction - action.quantum_reduction) > 0.05 + 1e-12:
            raise ValueError(
                "Local polishing may adjust an action by at most 5 percentage points."
            )
        if action.bits == "0" * recommendation.bits_per_candidate and (
            action.polished_reduction != 0.0
        ):
            raise ValueError("Zero-action lock requires polished_reduction=0.")
        if min(action.current_weight, action.sell_value, action.final_weight) < 0.0:
            raise ValueError(
                "Recommendation weights and sell values must be non-negative."
            )
    if not 0.0 <= recommendation.cash_before <= 1.0:
        raise ValueError("cash_before must be in [0, 1].")
    if not 0.0 <= recommendation.cash_after <= 1.0:
        raise ValueError("cash_after must be in [0, 1].")
    if not 0.0 <= recommendation.unchanged_weight_total <= 1.0:
        raise ValueError("unchanged_weight_total must be in [0, 1].")
    current_weight_sum = (
        recommendation.cash_before
        + recommendation.unchanged_weight_total
        + sum(action.current_weight for action in recommendation.actions)
    )
    if abs(current_weight_sum - 1.0) > 1e-8:
        raise ValueError(
            f"Current weights plus cash sum to {current_weight_sum}, expected 1.0."
        )
    final_weight_sum = (
        recommendation.cash_after
        + recommendation.unchanged_weight_total
        + sum(action.final_weight for action in recommendation.actions)
    )
    if abs(final_weight_sum - 1.0) > 1e-8:
        raise ValueError(
            f"Final weights plus cash sum to {final_weight_sum}, expected 1.0."
        )
    if recommendation.transaction_cost < 0.0 or recommendation.turnover < 0.0:
        raise ValueError("transaction_cost and turnover must be non-negative.")
    if recommendation.materiality_threshold <= 0.0:
        raise ValueError("materiality_threshold must be positive.")
    if recommendation.true_cvar_relative_reduction is not None:
        expected_met = (
            recommendation.true_cvar_relative_reduction
            >= recommendation.materiality_threshold
        )
        if (
            recommendation.materiality_met is not None
            and recommendation.materiality_met != expected_met
        ):
            raise ValueError(
                "materiality_met does not match true_cvar_relative_reduction vs threshold."
            )
        if recommendation.improvement_claim_allowed is True and not expected_met:
            raise ValueError(
                "improvement_claim_allowed requires materiality_met "
                f"(relative reduction >= {recommendation.materiality_threshold})."
            )


@dataclass(frozen=True)
class GateVerdict:
    """Sign-off / quality verdict for a named approval or validation gate."""

    gate_id: str
    status: str
    owner: str
    metrics: dict[str, float] = field(default_factory=dict)
    signed_at: str | None = None
    exception_disclosure: str | None = None
    notes: list[str] = field(default_factory=list)


def validate_gate_verdict(verdict: GateVerdict) -> None:
    if verdict.gate_id not in _GATE_IDS:
        raise ValueError(
            f"Unsupported gate_id={verdict.gate_id!r}; expected one of {sorted(_GATE_IDS)}."
        )
    if verdict.status not in _GATE_STATUSES:
        raise ValueError(
            f"Unsupported gate status={verdict.status!r}; "
            f"expected one of {sorted(_GATE_STATUSES)}."
        )
    if not verdict.owner.strip():
        raise ValueError("gate verdict owner is required.")
    if verdict.status == "EXCEPTION" and not (
        verdict.exception_disclosure and verdict.exception_disclosure.strip()
    ):
        raise ValueError("EXCEPTION gate status requires exception_disclosure.")


@dataclass(frozen=True)
class SolverManifest:
    """Registered solver settings that must travel with GATE-08 BenchmarkReport."""

    shots: int
    registered_seeds: list[int]
    reps: int
    optimizer: str
    maxiter: int
    backend: str
    package_versions: dict[str, str]
    warm_start: bool
    seed_status: dict[str, str] = field(default_factory=dict)
    NON_FINAL_CONFIG: bool = False


@dataclass(frozen=True)
class BenchmarkReport:
    """Contract for exact + QAOA + classical comparison on one QUBO (TL-015, G1/G3/G11)."""

    provenance: ArtifactProvenance
    qubo_hash: str
    candidate_order_hash: str
    solver_manifest: SolverManifest
    requested_solver: str
    actual_solver: str
    exact_best_energy: float
    qaoa_best_energy: float | None
    classical_best_energy: float | None
    success_prob: float | None = None
    feasible_rate: float | None = None
    optimality_gap: float | None = None
    energy_stats: dict[str, float] = field(default_factory=dict)
    runtime_seconds: dict[str, float] = field(default_factory=dict)
    peak_memory_mb: float | None = None
    reference_hardware: dict[str, Any] = field(default_factory=dict)
    fallback_reason: str | None = None
    caveats: list[str] = field(default_factory=list)


def validate_benchmark_report(report: BenchmarkReport) -> None:
    """Reject benchmark payloads that mix hashes, profiles, or incomplete solver provenance."""
    validate_provenance(report.provenance)
    if not report.qubo_hash or not report.candidate_order_hash:
        raise ValueError("benchmark report hashes are required.")
    if report.requested_solver not in _BENCHMARK_SOLVERS:
        raise ValueError(f"Unsupported requested_solver={report.requested_solver!r}.")
    if report.actual_solver not in _BENCHMARK_SOLVERS:
        raise ValueError(f"Unsupported actual_solver={report.actual_solver!r}.")
    manifest = report.solver_manifest
    if manifest.shots <= 0 or manifest.reps <= 0 or manifest.maxiter <= 0:
        raise ValueError("solver_manifest shots/reps/maxiter must be positive.")
    if len(manifest.registered_seeds) < 1:
        raise ValueError("solver_manifest.registered_seeds must be non-empty.")
    if not manifest.optimizer.strip() or not manifest.backend.strip():
        raise ValueError("solver_manifest optimizer and backend are required.")
    if report.requested_solver != report.actual_solver and not (
        report.fallback_reason and report.fallback_reason.strip()
    ):
        raise ValueError(
            "actual_solver differs from requested_solver — fallback_reason is required."
        )
    if report.success_prob is not None and not 0.0 <= report.success_prob <= 1.0:
        raise ValueError("success_prob must be in [0, 1].")
    if report.feasible_rate is not None and not 0.0 <= report.feasible_rate <= 1.0:
        raise ValueError("feasible_rate must be in [0, 1].")
    for key, value in report.runtime_seconds.items():
        if value < 0.0:
            raise ValueError(f"runtime_seconds[{key!r}] must be non-negative.")
    if report.peak_memory_mb is not None and report.peak_memory_mb < 0.0:
        raise ValueError("peak_memory_mb must be non-negative.")


def validate_transaction_cost_excludes_liquidity(config: dict[str, Any]) -> None:
    """TL-008 shape check: liquidity is a separate objective component, not a txn fee add-on.

    Accepts either flat Decision-package keys (provisional override) or nested ``risk.*``.
    """
    txn = config.get("transaction_cost")
    if not isinstance(txn, dict):
        txn = (config.get("risk") or {}).get("transaction_cost")
    if not isinstance(txn, dict):
        raise TypeError("transaction_cost block is required for TL-008 validation.")
    for key in ("fee", "spread"):
        if txn.get(key) is None:
            raise ValueError(f"transaction_cost.{key} must be set (TL-007).")
    objective = config.get("financial_objective")
    if not isinstance(objective, dict):
        objective = (config.get("risk") or {}).get("financial_objective")
    if not isinstance(objective, dict):
        raise TypeError("financial_objective block is required for TL-008 validation.")
    components = objective.get("components") or {}
    if "transaction_cost" not in components or "liquidity_penalty" not in components:
        raise ValueError(
            "financial_objective.components must list transaction_cost and "
            "liquidity_penalty separately (TL-008)."
        )
    if components["transaction_cost"] is components.get("liquidity_penalty"):
        raise ValueError("transaction_cost and liquidity_penalty must be distinct.")
