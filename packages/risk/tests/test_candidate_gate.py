from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]
import pytest
from qshield_risk.candidate_gate import evaluate_candidate_gate


def _frame(n: int = 12, selected: int = 10) -> pd.DataFrame:
    values = [float(n - index) for index in range(n)]
    return pd.DataFrame(
        {
            "rank": range(1, n + 1),
            "ticker": [f"T{index}" for index in range(n)],
            "eligible_status": ["eligible"] * n,
            "selected_top10": [index < selected for index in range(n)],
            "baseline_CVaR_contribution": values,
            "marginal_CVaR_reduction_10pct": values,
            "marginal_CVaR_reduction_20pct": values,
            "marginal_CVaR_reduction_30pct": values,
            "net_risk_score": values,
        }
    )


def _config() -> dict[str, object]:
    return {
        "candidate_gate": {
            "coverage_at_n_min": 0.70,
            "median_overlap_at_n_min": 0.70,
            "worst_overlap_at_n_min": 0.50,
            "sensitivity_counts": [12, 15],
        }
    }


def test_gate_passes_with_coverage_and_stable_registered_rankings() -> None:
    frame = _frame()
    base = frame["ticker"].tolist()
    result = evaluate_candidate_gate(
        frame,
        _config(),
        ranking_variants={"seed_101": base, "seed_202": base[:9] + [base[10], base[9], base[11]]},
    )
    assert result.status == "PASS"
    assert result.baseline_handoff_allowed is True
    assert result.coverage_at_n > 0.70
    assert result.median_overlap_at_n == pytest.approx(0.95)


def test_missing_stability_is_not_a_baseline_pass() -> None:
    result = evaluate_candidate_gate(_frame(), _config())
    assert result.status == "NOT_EVALUATED"
    assert result.analysis_handoff_allowed is True
    assert result.baseline_handoff_allowed is False
    assert "STABILITY_NOT_EVALUATED" in result.reasons


def test_underfill_or_low_coverage_fails_but_reports_sensitivity() -> None:
    frame = _frame(n=12, selected=4)
    result = evaluate_candidate_gate(
        frame,
        _config(),
        ranking_variants={"seed": frame["ticker"].tolist()},
    )
    assert result.status == "FAIL"
    assert "UNDERFILLED_CANDIDATES_4_OF_10" in result.reasons
    assert "COVERAGE_BELOW_THRESHOLD" in result.reasons
    assert result.sensitivity_coverage["coverage_at_12"] == pytest.approx(1.0)
