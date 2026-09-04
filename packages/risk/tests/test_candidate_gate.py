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
        ranking_variants={
            "seed_101": base,
            "seed_202": base[:9] + [base[10], base[9], base[11]],
        },
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


def _ladder_frame(n_rows: int = 20):
    """Frame có coverage tăng dần theo rank: N nhỏ không đủ, N lớn thì đủ."""
    import pandas as pd

    rows = []
    for rank in range(1, n_rows + 1):
        benefit = float(n_rows - rank + 1)
        rows.append(
            {
                "rank": rank,
                "ticker": f"T{rank:02d}",
                "eligible_status": True,
                "selected_top10": rank <= 10,
                "baseline_CVaR_contribution": benefit,
                "marginal_CVaR_reduction_10pct": benefit,
                "marginal_CVaR_reduction_20pct": benefit,
                "marginal_CVaR_reduction_30pct": benefit,
                "net_risk_score": benefit,
            }
        )
    return pd.DataFrame(rows)


def _ladder_config(coverage_min: float) -> dict:
    return {
        "candidate_gate": {
            "coverage_at_n_min": coverage_min,
            "median_overlap_at_n_min": 0.70,
            "worst_overlap_at_n_min": 0.50,
            "sensitivity_counts": [12, 15],
        }
    }


def test_dynamic_n_picks_the_smallest_passing_n() -> None:
    """CR-WF2-005: thử N tăng dần, chọn N NHỎ NHẤT đạt gate — không nhảy thẳng lên N lớn nhất."""
    from qshield_risk.cli import _resolve_dynamic_n

    frame = _ladder_frame()
    tickers = frame.sort_values("rank")["ticker"].astype(str).tolist()
    variants = {"seed_1": tickers, "seed_2": tickers}
    # coverage@10 = 155/210 ≈ 0.738; đặt ngưỡng 0.72 để N=10 đã đạt.
    _frame, gate, dynamic = _resolve_dynamic_n(
        frame,
        _ladder_config(0.72),
        output_candidates=10,
        ranking_variants=variants,
        sectors=None,
    )
    assert dynamic["selected_n"] == 10
    assert gate.status == "PASS"
    assert [attempt["n"] for attempt in dynamic["attempts"]] == [10]


def test_dynamic_n_climbs_the_ladder_when_the_smallest_n_fails() -> None:
    from qshield_risk.cli import _resolve_dynamic_n

    frame = _ladder_frame()
    tickers = frame.sort_values("rank")["ticker"].astype(str).tolist()
    variants = {"seed_1": tickers, "seed_2": tickers}
    # Ngưỡng 0.86: coverage@10≈0.738 fail, @12≈0.829 fail, @15≈0.929 pass.
    new_frame, gate, dynamic = _resolve_dynamic_n(
        frame,
        _ladder_config(0.86),
        output_candidates=10,
        ranking_variants=variants,
        sectors=None,
    )
    assert [attempt["n"] for attempt in dynamic["attempts"]] == [10, 12, 15]
    assert dynamic["selected_n"] == 15
    assert gate.status == "PASS"
    assert int(new_frame["selected_top10"].sum()) == 15


def test_dynamic_n_never_lowers_the_threshold_to_force_a_pass() -> None:
    """Hết ladder vẫn fail ⇒ giữ N ban đầu và giữ FAIL. Không nới ngưỡng, không nới N."""
    from qshield_risk.cli import _resolve_dynamic_n

    frame = _ladder_frame()
    tickers = frame.sort_values("rank")["ticker"].astype(str).tolist()
    variants = {"seed_1": tickers}
    _frame, gate, dynamic = _resolve_dynamic_n(
        frame,
        _ladder_config(0.999),
        output_candidates=10,
        ranking_variants=variants,
        sectors=None,
    )
    assert dynamic["selected_n"] == 10
    assert gate.status == "FAIL"
    assert all(attempt["status"] != "PASS" for attempt in dynamic["attempts"])
    assert "note" in dynamic


def test_stability_metrics_are_no_longer_silently_null() -> None:
    """P1-5: trước đây `stability_rankings_path: null` khiến mọi metric overlap đều null và gate
    luôn mang lý do STABILITY_NOT_EVALUATED. Có variants thì chúng phải có giá trị thật."""
    frame = _ladder_frame()
    tickers = frame.sort_values("rank")["ticker"].astype(str).tolist()
    shuffled = tickers[2:4] + tickers[:2] + tickers[4:]

    result = evaluate_candidate_gate(
        frame,
        _ladder_config(0.70),
        output_candidates=10,
        ranking_variants={"seed_1": tickers, "seed_2": shuffled},
    )

    assert result.median_overlap_at_n is not None
    assert result.worst_overlap_at_n is not None
    assert result.median_spearman is not None
    assert "STABILITY_NOT_EVALUATED" not in result.reasons
