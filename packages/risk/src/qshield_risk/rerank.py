"""True-objective reranking and bounded deterministic local polishing."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd  # type: ignore[import-untyped]

from qshield_risk.objective import FinancialObjective, financial_objective
from qshield_risk.policy import RiskPolicy
from qshield_risk.portfolio import validate_ticker_order
from qshield_risk.sampling import decode_four_level_bits


def materiality_from_cvar(
    cvar_before: float,
    cvar_after: float,
    *,
    threshold: float = 0.01,
) -> dict[str, float | bool | str]:
    """TL-018 — relative true-CVaR reduction after hedge (loss convention: lower after is better)."""
    if not np.isfinite(cvar_before) or not np.isfinite(cvar_after):
        raise ValueError("[risk.materiality] CVaR values must be finite.")
    if threshold <= 0.0:
        raise ValueError("[risk.materiality] threshold must be positive.")
    if cvar_before <= 0.0:
        relative = 0.0 if cvar_after >= cvar_before else 1.0
    else:
        relative = float((cvar_before - cvar_after) / cvar_before)
    met = relative >= threshold
    return {
        "materiality_threshold": float(threshold),
        "true_cvar_relative_reduction": relative,
        "materiality_met": met,
        "improvement_claim_allowed": met,
        "recommendation_status": (
            "IMPROVES_CVAR" if met else "NO_MATERIAL_IMPROVEMENT"
        ),
    }


def rerank_candidates(
    candidate_pool: Sequence[Mapping[str, Any]],
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    candidates: Sequence[str],
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Deduplicate feasible solver candidates and rank them by the true financial objective."""
    tickers = validate_ticker_order(ticker_order)
    candidate_order = tuple(str(ticker) for ticker in candidates)
    if not candidate_order or len(set(candidate_order)) != len(candidate_order):
        raise ValueError("[risk.rerank] candidates must be unique and non-empty.")
    missing = sorted(set(candidate_order) - set(tickers))
    if missing:
        raise ValueError(
            f"[risk.rerank] candidates absent from ticker_order: {missing}."
        )
    indices = [tickers.index(ticker) for ticker in candidate_order]

    distinct: dict[str, dict[str, Any]] = {}
    for item in candidate_pool:
        if item.get("feasible", True) is not True:
            continue
        bitstring = str(item.get("bitstring", ""))
        bits = np.asarray([int(char) for char in bitstring], dtype=int)
        decode_four_level_bits(bits, candidate_count=len(candidate_order))
        provenance = {
            key: item.get(key)
            for key in (
                "source_solver",
                "probability",
                "count",
                "qubo_energy",
                "fallback_status",
            )
            if item.get(key) is not None
        }
        if bitstring not in distinct:
            distinct[bitstring] = {
                **dict(item),
                "solver_provenance": [provenance],
            }
            continue
        existing = distinct[bitstring]
        existing["solver_provenance"].append(provenance)
        sources = {
            str(source)
            for source in (existing.get("source_solver"), item.get("source_solver"))
            if source
        }
        existing["source_solver"] = ",".join(sorted(sources))
        energies = [
            float(value)
            for value in (existing.get("qubo_energy"), item.get("qubo_energy"))
            if value is not None
        ]
        if energies:
            existing["qubo_energy"] = min(energies)
    if not distinct:
        raise ValueError(
            "[risk.rerank] candidate pool has no distinct feasible bitstrings."
        )

    rows: list[dict[str, object]] = []
    for bitstring, item in distinct.items():
        bits = np.asarray([int(char) for char in bitstring], dtype=int)
        candidate_reductions = decode_four_level_bits(
            bits, candidate_count=len(candidate_order)
        )
        reductions = np.zeros(len(tickers), dtype=float)
        reductions[indices] = candidate_reductions
        result = financial_objective(
            reductions, scenarios, tickers, weights, cash_weight, config
        )
        row: dict[str, object] = {
            **dict(item),
            "bitstring": bitstring,
            "decoded_actions": {
                ticker: float(value)
                for ticker, value in zip(
                    candidate_order, candidate_reductions, strict=True
                )
            },
            "true_objective": result.value,
            "true_cvar": result.components["cvar"].raw,
            "turnover": result.trade.turnover,
            "transaction_cost": result.trade.costs.total,
            "liquidity_penalty": result.trade.costs.liquidity_penalty,
            "cash_budget_deviation": result.components["cash_budget_deviation"].raw,
            "constraint_violations": result.constraint_violations,
            "constraint_details": tuple(
                violation.to_dict() for violation in result.constraint_details
            ),
            "feasible": not result.constraint_violations,
            "policy_status": result.status,
        }
        rows.append(row)
    frame = pd.DataFrame(rows)
    if "qubo_energy" in frame:
        frame["surrogate_rank"] = frame["qubo_energy"].rank(method="first").astype(int)
    else:
        frame["surrogate_rank"] = pd.NA
    # TL-016 tie-break: true objective, then true CVaR, then cash transaction cost
    frame = frame.sort_values(
        ["feasible", "true_objective", "true_cvar", "transaction_cost", "bitstring"],
        ascending=[False, True, True, True, True],
        kind="stable",
    ).reset_index(drop=True)
    top_n = int((config.get("reranking") or {}).get("top_distinct_feasible", 0) or 0)
    if top_n > 0:
        frame = frame.iloc[:top_n].reset_index(drop=True)
    frame.insert(0, "true_rank", frame.index + 1)
    frame["ranking_disagreement"] = (
        frame["surrogate_rank"] - frame["true_rank"]
        if "qubo_energy" in frame
        else pd.NA
    )
    return frame


