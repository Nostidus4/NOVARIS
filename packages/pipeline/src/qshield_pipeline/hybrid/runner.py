# Đỗ Ngọc Tân - chạy một portfolio-date instance: references, pools theo nguồn, polish, attribution.
"""Runner của thí nghiệm hybrid.

``run_instance`` là hàm thuần trên ``InstanceInputs`` (không đọc/ghi đĩa) để test được end-to-end;
``run_experiment`` lo I/O qua ``ArtifactPaths`` và ghi attempts (kể cả crash/skip).

Bất biến:
- exact (QUBO optimum, ``J*_grid``, ``J*_polished``) chỉ nằm trong track ``exact_reference``;
- mỗi track candidate-budget được chấm đúng B trạng thái unique, cùng polish top-k + evaluation cap;
- view compute-budget quy đổi wall time QAOA ra "số lần tính true objective tương đương" (đo trên
  chính instance) — tái lập được, không phụ thuộc tải máy lúc chạy classical;
- QAOA thất bại ⇒ track ghi FAILED; các track khác vẫn chạy.
"""

from __future__ import annotations

import json
import math
import time
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from qshield_contracts.enums import Stage
from qshield_contracts.hashing import effective_action_hash, stable_hash
from qshield_contracts.paths import ArtifactPaths
from qshield_contracts.schemas.hybrid import (
    REFERENCE_TRACK,
    validate_candidate_pool,
    validate_polish_trace,
    validate_qaoa_distribution,
    validate_track_results,
)
from qshield_quantum.formulation.four_level import four_level_variable_names
from qshield_quantum.formulation.normalization import normalize_for_qaoa
from qshield_quantum.formulation.qiskit_program import build_quadratic_program
from qshield_quantum.formulation.surrogate import (
    fit_quadratic_surrogate,
    structured_samples_to_arrays,
)
from qshield_quantum.generators.boltzmann_pool import boltzmann_pool
from qshield_quantum.generators.common import StateSpace, enumerate_state_space
from qshield_quantum.generators.qaoa_pool import (
    distribution_metrics,
    distribution_rows,
    qaoa_proposals,
    run_qaoa_seeds,
)
from qshield_quantum.generators.random_pool import stratified_pool, uniform_pool
from qshield_quantum.generators.surrogate_search import surrogate_local_search_pool
from qshield_quantum.solvers.qaoa import solve_qaoa_one_seed_fast
from qshield_quantum.verify.consistency import verify_quadratic_consistency
from qshield_quantum.verify.hybrid_attribution import attribution_checklist
from qshield_risk.candidates import candidate_order, select_four_level_candidates
from qshield_risk.hybrid import (
    ObjectiveContext,
    TrueGrid,
    TrueObjectiveScorer,
    bitstring_from_levels,
    build_objective_context,
    exact_true_grid,
    levels_from_bitstring,
    polish_top_candidates,
    rank_scored,
    true_coordinate_search_pool,
)
from qshield_risk.policy import RiskPolicy, policy_to_quantum_constraints
from qshield_risk.sampling import sample_objective_dataset
from scipy.stats import spearmanr

from qshield_pipeline.hybrid.instances import (
    HybridData,
    InstanceInputs,
    InstanceSkipped,
    build_instance_inputs,
)
from qshield_pipeline.hybrid.settings import HybridSettings


class HybridAttributionError(RuntimeError):
    """Checklist attribution FAIL — kết quả instance không được dùng."""


@dataclass
class InstanceOutputs:
    instance_id: str
    distribution: pd.DataFrame
    pools: pd.DataFrame
    polish: pd.DataFrame
    tracks: pd.DataFrame
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class _TrackRun:
    track: str
    view: str
    scored: list[dict[str, Any]]
    traces: list[dict[str, Any]]
    budget: int
    generation_seconds: float
    polish_seconds: float
    evaluations_generation: int
    status: str = "OK"
    reason: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


def _measure_eval_seconds(context: ObjectiveContext, samples: int, seed: int) -> float:
    rng = np.random.default_rng(seed)
    started = time.perf_counter()
    for _ in range(max(1, samples)):
        bits = "".join(rng.choice(["0", "1"], size=context.bit_count))
        context.evaluate(context.reductions_from_bitstring(bits))
    return (time.perf_counter() - started) / max(1, samples)


def _proposal_dicts(proposals: Sequence[Any]) -> list[dict[str, Any]]:
    return [asdict(item) for item in proposals]


