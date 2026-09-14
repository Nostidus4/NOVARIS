from __future__ import annotations

from itertools import product
from typing import Any

import numpy as np
import pytest
from qshield_risk.hybrid import (
    TrueObjectiveScorer,
    bitstring_from_levels,
    build_objective_context,
    exact_true_grid,
    levels_from_bitstring,
    objective_snapshot,
    polish_top_candidates,
    true_coordinate_search_pool,
)
from qshield_risk.objective import COMPONENT_NAMES, financial_objective
from qshield_risk.rerank import polish_reductions


def _config() -> dict[str, Any]:
    return {
        "cvar_alpha": 0.95,
        "robustness_confidence_levels": [],
        "horizon_days": 1,
        "weight_sum_tolerance": 1e-10,
        "maximum_reduction": 0.30,
        "target_cash_increment": 0.10,
        "transaction_cost": {
            "fee": 0.001,
            "spread": 0.001,
            "liquidity_penalty": 0.0005,
        },
        "financial_objective": {
            "components": {
                name: {
                    "weight": 1.0 if name in ("cvar", "cash_budget_deviation") else 0.2,
                    "scale": 1.0,
                }
                for name in COMPONENT_NAMES
            }
        },
    }


def _inputs() -> tuple[np.ndarray, tuple[str, ...], dict[str, float]]:
    rng = np.random.default_rng(7)
    tickers = ("A", "B", "C")
    cube = rng.normal(-0.01, 0.05, size=(60, 1, 3))
    weights = {"A": 0.4, "B": 0.35, "C": 0.25}
    return cube, tickers, weights


def _context():
    cube, tickers, weights = _inputs()
    return build_objective_context(
        cube, tickers, weights, 0.0, ("C", "A"), _config()
    ), cube


def test_codec_round_trip_matches_workflow_mapping() -> None:
    assert bitstring_from_levels([0, 10, 20, 30]) == "00100111"
    assert levels_from_bitstring("00100111").tolist() == [0, 10, 20, 30]


def test_context_scoring_matches_canonical_objective_by_hand_mapping() -> None:
    context, cube = _context()
    _, tickers, weights = _inputs()
    # "1001" → C=10%, A=20% ; ticker order A,B,C
    expected = financial_objective(
        [0.20, 0.0, 0.10], cube, tickers, weights, 0.0, _config()
    )
    scorer = TrueObjectiveScorer(context)
    value, feasible = scorer.score("1001")
    assert value == pytest.approx(expected.value, abs=1e-14)
    assert feasible is True
    scorer.score("1001")
    assert scorer.evaluations == 1  # memoized state is not charged twice


@pytest.mark.parametrize("workers", [1, 2])
def test_exact_true_grid_matches_bruteforce(workers: int) -> None:
    context, _ = _context()
    grid = exact_true_grid(context, workers=workers, chunk_size=5)
    brute = []
    for index in range(16):
        bits = format(index, "04b")
        brute.append(context.evaluate(context.reductions_from_bitstring(bits)).value)
    np.testing.assert_allclose(grid.values, brute, rtol=0, atol=1e-14)
    assert grid.best_index() == int(np.argmin(brute))
    assert grid.feasible_rank(grid.values[grid.best_index()]) == 1
    scorer = TrueObjectiveScorer(context, grid=grid)
    assert scorer.score("0110")[0] == pytest.approx(brute[0b0110], abs=1e-14)


