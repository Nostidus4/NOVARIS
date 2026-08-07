"""Page-shaped DTOs for the NOVARIS console — mapped from artifacts, no finance recompute."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConsoleShellDTO(BaseModel):
    online: bool
    profile_id: str
    profile_status: str
    config_version: str
    scenario_count: int | None = None
    candidate_count: int = 0


class PipelineStageDTO(BaseModel):
    key: str
    step: str
    name: str
    description: str
    status: str


class ActionMiniDTO(BaseModel):
    ticker: str
    polished_reduction: float | None = None
    bits: str | None = None
    current_weight: float | None = None
    final_weight: float | None = None
    quantum_reduction: float | None = None
    sell_value: float | None = None


class ConsoleOverviewDTO(BaseModel):
    online: bool
    profile_id: str
    profile_status: str
    config_version: str
    candidate_count: int
    scenario_count: int | None = None
    actual_solver: str | None = None
    true_cvar_before: float | None = None
    true_cvar_after: float | None = None
    true_cvar_relative_reduction: float | None = None
    materiality_met: bool | None = None
    transaction_cost: float | None = None
    turnover: float | None = None
    constraints_passed: bool | None = None
    warnings: list[str] = Field(default_factory=list)
    top_actions: list[ActionMiniDTO] = Field(default_factory=list)
    pipeline: list[PipelineStageDTO] = Field(default_factory=list)
    stage_status: dict[str, str] = Field(default_factory=dict)


class DataQualityRowDTO(BaseModel):
    check_id: str | None = None
    check_name: str | None = None
    status: str | None = None
    type: str | None = None
    count: int | None = None
    trace: str | None = None


class UniverseRowDTO(BaseModel):
    ticker: str | None = None
    company_name: str | None = None
    exchange: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ConsoleDataDTO(BaseModel):
    online: bool
    stage_status: str
    config_version: str
    manifest_present: bool
    universe_count: int
    evidence_count: int
    checks_passed: int
    checks_total: int
    data_quality: list[DataQualityRowDTO] = Field(default_factory=list)
    universe: list[UniverseRowDTO] = Field(default_factory=list)
    adjusted_close_evidence: list[dict[str, Any]] = Field(default_factory=list)
    data_manifest: dict[str, Any] | None = None


class RegimePointDTO(BaseModel):
    date: str
    regime: str
    prob_normal: float
    prob_volatile: float
    prob_stress: float


class ConsoleRegimeDTO(BaseModel):
    online: bool
    stage_status: str
    gate_status: str | None = None
    run_mode: str | None = None
    champion: dict[str, Any] = Field(default_factory=dict)
    coverage: dict[str, Any] = Field(default_factory=dict)
    label_map: dict[str, str] = Field(default_factory=dict)
    occupancy: dict[str, Any] = Field(default_factory=dict)
    latest: RegimePointDTO | None = None
    timeline: list[RegimePointDTO] = Field(default_factory=list)


class ScenarioValidationRowDTO(BaseModel):
    target_regime: str
    metric: str
    scenario_value: float
    reference_value: float
    statistic: float
    verdict: str


class ConsoleScenariosDTO(BaseModel):
    online: bool
    stage_status: str
    gate_status: str
    target_regime: str
    evaluation_date: str
    num_scenarios: int
    horizon_days: int
    n_assets: int | None = None
    block_length: int | None = None
    seed: int | str | None = None
    return_type: str | None = None
    anchor_first: str | None = None
    anchor_last: str | None = None
    reuse_rate: float | None = None
    ticker_order: list[str] = Field(default_factory=list)
    validation: list[ScenarioValidationRowDTO] = Field(default_factory=list)
    n_fail: int = 0
    primary: dict[str, Any] = Field(default_factory=dict)


class CandidateRowDTO(BaseModel):
    rank: int | None = None
    ticker: str | None = None
    selected_top10: bool = False
    eligible_status: bool = False
    net_risk_score: float | None = None
    baseline_cvar_contribution: float | None = None
    transaction_cost_estimate: float | None = None
    liquidity_penalty: float | None = None
    reason: str | None = None
    current_weight: float | None = None


class ConsoleRiskDTO(BaseModel):
    online: bool
    profile_id: str
    profile_status: str
    candidate_count: int
    true_cvar_before: float | None = None
    true_cvar_after: float | None = None
    transaction_cost: float | None = None
    turnover: float | None = None
    materiality_met: bool | None = None
    materiality_threshold: float | None = None
    top_candidate: CandidateRowDTO | None = None
    candidates: list[CandidateRowDTO] = Field(default_factory=list)
    risk_summary: dict[str, Any] | None = None


class ConsoleQuantumDTO(BaseModel):
    online: bool
    actual_solver: str | None = None
    requested_solver: str | None = None
    constraints_passed: bool | None = None
    winning_bitstring: str | None = None
    true_cvar_before: float | None = None
    true_cvar_after: float | None = None
    caveat: str | None = None
    exact_best_energy: float | None = None
    mean_feasibility_rate: float | None = None
    classical_energy: float | None = None
    optimality_gap: float | None = None
    qaoa_beats_classical: bool | None = None
    source_artifact: str | None = None
    actions: list[ActionMiniDTO] = Field(default_factory=list)
    workflow_benchmark: dict[str, Any] | None = None
    qubo_model: dict[str, Any] | None = None
    exact_solution: dict[str, Any] | None = None


class ConsoleReportDTO(BaseModel):
    online: bool
    profile_id: str
    profile_status: str
    config_version: str
    universe_count: int
    scenario_count: int | None = None
    actual_solver: str | None = None
    true_cvar_before: float | None = None
    true_cvar_after: float | None = None
    transaction_cost: float | None = None
    turnover: float | None = None
    materiality_met: bool | None = None
    warnings: list[str] = Field(default_factory=list)
    stage_status: dict[str, str] = Field(default_factory=dict)
    top_actions: list[ActionMiniDTO] = Field(default_factory=list)
    run_id: str | None = None
    logs_tail: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] | None = None
