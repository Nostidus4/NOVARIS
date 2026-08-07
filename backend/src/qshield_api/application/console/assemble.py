"""Assemble console page DTOs from workflow + related artifact views."""

from __future__ import annotations

from typing import Any

from qshield_api.application.console.dto import (
    ActionMiniDTO,
    CandidateRowDTO,
    ConsoleDataDTO,
    ConsoleOverviewDTO,
    ConsoleQuantumDTO,
    ConsoleRegimeDTO,
    ConsoleReportDTO,
    ConsoleRiskDTO,
    ConsoleScenariosDTO,
    ConsoleShellDTO,
    DataQualityRowDTO,
    PipelineStageDTO,
    RegimePointDTO,
    ScenarioValidationRowDTO,
    UniverseRowDTO,
)
from qshield_api.domain.benchmark.entities import BenchmarkView
from qshield_api.domain.regime.entities import RegimeCurrent, RegimeTimeline
from qshield_api.domain.runs.entities import RunDetail
from qshield_api.domain.scenarios.entities import ScenarioSummary
from qshield_api.domain.workflow.entities import WorkflowArtifactView

PIPELINE_SPEC: list[tuple[str, str, str, str]] = [
    ("data", "01", "Data Gate", "Coverage, nulls, stale feed checks"),
    ("regime", "02", "Regime", "Market-state inference completed"),
    ("scenarios", "03", "Scenarios", "Stress paths generated"),
    ("risk_prepare", "04", "Risk", "Top-10 ranking & handoff"),
    ("qubo_model", "05", "Quantum", "QUBO / exact / QAOA artifacts"),
    ("rerank_polish", "06", "Decision", "True-risk rerank & polish"),
]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


def _scenario_count(view: WorkflowArtifactView) -> int | None:
    risk = view.risk_summary or {}
    if risk.get("scenario_count") is not None:
        return int(risk["scenario_count"])
    manifest = view.scenario_manifest or {}
    primary = (
        manifest.get("primary") if isinstance(manifest.get("primary"), dict) else {}
    )
    for source in (manifest.get("num_scenarios"), primary.get("num_scenarios")):
        if source is not None:
            return int(source)
    return None


def _rec(view: WorkflowArtifactView) -> dict[str, Any]:
    return dict(view.final_recommendation or {})


def _actions(view: WorkflowArtifactView) -> list[ActionMiniDTO]:
    rec = _rec(view)
    rows = rec.get("actions") or []
    out: list[ActionMiniDTO] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            ActionMiniDTO(
                ticker=str(row.get("ticker", "")),
                polished_reduction=_float_or_none(row.get("polished_reduction")),
                bits=str(row["bits"]) if row.get("bits") is not None else None,
                current_weight=_float_or_none(row.get("current_weight")),
                final_weight=_float_or_none(row.get("final_weight")),
                quantum_reduction=_float_or_none(row.get("quantum_reduction")),
                sell_value=_float_or_none(row.get("sell_value")),
            )
        )
    return out


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _top_actions(view: WorkflowArtifactView, limit: int = 3) -> list[ActionMiniDTO]:
    ranked = [
        a
        for a in _actions(view)
        if a.polished_reduction is not None and a.polished_reduction > 0
    ]
    ranked.sort(key=lambda a: a.polished_reduction or 0.0, reverse=True)
    return ranked[:limit]