def test_true_coordinate_search_pool_budget_determinism_and_predicate() -> None:
    context, _ = _context()
    mask = np.ones(16, dtype=bool)
    mask[0b1111] = False  # 30/30 excluded by predicate
    rows_a, stats = true_coordinate_search_pool(
        TrueObjectiveScorer(context), predicate_mask=mask, budget=9, seed=3
    )
    scorer_b = TrueObjectiveScorer(context)
    rows_b, _ = true_coordinate_search_pool(
        scorer_b, predicate_mask=mask, budget=9, seed=3
    )
    assert [r["bitstring"] for r in rows_a] == [r["bitstring"] for r in rows_b]
    assert len(rows_a) == 9 == scorer_b.evaluations
    assert len({r["bitstring"] for r in rows_a}) == 9
    assert all(mask[int(r["bitstring"], 2)] for r in rows_a)
    assert stats["restarts"] >= 1
    rows_all, _ = true_coordinate_search_pool(
        TrueObjectiveScorer(context), predicate_mask=mask, budget=100, seed=3
    )
    assert len(rows_all) == 15  # shortfall: only 15 predicate-feasible states exist


def test_polish_budget_and_growth_path_equivalence() -> None:
    cube, tickers, weights = _inputs()
    context, _ = _context()
    start = np.array([0.20, 0.0, 0.10])
    legacy = polish_reductions(
        start,
        cube,
        tickers,
        weights,
        0.0,
        _config(),
        max_adjustment=0.05,
        maximum_reduction=0.30,
    )
    fast = polish_reductions(
        start,
        None,
        tickers,
        weights,
        0.0,
        _config(),
        max_adjustment=0.05,
        maximum_reduction=0.30,
        growth_paths=context.growth,
    )
    assert legacy.polished_reductions == fast.polished_reductions
    assert legacy.polished_objective.value == pytest.approx(
        fast.polished_objective.value
    )
    assert legacy.stop_reason == "converged" and legacy.evaluations >= 1
    capped = polish_reductions(
        start,
        None,
        tickers,
        weights,
        0.0,
        _config(),
        max_adjustment=0.05,
        maximum_reduction=0.30,
        growth_paths=context.growth,
        max_evaluations=2,
    )
    assert capped.evaluations == 2
    assert capped.stop_reason == "eval_budget"
    assert capped.polished_objective.value <= capped.quantum_objective.value
    with pytest.raises(ValueError, match="max_evaluations"):
        polish_reductions(
            start,
            cube,
            tickers,
            weights,
            0.0,
            _config(),
            max_adjustment=0.05,
            maximum_reduction=0.30,
            max_evaluations=0,
        )


def test_polish_top_candidates_trace_is_attributable() -> None:
    context, _ = _context()
    scorer = TrueObjectiveScorer(context)
    rows = scorer.score_proposals(
        [
            {"bitstring": bits, "source_method": "random_uniform"}
            for bits in ("1001", "1100", "0000", "1111")
        ]
    )
    traces = polish_top_candidates(
        context, rows, top_k=3, max_adjustment=0.05, max_evaluations=50
    )
    assert len(traces) == 3
    assert [t["start_rank"] for t in traces] == [1, 2, 3]
    for trace in traces:
        assert trace["active_set_changed"] is False
        assert trace["zero_action_lock_respected"] and trace["max_adjustment_respected"]
        assert trace["true_objective_evaluations"] <= 50
        assert trace["final_true_objective"] <= trace["start_true_objective"] + 1e-15
        assert trace["objective_improvement"] == pytest.approx(
            trace["start_true_objective"] - trace["final_true_objective"]
        )
    ranked_values = [t["start_true_objective"] for t in traces]
    assert ranked_values == sorted(ranked_values)


def test_polish_rejects_scorer_mismatch() -> None:
    context, _ = _context()
    rows = [{"bitstring": "1001", "true_objective": 123.0, "true_feasible": True}]
    with pytest.raises(ValueError, match="inconsistency"):
        polish_top_candidates(
            context, rows, top_k=1, max_adjustment=0.05, max_evaluations=10
        )


def test_objective_snapshot_weights_sum_to_one() -> None:
    context, _ = _context()
    for levels in product((0, 10, 20, 30), repeat=2):
        result = context.evaluate(
            context.reductions_from_bitstring(bitstring_from_levels(levels))
        )
        snapshot = objective_snapshot(result, context.config)
        assert snapshot["true_objective"] == pytest.approx(result.value)
        assert snapshot["constraint_violation_count"] == 0
