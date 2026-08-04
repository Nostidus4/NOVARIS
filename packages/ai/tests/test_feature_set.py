# Nguyễn Anh Tú - test 5 feature HMM: tương quan tính tay, không nhìn tương lai, scaler fit train.
import numpy as np
import pandas as pd
import pytest
from qshield_ai.fixtures import synthetic_dataset
from qshield_ai.regime.feature_set import (
    CORR_FEATURE,
    apply_transforms,
    build_feature_frame,
    fit_scaler,
    mean_pairwise_corr,
    to_matrix,
)

TICKERS = ["AAA", "BBB", "CCC", "DDD"]
MARKET_COLS = ["market_log_return", "realized_vol_20d", "drawdown", "liquidity_20d"]


def _returns_from_matrix(values: dict[str, list[float]]) -> pd.DataFrame:
    """Dựng khung returns tối thiểu (date, ticker, log_return) — đủ cho mean_pairwise_corr."""
    dates = pd.bdate_range("2024-01-01", periods=len(next(iter(values.values()))))
    frames = [
        pd.DataFrame({"date": dates, "ticker": ticker, "log_return": series})
        for ticker, series in values.items()
    ]
    return pd.concat(frames, ignore_index=True)


def test_mean_pairwise_corr_matches_hand_calculation() -> None:
    """A và B tương quan hoàn hảo (+1); C ngược pha hoàn hảo với cả hai (-1).

    Ba cặp: AB = +1, AC = -1, BC = -1 ⇒ trung bình = (1 - 1 - 1) / 3 = -1/3.
    """
    returns = _returns_from_matrix(
        {
            "AAA": [1.0, 2.0, 3.0, 4.0],
            "BBB": [2.0, 4.0, 6.0, 8.0],
            "CCC": [3.0, 2.0, 1.0, 0.0],
        }
    )
    corr = mean_pairwise_corr(returns, tickers=["AAA", "BBB", "CCC"], window=3)

    assert corr.iloc[:2].isna().all(), "min_periods=3 ⇒ hai ngày đầu chưa đủ cửa sổ"
    assert corr.iloc[2] == pytest.approx(-1.0 / 3.0)
    assert corr.iloc[3] == pytest.approx(-1.0 / 3.0)


def test_mean_pairwise_corr_is_not_look_ahead() -> None:
    """Giá trị tại ngày t không đổi khi thêm dữ liệu SAU t — quy tắc 4."""
    returns, _ = synthetic_dataset(tickers=TICKERS, n_days=300, seed=3)
    full = mean_pairwise_corr(returns, tickers=TICKERS, window=60)

    cutoff = full.index[200]
    truncated_returns = returns.loc[returns["date"] <= cutoff]
    truncated = mean_pairwise_corr(truncated_returns, tickers=TICKERS, window=60)

    pd.testing.assert_series_equal(full.loc[:cutoff], truncated)


def test_mean_pairwise_corr_uses_complete_panel_only() -> None:
    """AD-16: ngày thiếu mã bị loại KHỎI panel thay vì làm NaN lan 60 ngày sau đó."""
    returns, _ = synthetic_dataset(
        tickers=TICKERS, n_days=300, seed=3, missing_positions=(100,)
    )
    corr = mean_pairwise_corr(returns, tickers=TICKERS, window=60)
    assert corr.notna().sum() > 200, (
        "NaN lan ra là dấu hiệu tính trên panel không đầy đủ"
    )


def test_mean_pairwise_corr_rejects_unknown_ticker() -> None:
    returns, _ = synthetic_dataset(tickers=TICKERS, n_days=100, seed=3)
    with pytest.raises(ValueError, match="thiếu ticker"):
        mean_pairwise_corr(returns, tickers=[*TICKERS, "ZZZ"], window=20)


def test_build_feature_frame_shape_and_completeness() -> None:
    returns, market = synthetic_dataset(tickers=TICKERS, n_days=600, seed=5)
    frame = build_feature_frame(
        market, returns, tickers=TICKERS, market_columns=MARKET_COLS, corr_window=60
    )

    assert list(frame.columns) == ["date", "split", *MARKET_COLS, CORR_FEATURE]
    assert not frame.isna().to_numpy().any(), (
        "dòng warm-up phải bị loại HẲN, không để null"
    )
    assert frame["date"].is_monotonic_increasing
    assert frame["date"].is_unique
    assert set(frame["split"]) <= {"train", "validation", "test"}


def test_build_feature_frame_drops_out_of_scope() -> None:
    returns, market = synthetic_dataset(tickers=TICKERS, n_days=400, seed=5)
    market.loc[market.index[:50], "split"] = "out_of_scope"
    frame = build_feature_frame(
        market, returns, tickers=TICKERS, market_columns=MARKET_COLS, corr_window=60
    )
    assert "out_of_scope" not in set(frame["split"])


def test_transforms_match_hand_calculation() -> None:
    frame = pd.DataFrame(
        {"realized_vol_20d": [1.0, np.e], "mean_pairwise_corr_60d": [0.0, 0.5]}
    )
    out = apply_transforms(
        frame, {"realized_vol_20d": "log", "mean_pairwise_corr_60d": "fisher_z"}
    )

    assert out["realized_vol_20d"].tolist() == pytest.approx([0.0, 1.0])
    # arctanh(0.5) = 0.5 * ln((1+0.5)/(1-0.5)) = 0.5 * ln(3)
    assert out["mean_pairwise_corr_60d"].tolist() == pytest.approx(
        [0.0, 0.5 * np.log(3.0)]
    )


def test_log_transform_rejects_non_positive() -> None:
    frame = pd.DataFrame({"realized_vol_20d": [1.0, 0.0]})
    with pytest.raises(ValueError, match="<= 0"):
        apply_transforms(frame, {"realized_vol_20d": "log"})


def test_fisher_z_rejects_saturated_correlation() -> None:
    frame = pd.DataFrame({"mean_pairwise_corr_60d": [0.5, 1.0]})
    with pytest.raises(ValueError, match="Fisher-z"):
        apply_transforms(frame, {"mean_pairwise_corr_60d": "fisher_z"})


def test_unknown_transform_is_rejected() -> None:
    frame = pd.DataFrame({"realized_vol_20d": [1.0]})
    with pytest.raises(ValueError, match="chưa được hỗ trợ"):
        apply_transforms(frame, {"realized_vol_20d": "boxcox"})


def test_scaler_is_fit_on_train_only() -> None:
    """Quy tắc 4: tham số scaler phải bằng thống kê của riêng train, không phải toàn bộ."""
    frame = pd.DataFrame(
        {
            "split": ["train", "train", "validation", "test"],
            "feature_a": [1.0, 3.0, 100.0, 200.0],
        }
    )
    scaler = fit_scaler(frame, ["feature_a"])

    assert scaler.mean_[0] == pytest.approx(2.0)  # (1 + 3) / 2, không dính 100/200
    matrix = to_matrix(frame, ["feature_a"], scaler)
    assert matrix.shape == (4, 1)
    assert matrix[0, 0] == pytest.approx(-1.0)  # (1 - 2) / 1
    assert matrix[1, 0] == pytest.approx(1.0)


def test_fit_scaler_without_train_rows_raises() -> None:
    frame = pd.DataFrame({"split": ["test"], "feature_a": [1.0]})
    with pytest.raises(ValueError, match="train"):
        fit_scaler(frame, ["feature_a"])
