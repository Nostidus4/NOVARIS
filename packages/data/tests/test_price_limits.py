# Nguyễn Anh Tú - test resolve sàn theo ngày và phát hiện vượt biên độ (DQ-007).
import pandas as pd
import pytest
from qshield_data.quality.price_limits import resolve_exchange_column

_ACB_PERIODS = [
    {"exchange": "HNX", "until": "2020-11-30"},
    {"exchange": "HOSE", "from": "2020-12-01"},
]


def _universe(**overrides) -> pd.DataFrame:
    base = {
        "ticker": ["ACB", "VCB"],
        "exchange_periods": [_ACB_PERIODS, [{"exchange": "HOSE"}]],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def _returns(dates: list[str], tickers: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.to_datetime(dates), "ticker": tickers})


def test_open_ended_period_resolves_any_date() -> None:
    out = resolve_exchange_column(
        _returns(["1999-01-04", "2030-01-04"], ["VCB", "VCB"]), _universe()
    )
    assert list(out) == ["HOSE", "HOSE"]


def test_acb_resolves_on_both_sides_of_transfer() -> None:
    out = resolve_exchange_column(
        _returns(["2020-11-30", "2020-12-01"], ["ACB", "ACB"]), _universe()
    )
    assert list(out) == ["HNX", "HOSE"]


def test_unknown_ticker_raises_naming_it() -> None:
    with pytest.raises(ValueError, match="XYZ"):
        resolve_exchange_column(_returns(["2022-01-04"], ["XYZ"]), _universe())


def test_gap_in_periods_raises_naming_ticker_and_date() -> None:
    gapped = _universe(
        exchange_periods=[
            [
                {"exchange": "HNX", "until": "2020-11-30"},
                {"exchange": "HOSE", "from": "2021-01-01"},
            ],
            [{"exchange": "HOSE"}],
        ]
    )
    with pytest.raises(ValueError, match="ACB.*2020-12-15"):
        resolve_exchange_column(_returns(["2020-12-15"], ["ACB"]), gapped)


def test_overlapping_periods_raise() -> None:
    overlapped = _universe(
        exchange_periods=[
            [
                {"exchange": "HNX", "until": "2020-12-31"},
                {"exchange": "HOSE", "from": "2020-12-01"},
            ],
            [{"exchange": "HOSE"}],
        ]
    )
    with pytest.raises(ValueError, match="chồng lấn"):
        resolve_exchange_column(_returns(["2020-12-15"], ["ACB"]), overlapped)


def test_empty_periods_raise() -> None:
    empty = _universe(exchange_periods=[[], [{"exchange": "HOSE"}]])
    with pytest.raises(ValueError, match="ACB"):
        resolve_exchange_column(_returns(["2022-01-04"], ["ACB"]), empty)
