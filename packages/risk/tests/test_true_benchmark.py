"""Smoke tests for GATE-08 G8 true-financial benchmark scoring."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from qshield_risk.objective import COMPONENT_NAMES
from qshield_risk.true_benchmark import (
    build_true_benchmark,
    extract_solver_bitstrings,
    score_solver_bitstring,
)


def _config() -> dict[str, Any]:
    return {
        "cvar_alpha": 0.95,
        "robustness_confidence_levels": [0.975, 0.99],
        "horizon_days": 1,
        "weight_sum_tolerance": 1e-10,
        "maximum_reduction": 0.30,
        "target_cash_increment": 0.0,
        "transaction_cost": {"fee": 0.0, "spread": 0.0, "liquidity_penalty": 0.0},
        "materiality": {"true_cvar_relative_reduction_min": 0.01},
        "financial_objective": {
            "components": {
                name: {"weight": 1.0 if name == "cvar" else 0.0, "scale": 1.0}
                for name in COMPONENT_NAMES
            }
        },
    }


def _inputs(n: int = 3) -> tuple[np.ndarray, tuple[str, ...], dict[str, float]]:
    tickers = tuple(f"T{i}" for i in range(n))
    cube = np.zeros((40, 1, n))
    cube[:, 0, :] = -np.linspace(0.03, 0.09, n)
    weights = {ticker: 1.0 / n for ticker in tickers}
    return cube, tickers, weights


def test_extract_solver_bitstrings_prefers_seeds_then_pool() -> None:
    extracted = extract_solver_bitstrings(
        exact_payload={
            "best_feasible_bitstring": "1111",
            "best_feasible_energy": 1.0,
        },
        qaoa_payload={
            "requested_solver": "qaoa",
            "actual_solver": "qaoa",
            "seeds": {
                "1": {"bitstring": "1100", "energy": 2.0, "feasible": True},
                "2": {"bitstring": "0011", "energy": 1.5, "feasible": True},
            },
            "candidate_pool": [
                {
                    "bitstring": "0000",
                    "energy": 0.1,
                    "sources": ["exact"],
                }
            ],
        },
        workflow_benchmark={
            "classical_bitstring": "1010",
            "classical_energy": 1.2,
            "exact_best_bitstring": "1111",
            "exact_best_energy": 1.0,
        },
    )
    assert extracted["exact"]["bitstring"] == "1111"
    assert extracted["classical"]["bitstring"] == "1010"
    assert extracted["qaoa"]["bitstring"] == "0011"
    assert extracted["qaoa"]["qubo_energy"] == pytest.approx(1.5)


def test_extract_marks_qaoa_unavailable_without_seed_or_pool() -> None:
    extracted = extract_solver_bitstrings(
        exact_payload={"best_feasible_bitstring": "11", "best_feasible_energy": 0.5},
        qaoa_payload={
            "requested_solver": "qaoa",
            "actual_solver": "exact",
            "fallback_reason": "QAOA skipped",
            "seeds": {},
            "candidate_pool": [
                {"bitstring": "11", "energy": 0.5, "sources": ["exact"]}
            ],
        },
        workflow_benchmark={
            "classical_bitstring": "11",
            "classical_energy": 0.5,
            "fallback_reason": "QAOA skipped",
        },
    )
    assert extracted["qaoa"]["available"] is False
    assert "QAOA skipped" in str(extracted["qaoa"]["unavailable_reason"])


def test_build_true_benchmark_scores_three_solvers() -> None:
    cube, tickers, weights = _inputs()
    candidates = list(tickers[:2])
    # 11 11 → both candidates at 30%
    exact_bits = "1111"
    # 10 00 → first candidate 10%, second 0%
    classical_bits = "1000"
    # 01 01 → both at 20%
    qaoa_bits = "0101"

    payload = build_true_benchmark(
        identity={
            "run_id": "test",
            "profile_id": "workflow_update_downstream",
            "profile_status": "NON_BASELINE_RUN",
            "config_version": "test",
            "config_hash": "abc",
        },
        scenarios=cube,
        ticker_order=tickers,
        weights=weights,
        cash_weight=0.0,
        config=_config(),
        candidate_order_payload={
            "candidate_order_hash": "orderhash",
            "candidates": [
                {"ticker": candidates[0], "rank": 1},
                {"ticker": candidates[1], "rank": 2},
            ],
        },
        qubo_model={"qubo_hash": "qubohash", "candidate_order": candidates},
        exact_payload={
            "qubo_hash": "qubohash",
            "best_feasible_bitstring": exact_bits,
            "best_feasible_energy": 0.5,
        },
        qaoa_payload={
            "qubo_hash": "qubohash",
            "requested_solver": "qaoa",
            "actual_solver": "qaoa",
            "seeds": {"7": {"bitstring": qaoa_bits, "energy": 0.8, "feasible": True}},
            "candidate_pool": [],
        },
        workflow_benchmark={
            "qubo_hash": "qubohash",
            "requested_solver": "qaoa",
            "actual_solver": "qaoa",
            "classical_bitstring": classical_bits,
            "classical_energy": 0.9,
            "exact_best_bitstring": exact_bits,
            "exact_best_energy": 0.5,
        },
        final_recommendation={
            "qubo_hash": "qubohash",
            "winning_bitstring": exact_bits,
            "true_cvar_before": 0.1,
            "true_cvar_after": 0.08,
            "true_cvar_relative_reduction": 0.2,
            "materiality_met": True,
            "actual_solver": "qaoa",
        },
    )

    assert payload["qubo_hash"] == "qubohash"
    assert payload["profile_status"] == "NON_BASELINE_RUN"
    assert payload["requested_solver"] == "qaoa"
    assert payload["actual_solver"] == "qaoa"
    assert payload["materiality_threshold"] == pytest.approx(0.01)
    for name in ("exact", "qaoa", "classical"):
        entry = payload["solvers"][name]
        assert entry["available"] is True
        assert "true_cvar" in entry
        assert "cvar_reduction_pct" in entry
        assert "expected_return_sacrifice" in entry
        assert "transaction_cost" in entry
        assert "materiality_met" in entry
        assert set(entry["cvar_before"]) >= {"0.95"}
    assert payload["financial_ranking"]
    assert payload["final_recommendation"]["present"] is True
    assert len(payload["ranking_disagreement"]) == 3


def test_score_solver_bitstring_rejects_bad_length() -> None:
    cube, tickers, weights = _inputs()
    with pytest.raises(ValueError, match="bitstring"):
        score_solver_bitstring(
            "11",
            cube,
            tickers,
            weights,
            0.0,
            tickers[:2],
            _config(),
        )


def test_qubo_hash_mismatch_fails_fast() -> None:
    cube, tickers, weights = _inputs()
    with pytest.raises(ValueError, match="qubo_hash mismatch"):
        build_true_benchmark(
            identity={
                "run_id": "test",
                "profile_id": "workflow_update_downstream",
                "profile_status": "NON_BASELINE_RUN",
                "config_version": "test",
                "config_hash": "abc",
            },
            scenarios=cube,
            ticker_order=tickers,
            weights=weights,
            cash_weight=0.0,
            config=_config(),
            candidate_order_payload={
                "candidates": [{"ticker": "T0", "rank": 1}, {"ticker": "T1", "rank": 2}]
            },
            qubo_model={"qubo_hash": "aaa", "candidate_order": ["T0", "T1"]},
            exact_payload={
                "qubo_hash": "bbb",
                "best_feasible_bitstring": "1111",
                "best_feasible_energy": 1.0,
            },
            qaoa_payload={"seeds": {}, "candidate_pool": []},
            workflow_benchmark={
                "classical_bitstring": "0000",
                "classical_energy": 2.0,
            },
        )