def _candidates(view: WorkflowArtifactView) -> list[CandidateRowDTO]:
    rows: list[CandidateRowDTO] = []
    for raw in view.candidates or []:
        if not isinstance(raw, dict):
            continue
        rows.append(
            CandidateRowDTO(
                rank=int(raw["rank"]) if raw.get("rank") is not None else None,
                ticker=str(raw["ticker"]) if raw.get("ticker") is not None else None,
                selected_top10=_as_bool(raw.get("selected_top10")),
                eligible_status=_as_bool(raw.get("eligible_status")),
                net_risk_score=_float_or_none(raw.get("net_risk_score")),
                baseline_cvar_contribution=_float_or_none(
                    raw.get("baseline_CVaR_contribution")
                ),
                transaction_cost_estimate=_float_or_none(
                    raw.get("transaction_cost_estimate")
                ),
                liquidity_penalty=_float_or_none(raw.get("liquidity_penalty")),
                reason=str(raw["reason"]) if raw.get("reason") is not None else None,
                current_weight=_float_or_none(raw.get("current_weight")),
            )
        )
    rows = [r for r in rows if r.selected_top10]
    rows.sort(key=lambda r: r.rank if r.rank is not None else 10**9)
    return rows


def assemble_shell(view: WorkflowArtifactView | None) -> ConsoleShellDTO:
    if view is None:
        return ConsoleShellDTO(
            online=False,
            profile_id="",
            profile_status="",
            config_version="",
        )
    return ConsoleShellDTO(
        online=True,
        profile_id=view.profile_id,
        profile_status=view.profile_status,
        config_version=view.config_version,
        scenario_count=_scenario_count(view),
        candidate_count=view.candidate_count,
    )


def assemble_overview(view: WorkflowArtifactView | None) -> ConsoleOverviewDTO:
    if view is None:
        return ConsoleOverviewDTO(
            online=False,
            profile_id="",
            profile_status="",
            config_version="",
            candidate_count=0,
        )
    rec = _rec(view)
    pipeline = [
        PipelineStageDTO(
            key=key,
            step=step,
            name=name,
            description=desc,
            status=str(view.stage_status.get(key, "MISSING")),
        )
        for key, step, name, desc in PIPELINE_SPEC
    ]
    return ConsoleOverviewDTO(
        online=True,
        profile_id=view.profile_id,
        profile_status=view.profile_status,
        config_version=view.config_version,
        candidate_count=view.candidate_count,
        scenario_count=_scenario_count(view),
        actual_solver=str(rec["actual_solver"])
        if rec.get("actual_solver") is not None
        else None,
        true_cvar_before=_float_or_none(rec.get("true_cvar_before")),
        true_cvar_after=_float_or_none(rec.get("true_cvar_after")),
        true_cvar_relative_reduction=_float_or_none(
            rec.get("true_cvar_relative_reduction")
        ),
        materiality_met=_as_bool(rec["materiality_met"])
        if rec.get("materiality_met") is not None
        else None,
        transaction_cost=_float_or_none(rec.get("transaction_cost")),
        turnover=_float_or_none(rec.get("turnover")),
        constraints_passed=_as_bool(rec["constraints_passed"])
        if rec.get("constraints_passed") is not None
        else None,
        warnings=[str(w) for w in (rec.get("warnings") or [])],
        top_actions=_top_actions(view),
        pipeline=pipeline,
        stage_status=dict(view.stage_status),
    )