@dataclass(frozen=True)
class PolishingResult:
    """Coarse and polished actions with true-objective improvement and final accounting."""

    quantum_reductions: tuple[float, ...]
    polished_reductions: tuple[float, ...]
    quantum_objective: FinancialObjective
    polished_objective: FinancialObjective
    objective_improvement: float
    polishing_dependency: float
    actions: pd.DataFrame


def polish_reductions(
    quantum_reductions: npt.ArrayLike,
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
    *,
    max_adjustment: float,
    maximum_reduction: float,
) -> PolishingResult:
    """Coordinate-polish active actions while locking every Quantum zero at zero."""
    tickers = validate_ticker_order(ticker_order)
    quantum = np.asarray(quantum_reductions, dtype=float)
    # Codec computes 0.10 + 0.20 for level 30%, which can be
    # 0.30000000000000004. Normalize only machine-epsilon boundary noise.
    quantum = np.where(
        np.isclose(quantum, maximum_reduction, rtol=0.0, atol=1e-12),
        maximum_reduction,
        quantum,
    )
    if quantum.shape != (len(tickers),) or not np.isfinite(quantum).all():
        raise ValueError(
            f"[risk.polish] quantum_reductions must have shape ({len(tickers)},)."
        )
    if (
        not np.isfinite(max_adjustment)
        or max_adjustment < 0.0
        or max_adjustment > 0.05
        or not np.isfinite(maximum_reduction)
        or maximum_reduction <= 0.0
        or maximum_reduction > 0.30
        or np.any(quantum < 0.0)
        or np.any(quantum > maximum_reduction + 1e-12)
    ):
        raise ValueError(
            "[risk.polish] max adjustment is 0.05 and final reduction bound is [0, 0.30]."
        )

    quantum_result = financial_objective(
        quantum, scenarios, tickers, weights, cash_weight, config
    )
    current = quantum.copy()
    current_result = quantum_result
    active = np.flatnonzero(quantum > 0.0)
    lower = np.maximum(0.0, quantum - max_adjustment)
    upper = np.minimum(maximum_reduction, quantum + max_adjustment)
    policy = RiskPolicy.from_config(config)
    if policy is not None:
        caps = policy.per_asset_reduction_caps or {}
        upper = np.asarray(
            [
                max(
                    float(lower[index]),
                    min(float(upper[index]), caps.get(ticker, maximum_reduction)),
                )
                for index, ticker in enumerate(tickers)
            ],
            dtype=float,
        )

    def is_better(candidate: FinancialObjective, incumbent: FinancialObjective) -> bool:
        candidate_feasible = not candidate.constraint_violations
        incumbent_feasible = not incumbent.constraint_violations
        if candidate_feasible != incumbent_feasible:
            return candidate_feasible
        return candidate.value < incumbent.value - 1e-15

    while True:
        improved = False
        for index in active:
            choices = sorted(
                {float(lower[index]), float(current[index]), float(upper[index])}
            )
            best_values = current
            best_result = current_result
            for choice in choices:
                trial = current.copy()
                trial[index] = choice
                result = financial_objective(
                    trial, scenarios, tickers, weights, cash_weight, config
                )
                if is_better(result, best_result):
                    best_values = trial
                    best_result = result
            if is_better(best_result, current_result):
                current = best_values
                current_result = best_result
                improved = True
        if not improved:
            break
    if np.any(current[quantum == 0.0] != 0.0):
        raise RuntimeError("[risk.polish] zero-action lock was violated.")
    if np.any(np.abs(current - quantum) > max_adjustment + 1e-12):
        raise RuntimeError("[risk.polish] adjustment bound was violated.")

    zero_result = financial_objective(
        np.zeros(len(tickers)), scenarios, tickers, weights, cash_weight, config
    )
    polish_improvement = quantum_result.value - current_result.value
    total_improvement = zero_result.value - current_result.value
    dependency = (
        polish_improvement / total_improvement if total_improvement > 0.0 else 0.0
    )
    actions = pd.DataFrame(
        {
            "ticker": tickers,
            "current_weight": [float(weights[ticker]) for ticker in tickers],
            "quantum_reduction": quantum,
            "polished_reduction": current,
            "absolute_change": np.abs(current - quantum),
            "sell_value": np.asarray([weights[ticker] for ticker in tickers]) * current,
            "final_weight": current_result.trade.stock_weights,
        }
    )
    return PolishingResult(
        quantum_reductions=tuple(float(value) for value in quantum),
        polished_reductions=tuple(float(value) for value in current),
        quantum_objective=quantum_result,
        polished_objective=current_result,
        objective_improvement=polish_improvement,
        polishing_dependency=float(dependency),
        actions=actions,
    )


