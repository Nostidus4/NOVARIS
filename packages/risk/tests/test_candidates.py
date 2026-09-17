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


def _uniform_cube(n_assets: int, *, seed: int = 0):
    import numpy as np

    rng = np.random.default_rng(seed)
    return rng.normal(-0.001, 0.012, size=(300, 4, n_assets))


def _cand_config() -> dict:
    return {
        "horizon_days": 4,
        "cvar_alpha": 0.95,
        "confidence_levels": [0.95],
        "weight_sum_tolerance": 1e-8,
        "maximum_reduction": 0.30,
        "target_cash_increment": 0.10,
        "transaction_cost": {
            "fee": 0.0015,
            "spread": 0.001,
            "liquidity_penalty": 0.0005,
        },
        "financial_objective": {
            "components": {
                "cvar": {"weight": 1.0, "scale": 0.1},
                "return_sacrifice": {"weight": 0.25, "scale": 0.05},
                "transaction_cost": {"weight": 0.25, "scale": 0.01},
                "turnover": {"weight": 0.05, "scale": 0.2},
                "liquidity_penalty": {"weight": 0.25, "scale": 0.01},
                "cash_budget_deviation": {"weight": 0.35, "scale": 0.1},
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


def test_ineligible_assets_are_never_selected_as_candidates() -> None:
    """Bất biến chưa từng có test: mã KHÔNG đủ điều kiện point-in-time không bao giờ được chọn.

    `docs/decisions/2026-08-31-phan-hoi-bao-cao-15-08.md` C5 và CR-WF2-001: mã thiếu dữ liệu phải giữ residual risk hoặc bị block, KHÔNG
    được âm thầm đem đi giao dịch. Trong repo thật, VPL bị loại vì `INSUFFICIENT_HISTORY`
    (95 phiên) tại ngày đánh giá 2026-07-30 — nhưng nếu ai đó truyền `{t: True for t in tickers}`
    (đúng lỗi một script benchmark từng mắc), VPL sẽ lọt vào ứng viên và **không gì báo lỗi**.

    Test đặt mã không đủ điều kiện ở vị trí RỦI RO NHẤT (trọng số lớn nhất) để nó chắc chắn đứng
    đầu bảng xếp hạng nếu eligibility bị bỏ qua.
    """
    from qshield_risk.candidates import select_four_level_candidates

    tickers = ("AAA", "BBB", "CCC", "DDD")
    # DDD nắm nhiều nhất ⇒ đóng góp rủi ro lớn nhất ⇒ sẽ đứng đầu nếu không bị chặn.
    weights = {"AAA": 0.15, "BBB": 0.20, "CCC": 0.25, "DDD": 0.40}
    cube = _uniform_cube(len(tickers), seed=3)
    config = _cand_config()

    frame = select_four_level_candidates(
        cube,
        tickers,
        weights,
        0.0,
        {"AAA": True, "BBB": True, "CCC": True, "DDD": False},
        config,
        output_candidates=3,
        ineligible_reasons={"DDD": "INSUFFICIENT_HISTORY"},
    )

    selected = set(
        frame.loc[frame["selected_top10"].astype(bool), "ticker"].astype(str)
    )
    assert "DDD" not in selected, "mã không đủ điều kiện đã lọt vào ứng viên"

    row = frame.loc[frame["ticker"] == "DDD"].iloc[0]
    assert not bool(row["selected_top10"])
    assert row["reason"] == "INSUFFICIENT_HISTORY", (
        "phải giữ nguyên lý do loại, không nuốt mất"
    )
    assert "DDD" in set(frame["ticker"].astype(str)), (
        "mã bị loại vẫn phải XUẤT HIỆN trong bảng để mang residual risk (plan C5), "
        "không được biến mất khỏi báo cáo"
    )

    # Đối chứng: nếu eligibility bị bỏ qua thì DDD PHẢI được chọn — chứng minh test có sức phân biệt.
    naive = select_four_level_candidates(
        cube,
        tickers,
        weights,
        0.0,
        dict.fromkeys(tickers, True),
        config,
        output_candidates=3,
    )
    naive_selected = set(
        naive.loc[naive["selected_top10"].astype(bool), "ticker"].astype(str)
    )
    assert "DDD" in naive_selected, (
        "tiền đề của test hỏng: DDD phải được chọn khi bỏ qua eligibility, "
        "nếu không thì assert ở trên không chứng minh điều gì"
    )


def test_zero_weight_assets_are_never_selected_even_when_eligible() -> None:
    """Không nắm giữ thì không có gì để bán — nhưng vẫn phải xuất hiện kèm lý do."""
    from qshield_risk.candidates import select_four_level_candidates

    tickers = ("AAA", "BBB", "CCC")
    weights = {"AAA": 0.5, "BBB": 0.5, "CCC": 0.0}
    frame = select_four_level_candidates(
        _uniform_cube(len(tickers), seed=5),
        tickers,
        weights,
        0.0,
        dict.fromkeys(tickers, True),
        _cand_config(),
        output_candidates=3,
    )
    selected = set(
        frame.loc[frame["selected_top10"].astype(bool), "ticker"].astype(str)
    )
    assert "CCC" not in selected
    assert "CCC" in set(frame["ticker"].astype(str))