def assemble_data(view: WorkflowArtifactView | None) -> ConsoleDataDTO:
    if view is None:
        return ConsoleDataDTO(
            online=False,
            stage_status="MISSING",
            config_version="",
            manifest_present=False,
            universe_count=0,
            evidence_count=0,
            checks_passed=0,
            checks_total=0,
        )
    quality: list[DataQualityRowDTO] = []
    for row in view.data_quality or []:
        if not isinstance(row, dict):
            continue
        quality.append(
            DataQualityRowDTO(
                check_id=str(row["check_id"])
                if row.get("check_id") is not None
                else None,
                check_name=str(row["check_name"])
                if row.get("check_name") is not None
                else None,
                status=str(row["status"]) if row.get("status") is not None else None,
                type=str(row["type"]) if row.get("type") is not None else None,
                count=int(row["count"]) if row.get("count") is not None else None,
                trace=str(row["trace"]) if row.get("trace") is not None else None,
            )
        )
    universe: list[UniverseRowDTO] = []
    for row in view.universe or []:
        if not isinstance(row, dict):
            continue
        known = {"ticker", "company_name", "exchange", "exchange_current"}
        universe.append(
            UniverseRowDTO(
                ticker=str(row["ticker"]) if row.get("ticker") is not None else None,
                company_name=str(row["company_name"])
                if row.get("company_name") is not None
                else None,
                exchange=str(row.get("exchange") or row.get("exchange_current") or "")
                or None,
                extra={k: v for k, v in row.items() if k not in known},
            )
        )
    passed = sum(1 for q in quality if (q.status or "").upper() == "PASS")
    return ConsoleDataDTO(
        online=True,
        stage_status=str(view.stage_status.get("data", "MISSING")),
        config_version=view.config_version,
        manifest_present=view.data_manifest is not None,
        universe_count=len(universe),
        evidence_count=len(view.adjusted_close_evidence or []),
        checks_passed=passed,
        checks_total=len(quality),
        data_quality=quality,
        universe=universe,
        adjusted_close_evidence=list(view.adjusted_close_evidence or []),
        data_manifest=view.data_manifest,
    )


def assemble_regime(
    view: WorkflowArtifactView | None,
    *,
    current: RegimeCurrent | None = None,
    timeline: RegimeTimeline | None = None,
    timeline_limit: int = 120,
) -> ConsoleRegimeDTO:
    summary = dict((view.regime_summary if view else None) or {})
    points: list[RegimePointDTO] = []
    if timeline is not None:
        for snap in timeline.snapshots[-timeline_limit:]:
            points.append(
                RegimePointDTO(
                    date=snap.date,
                    regime=snap.regime,
                    prob_normal=snap.prob_normal,
                    prob_volatile=snap.prob_volatile,
                    prob_stress=snap.prob_stress,
                )
            )
    latest = None
    if current is not None:
        latest = RegimePointDTO(
            date=current.latest.date,
            regime=current.latest.regime,
            prob_normal=current.latest.prob_normal,
            prob_volatile=current.latest.prob_volatile,
            prob_stress=current.latest.prob_stress,
        )
    elif points:
        latest = points[-1]
    label_map = {
        str(k): str(v) for k, v in dict(summary.get("label_map") or {}).items()
    }
    return ConsoleRegimeDTO(
        online=view is not None,
        stage_status=str((view.stage_status if view else {}).get("regime", "MISSING")),
        gate_status=(
            current.gate_status
            if current is not None
            else (str(summary["gate_status"]) if summary.get("gate_status") else None)
        ),
        run_mode=(
            current.run_mode
            if current is not None
            else (str(summary["run_mode"]) if summary.get("run_mode") else None)
        ),
        champion=dict(summary.get("champion") or {}),
        coverage=dict(summary.get("coverage") or {}),
        label_map=label_map,
        occupancy=dict(summary.get("occupancy") or {}),
        latest=latest,
        timeline=points,
    )


