from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from qshield_risk.candidates import candidate_order, select_four_level_candidates
from qshield_risk.objective import COMPONENT_NAMES, financial_objective
from qshield_risk.rerank import polish_reductions, rerank_candidates
from qshield_risk.sampling import sample_objective, structured_bit_vectors


def _config() -> dict[str, Any]:
    return {
        "cvar_alpha": 0.95,
        "robustness_confidence_levels": [],
        "horizon_days": 1,
        "weight_sum_tolerance": 1e-10,
        "maximum_reduction": 0.30,
        "target_cash_increment": 0.0,
        "transaction_cost": {"fee": 0.0, "spread": 0.0, "liquidity_penalty": 0.0},
        "financial_objective": {
            "components": {
                name: {"weight": 1.0 if name == "cvar" else 0.0, "scale": 1.0}
                for name in COMPONENT_NAMES
            }
        },
        "candidate_selection": {
            "score_weights": {
                "marginal_10": 1.0,
                "marginal_20": 1.0,
                "marginal_30": 1.0,
                "baseline_contribution": 1.0,
                "transaction_cost": 1.0,
                "liquidity_penalty": 1.0,
            }
        },
    }


def _inputs(n: int = 3) -> tuple[np.ndarray, tuple[str, ...], dict[str, float]]:
    tickers = tuple(f"T{i}" for i in range(n))
    cube = np.zeros((40, 1, n))
    cube[:, 0, :] = -np.linspace(0.03, 0.09, n)
    weights = {ticker: 1.0 / n for ticker in tickers}
    return cube, tickers, weights


def test_objective_is_auditable_and_config_fails_fast() -> None:
    cube, tickers, weights = _inputs()
    result = financial_objective(
        [0.10, 0.20, 0.30], cube, tickers, weights, 0.0, _config()
    )
    assert set(result.components) == set(COMPONENT_NAMES)
    for component in result.components.values():
        assert component.contribution == pytest.approx(
            component.scaled * component.weight
        )
    assert result.trade.stock_weights.sum() + result.trade.cash_weight == pytest.approx(
        1.0
    )

    bad = _config()
    del bad["financial_objective"]
    with pytest.raises(TypeError, match="financial_objective"):
        financial_objective([0.0] * 3, cube, tickers, weights, 0.0, bad)


@pytest.mark.parametrize(("m", "expected"), [(8, 137), (10, 211)])
def test_structured_sample_count(m: int, expected: int) -> None:
    vectors, kinds = structured_bit_vectors(m)
    assert vectors.shape == (expected, 2 * m)
    assert len(kinds) == expected


def test_candidate_selection_true_levels_underfill_and_order() -> None:
    cube, tickers, weights = _inputs()
    frame = select_four_level_candidates(
        cube,
        tickers,
        weights,
        0.0,
        {"T0": True, "T1": False, "T2": True},
        _config(),
        output_candidates=10,
        ineligible_reasons={"T1": "insufficient_history"},
    )
    assert frame["selected_top10"].sum() == 2
    assert frame["underfilled_reason"].notna().all()
    assert frame["marginal_CVaR_reduction_10pct"].notna().all()
    assert frame.loc[frame["ticker"] == "T1", "reason"].item() == "insufficient_history"
    order = candidate_order(frame)
    assert [item["ticker"] for item in order] == ["T2", "T0"]


def test_sampler_rerank_and_polish_use_same_true_objective() -> None:
    cube, tickers, weights = _inputs()
    samples = sample_objective(cube, tickers, weights, 0.0, tickers[:2], _config())
    assert len(samples) == 1 + 4 + 6
    reranked = rerank_candidates(
        [
            {"bitstring": "1000", "qubo_energy": -1.0, "feasible": True},
            {"bitstring": "1101", "qubo_energy": 1.0, "feasible": True},
        ],
        cube,
        tickers,
        weights,
        0.0,
        tickers[:2],
        _config(),
    )
    assert reranked.iloc[0]["bitstring"] == "1101"

    polished = polish_reductions(
        [0.10, 0.0, 0.20],
        cube,
        tickers,
        weights,
        0.0,
        _config(),
        max_adjustment=0.05,
        maximum_reduction=0.30,
    )
    assert polished.polished_reductions == pytest.approx((0.15, 0.0, 0.25))
    assert polished.objective_improvement > 0.0
    assert polished.actions[
        "final_weight"
    ].sum() + polished.polished_objective.trade.cash_weight == (pytest.approx(1.0))