def _run_track(
    track: str,
    view: str,
    context: ObjectiveContext,
    grid: TrueGrid | None,
    settings: HybridSettings,
    budget: int,
    generate: Callable[[TrueObjectiveScorer], list[dict[str, Any]]],
    *,
    extra_generation_seconds: float = 0.0,
    polish_top_k: int | None = None,
) -> _TrackRun:
    scorer = TrueObjectiveScorer(context, grid=grid)
    started = time.perf_counter()
    proposals = generate(scorer)
    scored = scorer.score_proposals(proposals)
    generation_seconds = time.perf_counter() - started + extra_generation_seconds
    evaluations = scorer.evaluations
    polish_started = time.perf_counter()
    traces = (
        polish_top_candidates(
            context,
            scored,
            top_k=polish_top_k or settings.polish_top_k,
            max_adjustment=settings.polish_max_adjustment,
            max_evaluations=settings.polish_max_evaluations,
        )
        if scored
        else []
    )
    return _TrackRun(
        track=track,
        view=view,
        scored=scored,
        traces=traces,
        budget=budget,
        generation_seconds=generation_seconds,
        polish_seconds=time.perf_counter() - polish_started,
        evaluations_generation=evaluations,
    )


def _best_trace(traces: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    if not traces:
        return None
    return min(
        traces,
        key=lambda t: (
            not t["final_feasible"],
            t["final_true_objective"],
            t["start_rank"],
        ),
    )


def _diversity(bitstrings: Sequence[str], sample: int) -> float | None:
    if len(bitstrings) < 2:
        return None
    rng = np.random.default_rng(0)
    chosen = (
        list(bitstrings)
        if len(bitstrings) <= sample
        else [
            bitstrings[i]
            for i in rng.choice(len(bitstrings), size=sample, replace=False)
        ]
    )
    levels = np.stack([levels_from_bitstring(bits) for bits in chosen]).astype(float)
    distances = np.abs(levels[:, None, :] - levels[None, :, :]).sum(axis=2) / 100.0
    upper = distances[np.triu_indices(len(chosen), k=1)]
    return float(upper.mean())


def _summarize(
    run: _TrackRun,
    *,
    settings: HybridSettings,
    space: StateSpace,
    grid: TrueGrid | None,
    qubo_best_energy: float,
    j_grid: float | None,
    grid_top: Mapping[int, set[str]],
    classical_bits: set[str],
) -> dict[str, Any]:
    scored = run.scored
    generated = len(scored)
    shortfall = max(0, run.budget - generated) if run.view == "candidate_budget" else 0
    status = run.status
    if status == "OK" and shortfall > 0:
        status = "SHORTFALL"
    row: dict[str, Any] = {
        "track": run.track,
        "view": run.view,
        "status": status,
        "status_reason": run.reason,
        "budget_candidates": run.budget,
        "generated_unique": generated,
        "shortfall": shortfall,
        "true_evaluations_generation": run.evaluations_generation,
        "true_evaluations_polish": int(
            sum(t["true_objective_evaluations"] for t in run.traces)
        ),
        "generation_seconds": float(run.generation_seconds),
        "polish_seconds": float(run.polish_seconds),
        "predicate_feasible_count": int(
            sum(space.predicate_feasible[int(r["bitstring"], 2)] for r in scored)
        ),
        "true_feasible_count": int(sum(bool(r["true_feasible"]) for r in scored)),
        "raw_best_true_objective": None,
        "polished_best_true_objective": None,
        **{f"extra_{k}": v for k, v in run.extras.items()},
    }
    if scored:
        best = rank_scored(scored)[0]
        energies = [
            float(space.energies[int(r["bitstring"], 2)])
            for r in scored
            if space.predicate_feasible[int(r["bitstring"], 2)]
        ]
        row.update(
            {
                "raw_best_true_objective": float(best["true_objective"]),
                "raw_best_feasible": bool(best["true_feasible"]),
                "raw_best_bitstring": str(best["bitstring"]),
                "raw_best_source_rank": int(best.get("source_rank") or 0),
                "raw_best_qubo_energy_gap": (min(energies) - qubo_best_energy)
                if energies
                else None,
                "diversity_mean_l1": _diversity(
                    [str(r["bitstring"]) for r in scored], settings.diversity_sample
                ),
                "novelty_vs_classical_true": (
                    float(
                        np.mean(
                            [str(r["bitstring"]) not in classical_bits for r in scored]
                        )
                    )
                    if classical_bits
                    else None
                ),
            }
        )
        if grid is not None and j_grid is not None:
            gap = float(best["true_objective"]) - j_grid
            scale = max(abs(j_grid), 1e-12)
            feasible_values = np.asarray(
                [float(r["true_objective"]) for r in scored if r["true_feasible"]]
            )
            row["raw_best_abs_gap"] = gap
            row["raw_best_rel_gap"] = gap / scale
            row["raw_best_true_rank"] = (
                grid.feasible_rank(float(best["true_objective"]))
                if best["true_feasible"]
                else None
            )
            for eps in settings.near_optimal_eps:
                row[f"near_optimal_rate_{eps:g}"] = (
                    float(np.mean((feasible_values - j_grid) / scale <= eps))
                    if feasible_values.size
                    else 0.0
                )
            bits = {str(r["bitstring"]) for r in scored}
            for k, top in grid_top.items():
                row[f"recall_true_top_{k}"] = len(bits & top) / max(1, len(top))
    winner = _best_trace(run.traces)
    if winner is not None:
        snapshot = winner["final_snapshot"]
        row.update(
            {
                "polished_best_true_objective": float(winner["final_true_objective"]),
                "polished_best_feasible": bool(winner["final_feasible"]),
                "winner_start_rank": int(winner["start_rank"]),
                "winner_start_bitstring": str(winner["start_bitstring"]),
                "winner_start_true_objective": float(winner["start_true_objective"]),
                "winner_polish_gain": float(winner["objective_improvement"]),
                "winner_polishing_dependency": float(winner["polishing_dependency"]),
                "winner_final_reductions_pct": json.dumps(
                    winner["final_reductions_pct"]
                ),
                "winner_true_cvar": snapshot["true_cvar"],
                "winner_cvar_before": snapshot["cvar_before"],
                "winner_return_sacrifice": snapshot["return_sacrifice"],
                "winner_transaction_cost": snapshot["transaction_cost"],
                "winner_liquidity_penalty": snapshot["liquidity_penalty"],
                "winner_turnover": snapshot["turnover"],
                "winner_cash_weight_after": snapshot["cash_weight_after"],
                "winner_worst_drawdown_after": snapshot["worst_drawdown_after"],
                "winner_constraint_violations": snapshot["constraint_violation_count"],
                "polish_gain_raw_to_final": (
                    float(row["raw_best_true_objective"])
                    - float(winner["final_true_objective"])
                    if row["raw_best_true_objective"] is not None
                    else None
                ),
            }
        )
    return row


def run_instance(
    inputs: InstanceInputs,
    settings: HybridSettings,
    *,
    experiment_id: str,
    qaoa_solver: Callable[..., Any] = solve_qaoa_one_seed_fast,
    logger: Any | None = None,
    transfer_parameters: Mapping[str, Sequence[float]] | None = None,
) -> InstanceOutputs:
    def log(message: str, *args: object) -> None:
        if logger is not None:
            logger.info(message, *args)

    started = time.perf_counter()
    timings: dict[str, float] = {}
    cfg = inputs.config
    instance_id = str(inputs.instance["instance_id"])

    t0 = time.perf_counter()
    frame = select_four_level_candidates(
        inputs.scenarios,
        inputs.tickers,
        inputs.weights,
        inputs.cash_weight,
        inputs.eligibility,
        cfg,
        output_candidates=settings.candidate_count,
        ineligible_reasons=inputs.ineligible_reasons,
    )
    order = [str(item["ticker"]) for item in candidate_order(frame)]
    if len(order) != settings.candidate_count:
        raise InstanceSkipped(
            f"candidate selection underfilled: {len(order)} < {settings.candidate_count}."
        )
    candidate_order_hash = stable_hash(order)
    context = build_objective_context(
        inputs.scenarios, inputs.tickers, inputs.weights, inputs.cash_weight, order, cfg
    )
    eval_seconds = _measure_eval_seconds(
        context, settings.eval_timing_samples, int(inputs.instance["scenario_seed"])
    )
    timings["candidates_and_context"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    dataset = sample_objective_dataset(
        inputs.scenarios,
        inputs.tickers,
        inputs.weights,
        inputs.cash_weight,
        order,
        cfg,
        candidate_order_hash=candidate_order_hash,
    )
    Z, y, _ = structured_samples_to_arrays(dataset.train, order)
    model = fit_quadratic_surrogate(Z, y)
    verify_meta = verify_quadratic_consistency(
        model, variable_names=four_level_variable_names(order)
    )
    qubo_hash = stable_hash({"candidate_order": order, **model.to_dict()})
    Z_hold, y_hold, _ = structured_samples_to_arrays(dataset.holdout, order)
    holdout_spearman = (
        float(spearmanr(model.evaluate_batch(Z_hold), y_hold).statistic)
        if len(y_hold) > 2
        else None
    )
    timings["surrogate"] = time.perf_counter() - t0

    policy = RiskPolicy.from_config(cfg)
    constraints, encoding = policy_to_quantum_constraints(
        policy,
        cfg,
        candidate_weights={ticker: inputs.weights[ticker] for ticker in order},
        cash_weight_before=inputs.cash_weight,
    )
    try:
        space = enumerate_state_space(model, constraints)
    except ValueError as exc:
        if "no predicate-feasible state" not in str(exc):
            raise
        raise InstanceSkipped(
            f"NO_TRUE_FEASIBLE_STATE (predicate): {constraints}"
        ) from exc
    all_indices = np.arange(space.total_states)
    qubo_best_index = int(
        np.lexsort((all_indices, space.energies, ~space.predicate_feasible))[0]
    )
    qubo_best_energy = float(space.energies[qubo_best_index])

    t0 = time.perf_counter()
    grid = (
        exact_true_grid(
            context,
            workers=settings.grid_workers,
            chunk_size=settings.grid_chunk_size,
            max_bits=settings.grid_max_bits,
        )
        if context.bit_count <= settings.grid_max_bits
        else None
    )
    timings["exact_true_grid"] = time.perf_counter() - t0
    if grid is not None and not grid.feasible.any():
        # Không có nghiệm hợp lệ thì mọi gap/uplift chỉ là so sánh giữa các nghiệm vi phạm policy.
        raise InstanceSkipped(
            f"NO_TRUE_FEASIBLE_STATE: 0/{grid.values.shape[0]} grid states satisfy the policy."
        )
    j_zero = float(context.evaluate(np.zeros(len(inputs.tickers))).value)
    references: dict[str, Any] = {
        "qubo_optimum_index": qubo_best_index,
        "qubo_optimum_bitstring": format(qubo_best_index, f"0{space.bit_count}b"),
        "qubo_optimum_energy": qubo_best_energy,
        "total_states": space.total_states,
        "total_predicate_feasible_states": space.total_feasible_states,
        "j_no_action": j_zero,
        "reference_kind": "EXACT_TRUE_GRID" if grid is not None else "BEST_KNOWN_ONLY",
    }
    grid_top: dict[int, set[str]] = {}
    reference_rows: list[dict[str, Any]] = []
    reference_traces: list[dict[str, Any]] = []
    j_grid: float | None = None
    true_best_index: int | None = None
    if grid is not None:
        true_best_index = grid.best_index()
        j_grid = float(grid.values[true_best_index])
        width = space.bit_count
        for k in settings.recall_top_k:
            grid_top[k] = {format(int(i), f"0{width}b") for i in grid.top_indices(k)}
        qubo_true_value = float(grid.values[qubo_best_index])
        feasible_mask = grid.feasible & space.predicate_feasible
        references.update(
            {
                "true_grid_optimum_index": true_best_index,
                "true_grid_optimum_bitstring": format(true_best_index, f"0{width}b"),
                "j_star_grid": j_grid,
                "true_feasible_states": int(grid.feasible.sum()),
                "grid_seconds": grid.seconds,
                "grid_workers": grid.workers,
                "qubo_optimum_equals_true_grid_optimum": qubo_best_index
                == true_best_index,
                "qubo_optimum_true_objective": qubo_true_value,
                "qubo_optimum_true_rank": grid.feasible_rank(qubo_true_value),
                "qubo_optimum_true_gap": qubo_true_value - j_grid,
                "spearman_energy_vs_true_all_feasible": float(
                    spearmanr(
                        space.energies[feasible_mask], grid.values[feasible_mask]
                    ).statistic
                ),
            }
        )
        scorer = TrueObjectiveScorer(context, grid=grid)
        reference_rows = scorer.score_proposals(
            [
                {
                    "bitstring": format(int(index), f"0{width}b"),
                    "source_method": "exact_true_grid",
                    "source_rank": rank,
                    "source_seed": None,
                    "raw_probability": None,
                }
                for rank, index in enumerate(
                    grid.top_indices(settings.reference_polish_top_k), start=1
                )
            ]
        )
        reference_traces = polish_top_candidates(
            context,
            reference_rows,
            top_k=settings.reference_polish_top_k,
            max_adjustment=settings.polish_max_adjustment,
            max_evaluations=settings.polish_max_evaluations,
        )
        best_reference = _best_trace(reference_traces)
        references["j_star_polished_reference"] = (
            float(best_reference["final_true_objective"]) if best_reference else None
        )

    runs: list[_TrackRun] = []
    budget = settings.candidate_budget
    seeds = settings.generator_seeds

    # ---- QAOA (chạy trước để boltzmann khớp energy và compute view biết wall time) ----
    qaoa_cfg = settings.qaoa
    dist_frames: list[pd.DataFrame] = []
    dist_metrics_by_track: dict[str, dict[str, Any]] = {}
    qaoa_attempts_by_track: dict[str, list[dict[str, Any]]] = {}
    qaoa_walls: dict[str, float] = {}
    normalization: dict[str, Any] | None = None
    qaoa_tracks = [
        t for t in ("qaoa", "qaoa_transfer") if t in settings.candidate_tracks
    ]
    if qaoa_tracks:
        qaoa_model = model
        energy_scale, energy_offset = 1.0, 0.0
        target_range = (qaoa_cfg.get("energy_normalization") or {}).get("target_range")
        if target_range is not None:
            qaoa_model, norm = normalize_for_qaoa(model, float(target_range))
            energy_scale, energy_offset = norm.scale, norm.offset
            normalization = asdict(norm)
        qp = build_quadratic_program(
            qaoa_model.Q,
            qaoa_model.linear,
            qaoa_model.constant,
            ticker_order=four_level_variable_names(order),
        )
        reference_indices = {"qubo_optimum": qubo_best_index}
        if true_best_index is not None:
            reference_indices["true_grid_optimum"] = true_best_index
        for qaoa_track in qaoa_tracks:
            t0 = time.perf_counter()
            initial_point = None
            maxiter = int(qaoa_cfg["maxiter"])
            if qaoa_track == "qaoa_transfer":
                initial_point = (transfer_parameters or {}).get(instance_id)
                maxiter = int(qaoa_cfg["transfer"]["maxiter"])
                if initial_point is None:
                    qaoa_walls[qaoa_track] = 0.0
                    runs.append(
                        _TrackRun(
                            qaoa_track,
                            "candidate_budget",
                            [],
                            [],
                            budget,
                            0.0,
                            0.0,
                            0,
                            status="FAILED",
                            reason="no transfer parameters registered",
                        )
                    )
                    continue
            run = run_qaoa_seeds(
                qp,
                seeds=[int(s) for s in qaoa_cfg["seeds"]],
                shots=int(qaoa_cfg["shots"]),
                maxiter=maxiter,
                reps=int(qaoa_cfg.get("reps", 1)),
                warm_start=bool(qaoa_cfg.get("warm_start", False)),
                feasibility_constraints=constraints or None,
                seed_timeout_seconds=float(qaoa_cfg["seed_timeout_seconds"]),
                total_timeout_seconds=qaoa_cfg.get("total_timeout_seconds"),
                solver=qaoa_solver,
                initial_point=initial_point,
            )
            rows = distribution_rows(
                run, space, energy_scale=energy_scale, energy_offset=energy_offset
            )
            metrics = distribution_metrics(
                rows, space, reference_indices=reference_indices
            )
            dist_metrics_by_track[qaoa_track] = metrics
            qaoa_attempts_by_track[qaoa_track] = run.attempts
            qaoa_walls[qaoa_track] = run.wall_seconds
            if rows:
                dist_frames.append(
                    pd.DataFrame(rows).assign(
                        experiment_id=experiment_id,
                        instance_id=instance_id,
                        track=qaoa_track,
                        candidate_order_hash=candidate_order_hash,
                        qubo_hash=qubo_hash,
                    )
                )
            track_run = _run_track(
                qaoa_track,
                "candidate_budget",
                context,
                grid,
                settings,
                budget,
                lambda _scorer, rw=rows, tr=qaoa_track: _proposal_dicts(
                    qaoa_proposals(rw, space, budget=budget, track=tr)
                ),
                extra_generation_seconds=run.wall_seconds,
            )
            track_run.extras = {
                "seeds_completed": len(run.results),
                "seeds_registered": len(qaoa_cfg["seeds"]),
                "qaoa_wall_seconds": run.wall_seconds,
                "qaoa_maxiter": maxiter,
                "circuit_evaluations_total": int(
                    sum(a.get("circuit_evaluations", 0) for a in run.attempts)
                ),
                "mass_on_true_grid_optimum": metrics["mass_on_reference"].get(
                    "true_grid_optimum"
                ),
                "top_k_mass": metrics["top_k_mass"],
            }
            if not run.results:
                track_run.status, track_run.reason = "FAILED", "no QAOA seed completed"
            timings[qaoa_track] = time.perf_counter() - t0
            runs.append(track_run)
            log(
                "[hybrid] %s %s seeds=%d/%d wall=%.1fs unique=%s mass_opt=%s",
                instance_id,
                qaoa_track,
                len(run.results),
                len(qaoa_cfg["seeds"]),
                run.wall_seconds,
                metrics.get("unique_measured"),
                metrics["mass_on_reference"],
            )
    dist_frame = (
        pd.concat(dist_frames, ignore_index=True) if dist_frames else pd.DataFrame()
    )
    dist_metrics = dist_metrics_by_track.get("qaoa", {})
    qaoa_attempts = qaoa_attempts_by_track.get("qaoa", [])

    boltzmann_fit: dict[str, Any] | None = None
    for track in settings.candidate_tracks:
        if track in ("qaoa", "qaoa_transfer"):
            continue
        seed = seeds[track]
        if track == "random_uniform":
            runs.append(
                _run_track(
                    track,
                    "candidate_budget",
                    context,
                    grid,
                    settings,
                    budget,
                    lambda _s, sd=seed: _proposal_dicts(
                        uniform_pool(space, budget=budget, seed=sd)
                    ),
                )
            )
        elif track == "random_stratified":
            runs.append(
                _run_track(
                    track,
                    "candidate_budget",
                    context,
                    grid,
                    settings,
                    budget,
                    lambda _s, sd=seed: _proposal_dicts(
                        stratified_pool(space, budget=budget, seed=sd)
                    ),
                )
            )
        elif track == "classical_surrogate":
            runs.append(
                _run_track(
                    track,
                    "candidate_budget",
                    context,
                    grid,
                    settings,
                    budget,
                    lambda _s, sd=seed: _proposal_dicts(
                        surrogate_local_search_pool(space, budget=budget, seed=sd)[0]
                    ),
                )
            )
        elif track == "classical_true":
            runs.append(
                _run_track(
                    track,
                    "candidate_budget",
                    context,
                    grid,
                    settings,
                    budget,
                    lambda scorer, sd=seed: true_coordinate_search_pool(
                        scorer,
                        predicate_mask=space.predicate_feasible,
                        budget=budget,
                        seed=sd,
                    )[0],
                )
            )
        elif track == "boltzmann":
            target = dist_metrics.get("pooled_mean_feasible_energy")
            if target is None:
                runs.append(
                    _TrackRun(
                        track,
                        "candidate_budget",
                        [],
                        [],
                        budget,
                        0.0,
                        0.0,
                        0,
                        status="EMPTY",
                        reason="no QAOA distribution to match energy against",
                    )
                )
                continue
            holder: dict[str, Any] = {}

            def generate_boltzmann(_scorer, sd=seed, tgt=float(target), out=holder):
                proposals, fit = boltzmann_pool(
                    space, budget=budget, seed=sd, target_mean_energy=tgt
                )
                out["fit"] = asdict(fit)
                return _proposal_dicts(proposals)

            boltzmann_run = _run_track(
                track,
                "candidate_budget",
                context,
                grid,
                settings,
                budget,
                generate_boltzmann,
            )
            boltzmann_fit = holder.get("fit")
            boltzmann_run.extras = {
                "beta": (boltzmann_fit or {}).get("beta"),
                "fit_status": (boltzmann_fit or {}).get("status"),
            }
            runs.append(boltzmann_run)

    # ---- compute-budget view: mỗi track *_transfer khớp wall của qaoa_transfer, còn lại khớp qaoa ----
    cap = settings.compute_budget_max_evaluations
    compute_details: dict[str, Any] = {
        "true_eval_seconds_measured": eval_seconds,
        "rule": "ceil(qaoa_wall_seconds / true_eval_seconds) + candidate_budget, capped",
    }
    for track in settings.compute_tracks:
        source = "qaoa_transfer" if track.endswith("_transfer") else "qaoa"
        wall = qaoa_walls.get(source, 0.0)
        equivalent = (
            math.ceil(wall / eval_seconds) + budget if eval_seconds > 0 else budget
        )
        compute_budget = min(equivalent, cap)
        compute_details[source] = {
            "qaoa_wall_seconds": wall,
            "eval_equivalent": equivalent,
            "compute_budget_evaluations": compute_budget,
            "cap_applied": equivalent > cap,
        }
        seed = seeds[track]
        if track.startswith("classical_true_compute"):
            runs.append(
                _run_track(
                    track,
                    "compute_budget",
                    context,
                    grid,
                    settings,
                    compute_budget,
                    lambda scorer, sd=seed, cb=compute_budget: (
                        true_coordinate_search_pool(
                            scorer,
                            predicate_mask=space.predicate_feasible,
                            budget=cb,
                            seed=sd,
                        )[0]
                    ),
                )
            )
        elif track.startswith("random_uniform_compute"):
            runs.append(
                _run_track(
                    track,
                    "compute_budget",
                    context,
                    grid,
                    settings,
                    compute_budget,
                    lambda _s, sd=seed, cb=compute_budget: _proposal_dicts(
                        uniform_pool(space, budget=cb, seed=sd)
                    ),
                )
            )

    # ---- ablation: polish từ hành động đồng mức (không cần bộ sinh nào) ----
    if "heuristic_baselines" in settings.ablation_tracks:

        def generate_heuristics(_scorer):
            rows = []
            for rank, level in enumerate((10, 20, 30), start=1):
                bits = bitstring_from_levels([level] * settings.candidate_count)
                rows.append(
                    {
                        "bitstring": bits,
                        "source_method": f"uniform_level_{level}",
                        "source_rank": rank,
                        "source_seed": None,
                        "raw_probability": None,
                    }
                )
            return rows

        runs.append(
            _run_track(
                "heuristic_baselines",
                "ablation",
                context,
                grid,
                settings,
                3,
                generate_heuristics,
                polish_top_k=3,
            )
        )

    classical_bits = {
        str(r["bitstring"])
        for run_ in runs
        if run_.track == "classical_true"
        for r in run_.scored
    }
    summaries = [
        _summarize(
            run_,
            settings=settings,
            space=space,
            grid=grid,
            qubo_best_energy=qubo_best_energy,
            j_grid=j_grid,
            grid_top=grid_top,
            classical_bits=classical_bits,
        )
        for run_ in runs
    ]
    finals = [
        s["polished_best_true_objective"]
        for s in summaries
        if s["polished_best_true_objective"] is not None
        and s.get("polished_best_feasible")
    ]
    if references.get("j_star_polished_reference") is not None:
        finals.append(references["j_star_polished_reference"])
    j_best_known = float(min(finals)) if finals else None
    references["j_best_known"] = j_best_known
    improvement_scale = (j_zero - j_best_known) if j_best_known is not None else None
    references["improvement_scale_no_action_minus_best_known"] = improvement_scale
    for summary in summaries:
        final = summary["polished_best_true_objective"]
        summary["polished_abs_gap_best_known"] = (
            final - j_best_known
            if final is not None and j_best_known is not None
            else None
        )
        summary["polished_rel_gap_best_known"] = (
            (final - j_best_known) / max(abs(j_best_known), 1e-12)
            if final is not None and j_best_known is not None
            else None
        )

    common = {"experiment_id": experiment_id, "instance_id": instance_id}
    hashes = {"candidate_order_hash": candidate_order_hash, "qubo_hash": qubo_hash}

    def pool_rows(track: str, view: str, scored: Sequence[Mapping[str, Any]]):
        for row in scored:
            bits = str(row["bitstring"])
            index = int(bits, 2)
            yield {
                **common,
                **hashes,
                "track": track,
                "view": view,
                "source_method": str(row.get("source_method") or track),
                "source_seed": row.get("source_seed"),
                "source_rank": int(row.get("source_rank") or 1),
                "raw_probability": row.get("raw_probability"),
                "qubo_energy": float(space.energies[index]),
                "bitstring": bits,
                "effective_action_hash": effective_action_hash(
                    levels_from_bitstring(bits)
                ),
                "predicate_feasible": bool(space.predicate_feasible[index]),
                "true_objective": float(row["true_objective"]),
                "true_feasible": bool(row["true_feasible"]),
            }

    pool_records = list(pool_rows(REFERENCE_TRACK, "reference", reference_rows))
    polish_records = [
        {**common, "track": REFERENCE_TRACK, "view": "reference", **trace}
        for trace in reference_traces
    ]
    for run_ in runs:
        pool_records.extend(pool_rows(run_.track, run_.view, run_.scored))
        polish_records.extend(
            {**common, "track": run_.track, "view": run_.view, **trace}
            for trace in run_.traces
        )
    pools = pd.DataFrame(pool_records)
    if not pools.empty:
        pools["source_seed"] = pools["source_seed"].astype("Int64")
        pools["raw_probability"] = pools["raw_probability"].astype(float)
    polish = pd.DataFrame(polish_records)
    if not polish.empty:
        polish["final_snapshot"] = polish["final_snapshot"].map(json.dumps)
        polish["final_reductions_pct"] = polish["final_reductions_pct"].map(json.dumps)
    tracks = pd.DataFrame([{**common, **s} for s in summaries])

    validate_candidate_pool(pools, bit_count=space.bit_count)
    validate_polish_trace(polish)
    validate_track_results(tracks)
    if not dist_frame.empty:
        validate_qaoa_distribution(dist_frame, bit_count=space.bit_count)
    checklist = attribution_checklist(
        pools,
        polish.loc[polish["track"] != REFERENCE_TRACK] if not polish.empty else polish,
        tracks,
        bit_count=space.bit_count,
        polish_top_k=max(settings.polish_top_k, 3),
        polish_max_evaluations=settings.polish_max_evaluations,
    )
    if checklist["status"] != "PASS":
        raise HybridAttributionError(
            f"{instance_id}: attribution checklist FAIL: {checklist}"
        )

    qaoa_summary = next((s for s in summaries if s["track"] == "qaoa"), None)
    result = {
        **common,
        "status_label": inputs.instance.get("set"),
        "instance": inputs.instance,
        "backend": "StatevectorSampler (simulator)",
        "claim_scope": "QAOA-assisted hybrid on simulator; no quantum advantage claim",
        "input_metadata": inputs.metadata,
        "candidate_order": order,
        **hashes,
        "surrogate": {
            "train_samples": len(y),
            "holdout_spearman": holdout_spearman,
            "residual_sum_squares": model.residual_sum_squares,
            "verify_consistency": verify_meta,
        },
        "quantum_constraints": constraints,
        "quantum_constraint_encoding": encoding,
        "references": references,
        "qaoa_distribution_metrics": dist_metrics,
        "qaoa_attempts": qaoa_attempts,
        "qaoa_attempts_by_track": qaoa_attempts_by_track,
        "qaoa_distribution_metrics_by_track": dist_metrics_by_track,
        "qaoa_energy_normalization": normalization,
        "boltzmann_fit": boltzmann_fit,
        "compute_budget": compute_details,
        "budgets": {
            "candidate_budget": budget,
            "polish_top_k": settings.polish_top_k,
            "polish_max_evaluations": settings.polish_max_evaluations,
            "polish_max_adjustment": settings.polish_max_adjustment,
        },
        "phase0_answers": {
            "coverage_definition": (
                "unique measured bitstrings across all seeds and shots, duplicates counted once; "
                "reported against all states and predicate-feasible states"
            ),
            "coverage_all": dist_metrics.get("coverage_all_fraction"),
            "coverage_feasible": dist_metrics.get("coverage_feasible_fraction"),
            "optimum_used_for_raw_gap": "J*_grid (true financial objective on 4-level grid)",
            "optimum_used_for_polished_gap": "J_best_known (min of J*_polished reference and "
            "all track finals)",
            "qubo_vs_true_optimum_same_state": references.get(
                "qubo_optimum_equals_true_grid_optimum"
            ),
            "qaoa_polishing_dependency": (qaoa_summary or {}).get(
                "winner_polishing_dependency"
            ),
            "qaoa_raw_gap": (qaoa_summary or {}).get("raw_best_abs_gap"),
            "qaoa_polished_gap": (qaoa_summary or {}).get(
                "polished_abs_gap_best_known"
            ),
        },
        "attribution_checklist": checklist,
        "timings_seconds": {**timings, "total": time.perf_counter() - started},
    }
    return InstanceOutputs(instance_id, dist_frame, pools, polish, tracks, result)


# --------------------------------------------------------------------------- experiment I/O


def experiment_dir(paths: ArtifactPaths, experiment_id: str) -> Any:
    return paths.for_stage(Stage.HYBRID, experiment_id)


def write_instance_outputs(
    outputs: InstanceOutputs, paths: ArtifactPaths, experiment_id: str
) -> None:
    target = paths.for_stage(
        Stage.HYBRID, f"{experiment_id}/instances/{outputs.instance_id}"
    )
    target.mkdir(parents=True, exist_ok=True)
    # CSV nén, KHÔNG parquet: tiến trình này đã nạp qiskit, và `to_parquet` sau đó segfault trong
    # mimalloc của pyarrow (đã tái hiện 2026-09-13 trên x01; cùng lỗi ghi ở docstring `run.py`).
    # Bitstring giữ dạng chuỗi — đọc lại bằng `dtype={"bitstring": str, ...}`.
    if not outputs.distribution.empty:
        outputs.distribution.to_csv(target / "qaoa_distribution.csv.gz", index=False)
    outputs.pools.to_csv(target / "candidate_pools.csv.gz", index=False)
    outputs.polish.to_csv(target / "polishing_results.csv.gz", index=False)
    outputs.tracks.to_csv(target / "track_results.csv", index=False)
    # instance_result.json ghi CUỐI: sự tồn tại của nó = instance hoàn tất (dùng cho resume).
    (target / "instance_result.json").write_text(
        json.dumps(outputs.result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def run_experiment(
    manifest: Mapping[str, Any],
    config: Mapping[str, Any],
    settings: HybridSettings,
    data: HybridData,
    paths: ArtifactPaths,
    *,
    logger: Any,
    limit: int | None = None,
    resume: bool = True,
    only: Sequence[str] | None = None,
    qaoa_solver: Callable[..., Any] = solve_qaoa_one_seed_fast,
    transfer_parameters: Mapping[str, Sequence[float]] | None = None,
) -> dict[str, int]:
    root = experiment_dir(paths, settings.experiment_id)
    root.mkdir(parents=True, exist_ok=True)
    attempts_path = root / "hybrid_attempts.jsonl"
    counts = {"completed": 0, "skipped": 0, "failed": 0, "resumed": 0}
    instances = [
        item
        for item in manifest["instances"]
        if not only or item["instance_id"] in set(only)
    ]
    for item in instances[: limit or None]:
        instance_id = str(item["instance_id"])
        done = paths.for_stage(
            Stage.HYBRID,
            f"{settings.experiment_id}/instances/{instance_id}/instance_result.json",
        )
        if resume and done.exists():
            counts["resumed"] += 1
            continue
        started = time.perf_counter()
        record: dict[str, Any] = {
            "instance_id": instance_id,
            "set": manifest.get("set"),
            "manifest_hash": manifest["instances_hash"],
            "started_at": pd.Timestamp.now(tz="UTC").isoformat(),
        }
        try:
            logger.info("[hybrid] building %s", instance_id)
            inputs = build_instance_inputs(item, config, settings, data)
            outputs = run_instance(
                inputs,
                settings,
                experiment_id=settings.experiment_id,
                qaoa_solver=qaoa_solver,
                logger=logger,
                transfer_parameters=transfer_parameters,
            )
            write_instance_outputs(outputs, paths, settings.experiment_id)
            record.update(status="completed")
            counts["completed"] += 1
        except InstanceSkipped as exc:
            record.update(status="skipped", reason=str(exc))
            counts["skipped"] += 1
            logger.warning("[hybrid] skipped %s: %s", instance_id, exc)
        except Exception as exc:  # noqa: BLE001 — mọi thất bại phải vào attempts, không lọc
            record.update(
                status="failed",
                reason=f"{type(exc).__name__}: {exc}",
                traceback=traceback.format_exc()[-4000:],
            )
            counts["failed"] += 1
            logger.error("[hybrid] failed %s: %s", instance_id, exc)
        record["seconds"] = time.perf_counter() - started
        with attempts_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return counts
