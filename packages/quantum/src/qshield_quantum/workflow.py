"""Pure orchestration helpers for the workflow four-level Quantum branch.

Disk access remains in ``cli.py``.  This module consumes the risk handoff as
plain pandas/dict objects and intentionally avoids not-yet-created contract
types while validating the boundary explicitly.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from qshield_quantum.benchmark import build_generic_benchmark
from qshield_quantum.formulation.four_level import (
    decode_action_levels,
    four_level_variable_names,
)
from qshield_quantum.formulation.qiskit_program import build_quadratic_program
from qshield_quantum.formulation.surrogate import (
    QuadraticSurrogate,
    fit_quadratic_surrogate,
    structured_samples_to_arrays,
)
from qshield_quantum.solvers.exact import GenericExactResult, solve_quadratic_exact
from qshield_quantum.solvers.qaoa import QaoaSeedResult, solve_qaoa
from qshield_quantum.verify.consistency import verify_quadratic_consistency

FOUR_LEVEL_MODE = "top10_four_level_actions"


@dataclass(frozen=True)
class WorkflowQuantumResult:
    model: QuadraticSurrogate
    exact: GenericExactResult
    qaoa_by_seed: dict[int, QaoaSeedResult]
    benchmark: dict[str, Any]
    candidate_pool: tuple[dict[str, Any], ...]
    candidate_order: tuple[str, ...]
    target_column: str


def validate_four_level_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    quantum = dict(profile.get("quantum", {}) or {})
    if quantum.get("mode") != FOUR_LEVEL_MODE:
        raise ValueError(
            f"Profile quantum.mode={quantum.get('mode')!r}; expected {FOUR_LEVEL_MODE!r}."
        )
    levels = list(quantum.get("action_levels_pct", []))
    if levels != [0, 10, 20, 30]:
        raise ValueError(
            f"Four-level profile action_levels_pct must be [0, 10, 20, 30], got {levels}."
        )
    bits_per_asset = int(
        (quantum.get("bit_encoding", {}) or {}).get("bits_per_asset", 0)
    )
    if bits_per_asset != 2:
        raise ValueError(
            f"Four-level profile requires bits_per_asset=2, got {bits_per_asset}."
        )
    encoding = dict(quantum.get("bit_encoding", {}) or {})
    expected_bits = 2 * int(quantum.get("input_candidates", 0))
    if int(encoding.get("total_decision_bits", expected_bits)) != expected_bits:
        raise ValueError(
            "Four-level profile total_decision_bits does not equal "
            f"2 * input_candidates ({expected_bits})."
        )
    expected_mapping = {"00": 0, "10": 10, "01": 20, "11": 30}
    if dict(encoding.get("mapping", expected_mapping)) != expected_mapping:
        raise ValueError(f"Four-level profile bit mapping must be {expected_mapping}.")
    return quantum


def candidate_order_from_handoff(
    candidates: pd.DataFrame, *, expected_candidates: int
) -> list[str]:
    required = {"ticker", "rank"}
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(
            f"candidate_top10 handoff is missing columns: {sorted(missing)}."
        )
    selected = candidates
    if "selected_top10" in candidates.columns:
        values = candidates["selected_top10"]
        selected = candidates[
            values.astype(str).str.lower().isin({"true", "1", "yes"}) | (values == True)
        ]
    selected = selected.sort_values("rank")
    tickers = selected["ticker"].astype(str).tolist()
    if len(tickers) != expected_candidates:
        raise ValueError(
            f"Expected {expected_candidates} selected candidates, got {len(tickers)}."
        )
    if len(set(tickers)) != len(tickers):
        raise ValueError("candidate_top10 contains duplicate selected tickers.")
    return tickers


def make_four_level_feasibility(
    constraints: Mapping[str, Any] | None = None,
) -> Callable[[np.ndarray], bool]:
    """Build a generic predicate from optional, explicit handoff bounds.

    Unknown keys are ignored because risk_summary is not yet a locked contract.
    Supported bounds are active-candidate count and total percentage points.
    """
    values = dict(constraints or {})
    min_active = int(values.get("min_active_candidates", 0))
    max_active_raw = values.get("max_active_candidates")
    max_active = None if max_active_raw is None else int(max_active_raw)
    min_total = float(values.get("min_total_action_pct", 0.0))
    max_total_raw = values.get("max_total_action_pct")
    max_total = None if max_total_raw is None else float(max_total_raw)

    def predicate(bits: np.ndarray) -> bool:
        try:
            levels = decode_action_levels(bits)
        except ValueError:
            return False
        active = int(np.count_nonzero(levels))
        total = float(levels.sum())
        return (
            active >= min_active
            and (max_active is None or active <= max_active)
            and total >= min_total
            and (max_total is None or total <= max_total)
        )

    return predicate


def run_four_level_workflow(
    candidates: pd.DataFrame,
    objective_samples: pd.DataFrame,
    *,
    profile: Mapping[str, Any],
    risk_summary: Mapping[str, Any] | None,
    seeds: list[int],
    shots: int,
    maxiter: int,
    chunk_size: int = 65_536,
    candidate_pool_size: int = 20,
    verify: bool = True,
    warm_start: bool = True,
) -> WorkflowQuantumResult:
    """Fit, verify, exhaust, run QAOA, and benchmark a four-level handoff."""
    quantum = validate_four_level_profile(profile)
    expected = int(quantum["input_candidates"])
    order = candidate_order_from_handoff(candidates, expected_candidates=expected)
    Z, targets, target_column = structured_samples_to_arrays(objective_samples, order)
    model = fit_quadratic_surrogate(Z, targets)
    names = four_level_variable_names(order)
    if verify:
        verify_quadratic_consistency(model, variable_names=names, chunk_size=chunk_size)

    constraints = (risk_summary or {}).get("quantum_constraints", {})
    feasibility = make_four_level_feasibility(constraints)
    exact = solve_quadratic_exact(
        model,
        feasibility=feasibility,
        chunk_size=chunk_size,
        top_n=candidate_pool_size,
    )
    qp = build_quadratic_program(
        model.Q, model.linear, model.constant, ticker_order=names
    )
    qaoa = solve_qaoa(
        qp,
        seeds=seeds,
        shots=shots,
        maxiter=maxiter,
        feasibility=feasibility,
        reference_bitstring=exact.best_feasible_bitstring,
        reps=int((quantum.get("qaoa", {}) or {}).get("p", 1)),
        warm_start=warm_start,
        candidate_pool_size=candidate_pool_size,
    )
    benchmark = build_generic_benchmark(
        exact,
        qaoa,
        model=model,
        feasibility=feasibility,
        classical_seed=seeds[0],
    )
    pool = _merge_candidate_pool(exact, qaoa, order, candidate_pool_size)
    return WorkflowQuantumResult(
        model=model,
        exact=exact,
        qaoa_by_seed=qaoa,
        benchmark=benchmark,
        candidate_pool=pool,
        candidate_order=tuple(order),
        target_column=target_column,
    )


def _merge_candidate_pool(
    exact: GenericExactResult,
    qaoa: dict[int, QaoaSeedResult],
    candidate_order: list[str],
    limit: int,
) -> tuple[dict[str, Any], ...]:
    entries: dict[str, dict[str, Any]] = {}
    for candidate in exact.top_feasible_candidates:
        entries[candidate.bitstring] = {
            "bitstring": candidate.bitstring,
            "energy": candidate.energy,
            "sources": ["exact"],
        }
    for seed, result in qaoa.items():
        samples = result.samples or ()
        if not samples and result.feasible:
            samples = ()
            entries.setdefault(
                result.bitstring,
                {"bitstring": result.bitstring, "energy": result.energy, "sources": []},
            )
            entries[result.bitstring]["sources"].append(f"qaoa_seed_{seed}")
        for sample in samples:
            if not sample.feasible:
                continue
            entry = entries.setdefault(
                sample.bitstring,
                {"bitstring": sample.bitstring, "energy": sample.energy, "sources": []},
            )
            entry["energy"] = min(float(entry["energy"]), sample.energy)
            entry["sources"].append(f"qaoa_seed_{seed}")
    ordered = sorted(
        entries.values(), key=lambda item: (item["energy"], item["bitstring"])
    )[:limit]
    for rank, entry in enumerate(ordered, start=1):
        levels = decode_action_levels(entry["bitstring"])
        entry["rank"] = rank
        entry["actions_pct"] = {
            ticker: int(level)
            for ticker, level in zip(candidate_order, levels, strict=True)
        }
        entry["sources"] = sorted(set(entry["sources"]))
    return tuple(ordered)


def exact_result_payload(result: GenericExactResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["top_feasible_candidates"] = [
        asdict(candidate) for candidate in result.top_feasible_candidates
    ]
    return payload


def qaoa_result_payload(
    qaoa: dict[int, QaoaSeedResult], candidate_pool: tuple[dict[str, Any], ...]
) -> dict[str, Any]:
    return {
        "seeds": {
            str(seed): {
                **asdict(result),
                "samples": [asdict(sample) for sample in result.samples],
            }
            for seed, result in qaoa.items()
        },
        "candidate_pool": list(candidate_pool),
    }
