# Nguyễn Đỗ Minh Anh - test compute_asset_returns: không forward-fill, không leakage giữa ticker.
import numpy as np
import pandas as pd
import pytest
from qshield_data.returns import compute_asset_returns


def _prices(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["ticker", "date", "adjusted_close"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_first_day_per_ticker_is_nan() -> None:
    prices = _prices(
        [
            ("AAA", "2024-01-01", 100.0),
            ("AAA", "2024-01-02", 110.0),
            ("BBB", "2024-01-01", 50.0),
            ("BBB", "2024-01-02", 55.0),
        ]
    )
    out = compute_asset_returns(prices)

    first_days = out[out["date"] == "2024-01-01"]
    assert first_days["simple_return"].isna().all()
    assert first_days["log_return"].isna().all()


def test_simple_and_log_return_values_match_hand_calc() -> None:
    prices = _prices([("AAA", "2024-01-01", 100.0), ("AAA", "2024-01-02", 110.0)])
    out = compute_asset_returns(prices).set_index("date")

    second_day = out.loc[pd.Timestamp("2024-01-02")]
    assert second_day["simple_return"] == pytest.approx(0.10)
    assert second_day["log_return"] == pytest.approx(np.log(1.10))


def test_no_cross_ticker_leakage() -> None:
    """Return của AAA ngày 2 không được tính bằng giá của BBB dù đứng liền kề sau sort."""
    prices = _prices(
        [
            ("AAA", "2024-01-01", 100.0),
            ("BBB", "2024-01-01", 999.0),
            ("AAA", "2024-01-02", 105.0),
        ]
    )
    out = compute_asset_returns(prices)

    aaa_day2 = out[(out["ticker"] == "AAA") & (out["date"] == "2024-01-02")].iloc[0]
    assert aaa_day2["simple_return"] == pytest.approx(0.05)