def assemble_scenarios(
    view: WorkflowArtifactView | None,
    *,
    scenario: ScenarioSummary | None = None,
) -> ConsoleScenariosDTO:
    manifest = dict((view.scenario_manifest if view else None) or {})
    primary = (
        dict(manifest.get("primary") or {})
        if isinstance(manifest.get("primary"), dict)
        else {}
    )
    if scenario is not None:
        validation = [
            ScenarioValidationRowDTO(
                target_regime=m.target_regime,
                metric=m.metric,
                scenario_value=m.scenario_value,
                reference_value=m.reference_value,
                statistic=m.statistic,
                verdict=m.verdict,
            )
            for m in scenario.validation
        ]
        return ConsoleScenariosDTO(
            online=True,
            stage_status=str(
                (view.stage_status if view else {}).get("scenarios", "MISSING")
            ),
            gate_status=scenario.gate_status,
            target_regime=scenario.target_regime,
            evaluation_date=scenario.evaluation_date,
            num_scenarios=scenario.num_scenarios,
            horizon_days=scenario.horizon_days,
            n_assets=int(primary["n_assets"])
            if primary.get("n_assets") is not None
            else len(scenario.ticker_order),
            block_length=(
                int(primary["block_length"])
                if primary.get("block_length") is not None
                else (
                    int(manifest["block_length"])
                    if manifest.get("block_length") is not None
                    else None
                )
            ),
            seed=manifest.get("seed") or primary.get("seed"),
            return_type=str(
                primary.get("return_type") or manifest.get("return_type") or ""
            )
            or None,
            anchor_first=str(primary["anchor_first"])
            if primary.get("anchor_first") is not None
            else None,
            anchor_last=str(primary["anchor_last"])
            if primary.get("anchor_last") is not None
            else None,
            reuse_rate=_float_or_none(primary.get("reuse_rate")),
            ticker_order=list(
                scenario.ticker_order
                or primary.get("ticker_order")
                or manifest.get("ticker_order")
                or []
            ),
            validation=validation,
            n_fail=sum(1 for m in validation if m.verdict != "PASS"),
            primary=primary,
        )

    count = _scenario_count(view) if view else None
    return ConsoleScenariosDTO(
        online=view is not None,
        stage_status=str(
            (view.stage_status if view else {}).get("scenarios", "MISSING")
        ),
        gate_status=str(manifest.get("gate_status") or "MISSING"),
        target_regime=str(manifest.get("target_regime") or "unknown"),
        evaluation_date=str(manifest.get("evaluation_date") or "unknown"),
        num_scenarios=int(count or 0),
        horizon_days=int(
            manifest.get("horizon_days") or primary.get("horizon_days") or 0
        ),
        n_assets=int(primary["n_assets"])
        if primary.get("n_assets") is not None
        else None,
        block_length=int(primary["block_length"])
        if primary.get("block_length") is not None
        else (
            int(manifest["block_length"])
            if manifest.get("block_length") is not None
            else None
        ),
        seed=manifest.get("seed") or primary.get("seed"),
        return_type=str(primary.get("return_type") or manifest.get("return_type") or "")
        or None,
        anchor_first=str(primary["anchor_first"])
        if primary.get("anchor_first") is not None
        else None,
        anchor_last=str(primary["anchor_last"])
        if primary.get("anchor_last") is not None
        else None,
        reuse_rate=_float_or_none(primary.get("reuse_rate")),
        ticker_order=list(
            primary.get("ticker_order") or manifest.get("ticker_order") or []
        ),
        validation=[],
        n_fail=0,
        primary=primary,
    )


def assemble_risk(view: WorkflowArtifactView | None) -> ConsoleRiskDTO:
    if view is None:
        return ConsoleRiskDTO(
            online=False,
            profile_id="",
            profile_status="",
            candidate_count=0,
        )
    rec = _rec(view)
    candidates = _candidates(view)
    return ConsoleRiskDTO(
        online=True,
        profile_id=view.profile_id,
        profile_status=view.profile_status,
        candidate_count=view.candidate_count,
        true_cvar_before=_float_or_none(rec.get("true_cvar_before")),
        true_cvar_after=_float_or_none(rec.get("true_cvar_after")),
        transaction_cost=_float_or_none(rec.get("transaction_cost")),
        turnover=_float_or_none(rec.get("turnover")),
        materiality_met=_as_bool(rec["materiality_met"])
        if rec.get("materiality_met") is not None
        else None,
        materiality_threshold=_float_or_none(rec.get("materiality_threshold")),
        top_candidate=candidates[0] if candidates else None,
        candidates=candidates,
        risk_summary=view.risk_summary,
    )


