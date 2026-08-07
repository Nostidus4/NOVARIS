"""True-objective financial benchmark for exact / QAOA / classical bitstrings (GATE-08 G8)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt

from qshield_risk.evaluate import required_float
from qshield_risk.metrics import alpha_key
from qshield_risk.objective import FinancialObjective, financial_objective
from qshield_risk.portfolio import validate_ticker_order
from qshield_risk.rerank import materiality_from_cvar
from qshield_risk.sampling import decode_four_level_bits

_SOLVER_ORDER = ("exact", "qaoa", "classical")


def _read_json_mapping(payload: Mapping[str, Any] | None, label: str) -> dict[str, Any]:
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise TypeError(f"[risk.true_benchmark] {label} must be a mapping.")
    return dict(payload)


def reductions_from_bitstring(
    bitstring: str,
    *,
    universe_tickers: Sequence[str],
    candidate_order: Sequence[str],
) -> np.ndarray:
    """Map a four-level bitstring onto the full universe reduction vector."""
    tickers = validate_ticker_order(universe_tickers)
    ordered = tuple(str(ticker) for ticker in candidate_order)
    if not ordered or len(set(ordered)) != len(ordered):
        raise ValueError(
            "[risk.true_benchmark] candidate_order must be unique and non-empty."
        )
    missing = sorted(set(ordered) - set(tickers))
    if missing:
        raise ValueError(
            f"[risk.true_benchmark] candidates absent from ticker_order: {missing}."
        )
    expected = 2 * len(ordered)
    text = str(bitstring)
    if len(text) != expected or any(char not in "01" for char in text):
        raise ValueError(
            f"[risk.true_benchmark] bitstring={text!r} must be length {expected} binary."
        )
    bits = np.asarray([int(char) for char in text], dtype=int)
    candidate_reductions = decode_four_level_bits(bits, candidate_count=len(ordered))
    reductions = np.zeros(len(tickers), dtype=float)
    indices = [tickers.index(ticker) for ticker in ordered]
    reductions[indices] = candidate_reductions
    return reductions


def _metrics_snapshot(metrics: Mapping[str, float]) -> dict[str, float]:
    return {str(key): float(value) for key, value in metrics.items()}


def _score_objective(
    result: FinancialObjective,
    *,
    primary_key: str,
    materiality_threshold: float,
) -> dict[str, Any]:
    cvar_before = float(result.before.cvar[primary_key])
    cvar_after = float(result.after.cvar[primary_key])
    cvar_abs_reduction = cvar_before - cvar_after
    materiality = materiality_from_cvar(
        cvar_before, cvar_after, threshold=materiality_threshold
    )
    relative = float(materiality["true_cvar_relative_reduction"])
    return_sacrifice = float(result.components["return_sacrifice"].raw)
    transaction_cost = float(result.trade.costs.total)
    drawdown_before = float(result.before.worst_scenario_max_drawdown)
    drawdown_after = float(result.after.worst_scenario_max_drawdown)
    # Drawdown is negative; reduction is improvement toward zero (after − before when both ≤ 0).
    worst_drawdown_reduction = float(drawdown_after - drawdown_before)
    cost_per = (
        float(transaction_cost / cvar_abs_reduction)
        if cvar_abs_reduction > 0.0
        else None
    )
    return {
        "true_objective": float(result.value),
        "true_cvar": cvar_after,
        "true_cvar_before": cvar_before,
        "true_cvar_after": cvar_after,
        "cvar_before": _metrics_snapshot(result.before.cvar),
        "cvar_after": _metrics_snapshot(result.after.cvar),
        "cvar_reduction_relative": relative,
        "cvar_reduction_pct": relative * 100.0,
        "CVaR_reduction": cvar_abs_reduction,
        "CVaR_reduction_pct": relative,
        "expected_return_sacrifice": return_sacrifice,
        "expected_return_before": float(result.before.expected_horizon_return),
        "expected_return_after": float(result.after.expected_horizon_return),
        "worst_drawdown_before": drawdown_before,
        "worst_drawdown_after": drawdown_after,
        "worst_drawdown_reduction": worst_drawdown_reduction,
        "turnover": float(result.trade.turnover),
        "transaction_cost": transaction_cost,
        "liquidity_penalty": float(result.trade.costs.liquidity_penalty),
        "cost_per_cvar_reduction": cost_per,
        "cost_per_CVaR_reduction": cost_per,
        "constraint_violations": list(result.constraint_violations),
        **materiality,
    }


def extract_solver_bitstrings(
    *,
    exact_payload: Mapping[str, Any] | None,
    qaoa_payload: Mapping[str, Any] | None,
    workflow_benchmark: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Pull best feasible bitstrings for exact / QAOA / classical from optimization artifacts."""
    exact = _read_json_mapping(exact_payload, "exact_solution")
    qaoa = _read_json_mapping(qaoa_payload, "qaoa_results")
    bench = _read_json_mapping(workflow_benchmark, "workflow_benchmark")

    exact_bits = exact.get("best_feasible_bitstring") or bench.get(
        "exact_best_bitstring"
    )
    exact_energy = exact.get("best_feasible_energy")
    if exact_energy is None:
        exact_energy = bench.get("exact_best_energy")
    solvers: dict[str, dict[str, Any]] = {
        "exact": {
            "available": bool(exact_bits),
            "bitstring": str(exact_bits) if exact_bits else None,
            "qubo_energy": float(exact_energy) if exact_energy is not None else None,
            "source": (
                "exact_solution.json"
                if exact.get("best_feasible_bitstring")
                else "workflow_benchmark.json"
            ),
        }
    }

    classical_bits = bench.get("classical_bitstring")
    classical_energy = bench.get("classical_energy")
    solvers["classical"] = {
        "available": bool(classical_bits),
        "bitstring": str(classical_bits) if classical_bits else None,
        "qubo_energy": (
            float(classical_energy) if classical_energy is not None else None
        ),
        "source": "workflow_benchmark.json",
    }

    qaoa_bits: str | None = None
    qaoa_energy: float | None = None
    qaoa_source = "qaoa_results.json"
    seeds = qaoa.get("seeds") or {}
    if isinstance(seeds, Mapping) and seeds:
        best: tuple[float, str] | None = None
        for seed_payload in seeds.values():
            if not isinstance(seed_payload, Mapping):
                continue
            if seed_payload.get("feasible") is False:
                continue
            bitstring = seed_payload.get("bitstring")
            energy = seed_payload.get("energy")
            if bitstring is None or energy is None:
                continue
            candidate = (float(energy), str(bitstring))
            if best is None or candidate < best:
                best = candidate
        if best is not None:
            qaoa_energy, qaoa_bits = best
            qaoa_source = "qaoa_results.json:seeds"
    if qaoa_bits is None:
        pool = qaoa.get("candidate_pool") or ()
        for item in pool:
            if not isinstance(item, Mapping):
                continue
            sources = item.get("sources") or ()
            if not any(str(source).startswith("qaoa") for source in sources):
                continue
            bitstring = item.get("bitstring")
            energy = item.get("energy", item.get("qubo_energy"))
            if bitstring is None:
                continue
            energy_f = float(energy) if energy is not None else float("inf")
            current = float("inf") if qaoa_energy is None else float(qaoa_energy)
            if qaoa_bits is None or energy_f < current:
                qaoa_bits = str(bitstring)
                qaoa_energy = None if energy is None else float(energy)
                qaoa_source = "qaoa_results.json:candidate_pool"
    reason = None
    if qaoa_bits is None:
        reason = str(
            qaoa.get("fallback_reason")
            or bench.get("fallback_reason")
            or "QAOA bitstring unavailable in artifacts"
        )
    solvers["qaoa"] = {
        "available": bool(qaoa_bits),
        "bitstring": qaoa_bits,
        "qubo_energy": qaoa_energy,
        "source": qaoa_source,
        "unavailable_reason": reason,
    }
    return solvers


