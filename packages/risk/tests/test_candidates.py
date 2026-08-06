import numpy as np
import pandas as pd
import pytest
from qshield_risk.candidates import REQUIRED_COLUMNS, select_candidates
from qshield_risk.costs import CostRates

from .conftest import TICKERS


def _action_effects(gains: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"action_id": i, "ticker": ticker, "g": gains[ticker], "c": 0.001}
            for i, ticker in enumerate(TICKERS)
        ]
    )


def _weights() -> dict[str, float]:
    return {ticker: 0.125 for ticker in TICKERS}


def test_all_selected_when_n_less_than_output_candidates() -> None:
    gains = dict.fromkeys(TICKERS, 0.01)
    frame = select_candidates(
        _action_effects(gains),
        baseline_cvar=0.05,
        weights=_weights(),
        cost_rates=CostRates(0.001, 0.002, 0.0005),
        reduction_pct=0.20,
        output_candidates=10,
    )
    assert len(frame) == len(TICKERS)
    assert frame["selected_top10"].all()
    assert (frame["reason"] == "N=8 <= output_candidates=10, không lọc").all()


def test_ranked_descending_by_net_risk_score() -> None:
    gains = {t: float(i) for i, t in enumerate(TICKERS)}  # FPT (last) has highest g
    frame = select_candidates(
        _action_effects(gains),
        baseline_cvar=0.05,
        weights=_weights(),
        cost_rates=CostRates(0.0, 0.0, 0.0),
        reduction_pct=0.20,
        output_candidates=10,
    )
    assert frame.iloc[0]["ticker"] == "FPT"
    assert frame.iloc[0]["rank"] == 1
    assert list(frame["rank"]) == list(range(1, len(TICKERS) + 1))


def test_only_top_n_selected_when_n_greater_than_output_candidates() -> None:
    gains = {t: float(i) for i, t in enumerate(TICKERS)}
    frame = select_candidates(
        _action_effects(gains),
        baseline_cvar=0.05,
        weights=_weights(),
        cost_rates=CostRates(0.0, 0.0, 0.0),
        reduction_pct=0.20,
        output_candidates=3,
    )
    assert frame["selected_top10"].sum() == 3
    assert set(frame.loc[frame["selected_top10"], "ticker"]) == {"FPT", "VNM", "MWG"}
    assert (
        frame.loc[~frame["selected_top10"], "reason"] == "rank > output_candidates"
    ).all()


def test_net_risk_score_is_gain_minus_cost() -> None:
    action_effects = pd.DataFrame(
        [{"action_id": 0, "ticker": "ACB", "g": 0.03, "c": 0.004}]
    )
    frame = select_candidates(
        action_effects,
        baseline_cvar=0.05,
        weights={"ACB": 0.125},
        cost_rates=CostRates(0.001, 0.002, 0.0005),
        reduction_pct=0.20,
        output_candidates=10,
    )
    assert frame.loc[0, "net_risk_score"] == pytest.approx(0.03 - 0.004)


def test_only_matching_reduction_level_column_is_filled() -> None:
    action_effects = pd.DataFrame(
        [{"action_id": 0, "ticker": "ACB", "g": 0.02, "c": 0.001}]
    )
    frame = select_candidates(
        action_effects,
        baseline_cvar=0.05,
        weights={"ACB": 0.125},
        cost_rates=CostRates(0.0, 0.0, 0.0),
        reduction_pct=0.20,
        output_candidates=10,
    )
    assert frame.loc[0, "marginal_CVaR_reduction_20pct"] == pytest.approx(0.02)
    assert np.isnan(frame.loc[0, "marginal_CVaR_reduction_10pct"])
    assert np.isnan(frame.loc[0, "marginal_CVaR_reduction_30pct"])
    assert frame.loc[0, "note"] is None


def test_note_explains_missing_levels_for_10pct_reduction() -> None:
    action_effects = pd.DataFrame(
        [{"action_id": 0, "ticker": "ACB", "g": 0.01, "c": 0.001}]
    )
    frame = select_candidates(
        action_effects,
        baseline_cvar=0.05,
        weights={"ACB": 0.125},
        cost_rates=CostRates(0.0, 0.0, 0.0),
        reduction_pct=0.10,
        output_candidates=10,
    )
    assert frame.loc[0, "marginal_CVaR_reduction_10pct"] == pytest.approx(0.01)
    assert "workflow_update" in frame.loc[0, "note"]


def test_unrecognized_reduction_pct_raises() -> None:
    action_effects = pd.DataFrame(
        [{"action_id": 0, "ticker": "ACB", "g": 0.01, "c": 0.001}]
    )
    with pytest.raises(ValueError, match="không khớp mức nào"):
        select_candidates(
            action_effects,
            baseline_cvar=0.05,
            weights={"ACB": 0.125},
            cost_rates=CostRates(0.0, 0.0, 0.0),
            reduction_pct=0.25,
            output_candidates=10,
        )


def test_missing_action_effects_column_raises() -> None:
    with pytest.raises(ValueError, match="thiếu cột"):
        select_candidates(
            pd.DataFrame([{"ticker": "ACB", "g": 0.01}]),
            baseline_cvar=0.05,
            weights={"ACB": 0.125},
            cost_rates=CostRates(0.0, 0.0, 0.0),
            reduction_pct=0.20,
            output_candidates=10,
        )


def test_ticker_not_in_weights_raises() -> None:
    action_effects = pd.DataFrame(
        [{"action_id": 0, "ticker": "ACB", "g": 0.01, "c": 0.001}]
    )
    with pytest.raises(ValueError, match="không có trong weights"):
        select_candidates(
            action_effects,
            baseline_cvar=0.05,
            weights={},
            cost_rates=CostRates(0.0, 0.0, 0.0),
            reduction_pct=0.20,
            output_candidates=10,
        )


def test_output_columns_match_required_columns() -> None:
    action_effects = pd.DataFrame(
        [{"action_id": 0, "ticker": "ACB", "g": 0.01, "c": 0.001}]
    )
    frame = select_candidates(
        action_effects,
        baseline_cvar=0.05,
        weights={"ACB": 0.125},
        cost_rates=CostRates(0.0, 0.0, 0.0),
        reduction_pct=0.20,
        output_candidates=10,
    )
    assert list(frame.columns) == list(REQUIRED_COLUMNS)