def assemble_quantum(
    view: WorkflowArtifactView | None,
    *,
    benchmark: BenchmarkView | None = None,
) -> ConsoleQuantumDTO:
    if view is None:
        return ConsoleQuantumDTO(online=False)
    rec = _rec(view)
    bench = view.workflow_benchmark or {}
    return ConsoleQuantumDTO(
        online=True,
        actual_solver=(
            (benchmark.actual_solver if benchmark and benchmark.actual_solver else None)
            or (
                str(rec["actual_solver"])
                if rec.get("actual_solver") is not None
                else None
            )
            or (
                str(bench["actual_solver"])
                if bench.get("actual_solver") is not None
                else None
            )
        ),
        requested_solver=(
            (
                benchmark.requested_solver
                if benchmark and benchmark.requested_solver
                else None
            )
            or (
                str(rec["requested_solver"])
                if rec.get("requested_solver") is not None
                else None
            )
        ),
        constraints_passed=_as_bool(rec["constraints_passed"])
        if rec.get("constraints_passed") is not None
        else None,
        winning_bitstring=(
            str(rec["winning_bitstring"])
            if rec.get("winning_bitstring") is not None
            else (benchmark.winning_bitstring if benchmark is not None else None)
        ),
        true_cvar_before=_float_or_none(rec.get("true_cvar_before")),
        true_cvar_after=_float_or_none(rec.get("true_cvar_after")),
        caveat=(
            benchmark.caveat
            if benchmark is not None and benchmark.caveat
            else (str(bench["caveat"]) if bench.get("caveat") is not None else None)
        ),
        exact_best_energy=(
            benchmark.exact_best_feasible_energy
            if benchmark is not None
            else _float_or_none(bench.get("exact_best_energy"))
        ),
        mean_feasibility_rate=(
            benchmark.mean_feasibility_rate
            if benchmark is not None
            else _float_or_none(bench.get("mean_feasibility_rate"))
        ),
        classical_energy=(
            benchmark.classical_energy
            if benchmark is not None
            else _float_or_none(bench.get("classical_energy"))
        ),
        optimality_gap=(
            benchmark.optimality_gap
            if benchmark is not None
            else _float_or_none(bench.get("optimality_gap"))
        ),
        qaoa_beats_classical=(
            benchmark.qaoa_beats_classical if benchmark is not None else None
        ),
        source_artifact=(benchmark.source_artifact if benchmark is not None else None),
        actions=sorted(_actions(view), key=lambda a: a.ticker),
        workflow_benchmark=view.workflow_benchmark,
        qubo_model=view.qubo_model,
        exact_solution=view.exact_solution,
    )


def assemble_report(
    view: WorkflowArtifactView | None,
    *,
    run: RunDetail | None = None,
) -> ConsoleReportDTO:
    if view is None:
        return ConsoleReportDTO(
            online=False,
            profile_id="",
            profile_status="",
            config_version="",
            universe_count=0,
        )
    rec = _rec(view)
    return ConsoleReportDTO(
        online=True,
        profile_id=view.profile_id,
        profile_status=view.profile_status,
        config_version=view.config_version,
        universe_count=len(view.universe or []),
        scenario_count=_scenario_count(view),
        actual_solver=str(rec["actual_solver"])
        if rec.get("actual_solver") is not None
        else None,
        true_cvar_before=_float_or_none(rec.get("true_cvar_before")),
        true_cvar_after=_float_or_none(rec.get("true_cvar_after")),
        transaction_cost=_float_or_none(rec.get("transaction_cost")),
        turnover=_float_or_none(rec.get("turnover")),
        materiality_met=_as_bool(rec["materiality_met"])
        if rec.get("materiality_met") is not None
        else None,
        warnings=[str(w) for w in (rec.get("warnings") or [])],
        stage_status=dict(view.stage_status),
        top_actions=_top_actions(view),
        run_id=run.run_id if run is not None else None,
        logs_tail=list(run.logs_tail) if run is not None else [],
        metrics=dict(run.metrics) if run is not None and run.metrics else None,
    )