def score_solver_bitstring(
    bitstring: str,
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    candidate_order: Sequence[str],
    config: Mapping[str, Any],
    *,
    qubo_energy: float | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Score one solver bitstring with the canonical true financial objective."""
    reductions = reductions_from_bitstring(
        bitstring,
        universe_tickers=ticker_order,
        candidate_order=candidate_order,
    )
    result = financial_objective(
        reductions, scenarios, ticker_order, weights, cash_weight, config
    )
    primary_key = alpha_key(required_float(config, "cvar_alpha"))
    materiality_cfg = config.get("materiality") or {}
    threshold = float(materiality_cfg.get("true_cvar_relative_reduction_min", 0.01))
    scored = _score_objective(
        result, primary_key=primary_key, materiality_threshold=threshold
    )
    decoded = decode_four_level_bits(
        np.asarray([int(char) for char in str(bitstring)], dtype=int),
        candidate_count=len(candidate_order),
    )
    return {
        "available": True,
        "bitstring": str(bitstring),
        "qubo_energy": None if qubo_energy is None else float(qubo_energy),
        "source": source,
        "decoded_actions": {
            ticker: float(value)
            for ticker, value in zip(candidate_order, decoded, strict=True)
        },
        **scored,
    }


def build_true_benchmark(
    *,
    identity: Mapping[str, str],
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
    candidate_order_payload: Mapping[str, Any],
    qubo_model: Mapping[str, Any],
    exact_payload: Mapping[str, Any] | None,
    qaoa_payload: Mapping[str, Any] | None,
    workflow_benchmark: Mapping[str, Any] | None,
    final_recommendation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the GATE-08 G8 true-financial benchmark payload for three solvers."""
    order_payload = _read_json_mapping(candidate_order_payload, "candidate_order")
    model = _read_json_mapping(qubo_model, "qubo_model")
    bench = _read_json_mapping(workflow_benchmark, "workflow_benchmark")
    qaoa = _read_json_mapping(qaoa_payload, "qaoa_results")
    final = _read_json_mapping(final_recommendation, "final_recommendation")

    candidates_raw = order_payload.get("candidates") or model.get("candidate_order")
    if not candidates_raw:
        raise ValueError(
            "[risk.true_benchmark] candidate_order.json "
            "(or qubo_model.candidate_order) required."
        )
    if isinstance(candidates_raw[0], Mapping):
        candidate_order = [str(item["ticker"]) for item in candidates_raw]
    else:
        candidate_order = [str(ticker) for ticker in candidates_raw]

    qubo_hash = str(model.get("qubo_hash") or bench.get("qubo_hash") or "")
    if not qubo_hash:
        raise ValueError("[risk.true_benchmark] qubo_hash is required.")
    hashes = {
        str(payload.get("qubo_hash"))
        for payload in (exact_payload, qaoa, bench, final)
        if isinstance(payload, Mapping) and payload.get("qubo_hash")
    }
    if hashes and hashes != {qubo_hash}:
        raise ValueError(
            f"[risk.true_benchmark] qubo_hash mismatch across artifacts: {sorted(hashes)}."
        )

    primary_key = alpha_key(required_float(config, "cvar_alpha"))
    materiality_cfg = config.get("materiality") or {}
    threshold = float(materiality_cfg.get("true_cvar_relative_reduction_min", 0.01))
    baseline = financial_objective(
        np.zeros(len(ticker_order)),
        scenarios,
        ticker_order,
        weights,
        cash_weight,
        config,
    )

    extracted = extract_solver_bitstrings(
        exact_payload=exact_payload,
        qaoa_payload=qaoa,
        workflow_benchmark=bench,
    )
    solvers: dict[str, Any] = {}
    for name in _SOLVER_ORDER:
        meta = extracted[name]
        if not meta.get("available") or not meta.get("bitstring"):
            solvers[name] = {
                "available": False,
                "bitstring": None,
                "qubo_energy": meta.get("qubo_energy"),
                "source": meta.get("source"),
                "unavailable_reason": meta.get("unavailable_reason")
                or f"{name} bitstring missing",
            }
            continue
        solvers[name] = score_solver_bitstring(
            str(meta["bitstring"]),
            scenarios,
            ticker_order,
            weights,
            cash_weight,
            candidate_order,
            config,
            qubo_energy=meta.get("qubo_energy"),
            source=str(meta.get("source")),
        )

    available = [
        (name, solvers[name])
        for name in _SOLVER_ORDER
        if solvers[name].get("available")
    ]
    by_true = sorted(
        available,
        key=lambda item: (
            float(item[1]["true_cvar"]),
            float(item[1]["true_objective"]),
            item[0],
        ),
    )
    by_qubo = sorted(
        [
            (name, entry)
            for name, entry in available
            if entry.get("qubo_energy") is not None
        ],
        key=lambda item: (float(item[1]["qubo_energy"]), item[0]),
    )
    true_rank = {name: rank for rank, (name, _) in enumerate(by_true, start=1)}
    qubo_rank = {name: rank for rank, (name, _) in enumerate(by_qubo, start=1)}
    ranking_disagreement = [
        {
            "solver": name,
            "true_rank": true_rank[name],
            "qubo_rank": qubo_rank.get(name),
            "ranking_disagreement": (
                None
                if name not in qubo_rank
                else int(qubo_rank[name]) - int(true_rank[name])
            ),
            "true_cvar": float(solvers[name]["true_cvar"]),
            "qubo_energy": solvers[name].get("qubo_energy"),
        }
        for name, _ in available
    ]

    notes: list[str] = []
    if (
        solvers["qaoa"].get("available")
        and solvers["exact"].get("available")
        and float(solvers["qaoa"]["true_cvar"]) > float(solvers["exact"]["true_cvar"])
    ):
        notes.append("QAOA loses to exact on true CVaR (no quantum advantage claim).")
    if (
        solvers["qaoa"].get("available")
        and solvers["classical"].get("available")
        and float(solvers["qaoa"]["true_cvar"])
        > float(solvers["classical"]["true_cvar"])
    ):
        notes.append("QAOA loses to classical on true CVaR.")
    if not solvers["qaoa"].get("available"):
        notes.append(
            "QAOA true-objective row unavailable — report uses exact/classical only."
        )

    requested = str(
        qaoa.get("requested_solver")
        or bench.get("requested_solver")
        or final.get("requested_solver")
        or "qaoa"
    )
    actual = str(
        qaoa.get("actual_solver")
        or bench.get("actual_solver")
        or final.get("actual_solver")
        or requested
    )
    fallback = (
        qaoa.get("fallback_reason")
        or bench.get("fallback_reason")
        or final.get("fallback_reason")
    )

    payload: dict[str, Any] = {
        **dict(identity),
        "qubo_hash": qubo_hash,
        "candidate_order_hash": str(
            order_payload.get("candidate_order_hash")
            or model.get("candidate_order_hash")
            or ""
        ),
        "candidate_count": len(candidate_order),
        "candidate_order": list(candidate_order),
        "requested_solver": requested,
        "actual_solver": actual,
        "fallback_reason": fallback,
        "materiality_threshold": threshold,
        "baseline": {
            "true_cvar": float(baseline.before.cvar[primary_key]),
            "cvar": _metrics_snapshot(baseline.before.cvar),
            "expected_horizon_return": float(baseline.before.expected_horizon_return),
            "worst_scenario_max_drawdown": float(
                baseline.before.worst_scenario_max_drawdown
            ),
        },
        "solvers": solvers,
        "financial_ranking": [name for name, _ in by_true],
        "ranking_disagreement": ranking_disagreement,
        "notes": notes,
        "warnings": [
            "NON_BASELINE_RUN: true-benchmark is development evidence only.",
            "No quantum advantage claim; report financial ranking honestly.",
        ],
        "caveat": str(bench.get("caveat") or "Simulator / NON_BASELINE evidence only."),
    }
    if final:
        payload["final_recommendation"] = {
            "present": True,
            "winning_bitstring": final.get("winning_bitstring"),
            "true_cvar_before": final.get("true_cvar_before"),
            "true_cvar_after": final.get("true_cvar_after"),
            "true_cvar_relative_reduction": final.get("true_cvar_relative_reduction"),
            "materiality_met": final.get("materiality_met"),
            "actual_solver": final.get("actual_solver"),
        }
    else:
        payload["final_recommendation"] = {"present": False}
    return payload
