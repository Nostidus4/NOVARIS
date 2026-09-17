# Nguyễn Đỗ Minh Anh - nguồn FiinPro: patch raw, lịch giao dịch, cờ OHLC, turnover vendor.
import numpy as np
import pandas as pd
import pytest
from qshield_data.clean.validate_prices import (
    flag_price_quality,
    remove_non_trading_days,
)
from qshield_data.sources.loaders.fiinpro import apply_raw_price_patches


def _full_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["VIB", "VIB"],
            "date": pd.to_datetime(["2018-07-20", "2018-07-23"]),
            "Close": [28000.0, 0.0],
            "Adj Close": [3.14, 3.16],
        }
    )


def test_raw_price_patch_overwrites_only_declared_column() -> None:
    patch = {
        "ticker": "VIB",
        "date": "2018-07-23",
        "Close": 28200.0,
        "reason": "close = 0",
    }
    out, log = apply_raw_price_patches(_full_df(), [patch])
    assert out.loc[1, "Close"] == 28200.0
    assert out.loc[1, "Adj Close"] == 3.16
    assert out.loc[0, "Close"] == 28000.0
    assert log[["column", "old_value", "new_value"]].values.tolist() == [
        ["Close", 0.0, 28200.0]
    ]


def test_raw_price_patch_not_matching_one_row_raises() -> None:
    with pytest.raises(ValueError, match="khớp 0 dòng"):
        apply_raw_price_patches(
            _full_df(), [{"ticker": "VIB", "date": "2018-07-24", "Close": 1.0}]
        )


def _prices(**overrides: list) -> pd.DataFrame:
    base = {
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "ticker": ["AAA", "AAA"],
        "open": [10.0, 10.0],
        "high": [11.0, 11.0],
        "low": [9.0, 9.0],
        "close": [10.0, 10.0],
        "adjusted_close": [5.0, 5.0],
        "volume": [100.0, 100.0],
        "turnover_value": [1234.0, 1234.0],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_invalid_ohlc_flags_open_outside_range_but_not_close() -> None:
    # Dòng 0: open > high ⇒ INVALID_OHLC. Dòng 1: close < low (bình quân gia quyền UPCOM) ⇒ OK.
    out = flag_price_quality(_prices(open=[12.0, 10.0], close=[10.0, 8.5]))
    assert out["quality_flag"].tolist() == ["INVALID_OHLC", "OK"]


def test_turnover_keeps_vendor_value_and_estimates_only_missing() -> None:
    out = flag_price_quality(_prices(turnover_value=[1234.0, np.nan]))
    assert out["turnover_value"].tolist() == [1234.0, 10.0 * 100.0]


def test_remove_non_trading_days_uses_index_calendar() -> None:
    index = pd.DataFrame({"Close": [1.0]}, index=pd.to_datetime(["2024-01-02"]))
    out, n = remove_non_trading_days(_prices(), index)
    assert n == 1
    assert out["date"].tolist() == [pd.Timestamp("2024-01-02")]