def build_financial_baselines(
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Evaluate no-action, pro-rata and deterministic greedy direct-financial baselines."""
    tickers = validate_ticker_order(ticker_order)
    maximum = float(config.get("maximum_reduction", 0.30))
    zero = np.zeros(len(tickers), dtype=float)
    no_action = financial_objective(
        zero, scenarios, tickers, weights, cash_weight, config
    )
    policy = RiskPolicy.from_config(config)

    pro_rata: np.ndarray = zero.copy()
    if policy is not None and cash_weight < policy.cash_min:
        stock_total = sum(float(weights[ticker]) for ticker in tickers)
        required = policy.cash_min - cash_weight
        fraction = min(maximum, required / stock_total) if stock_total > 0.0 else 0.0
        pro_rata[:] = fraction
        caps = policy.per_asset_reduction_caps or {}
        pro_rata = np.asarray(
            [min(value, caps.get(ticker, maximum)) for value, ticker in zip(pro_rata, tickers, strict=True)],
            dtype=float,
        )
    pro_rata_result = financial_objective(
        pro_rata, scenarios, tickers, weights, cash_weight, config
    )

    greedy = zero.copy()
    baseline_cvar = no_action.components["cvar"].raw
    gains: list[tuple[float, str, int]] = []
    for index, ticker in enumerate(tickers):
        trial = zero.copy()
        trial[index] = min(0.10, maximum)
        evaluated = financial_objective(
            trial, scenarios, tickers, weights, cash_weight, config
        )
        gains.append((baseline_cvar - evaluated.components["cvar"].raw, ticker, index))
    gains.sort(key=lambda item: (-item[0], item[1]))
    greedy_result = no_action
    caps = (policy.per_asset_reduction_caps or {}) if policy is not None else {}
    for _, ticker, index in gains:
        cap = min(maximum, (caps or {}).get(ticker, maximum))
        while greedy[index] + 0.10 <= cap + 1e-12:
            trial = greedy.copy()
            trial[index] = min(cap, greedy[index] + 0.10)
            evaluated = financial_objective(
                trial, scenarios, tickers, weights, cash_weight, config
            )
            if evaluated.value > greedy_result.value + 1e-15 and not greedy_result.constraint_violations:
                break
            greedy = trial
            greedy_result = evaluated
            if not evaluated.constraint_violations:
                break
        if not greedy_result.constraint_violations:
            break

    rows = []
    for name, reductions, result in (
        ("no_action", zero, no_action),
        ("pro_rata", pro_rata, pro_rata_result),
        ("greedy", greedy, greedy_result),
    ):
        rows.append(
            {
                "baseline": name,
                "reductions": tuple(float(value) for value in reductions),
                "true_objective": result.value,
                "true_cvar": result.components["cvar"].raw,
                "turnover": result.trade.turnover,
                "transaction_cost": result.trade.costs.total,
                "feasible": not result.constraint_violations,
                "constraint_violations": result.constraint_violations,
                "status": result.status,
            }
        )
    return pd.DataFrame(rows)
