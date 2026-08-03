# Nguyễn Đỗ Minh Anh - test 6 check của Data Quality Gate.
import pandas as pd
from qshield_data.quality.checks import (
    check_no_duplicates,
    check_no_negative_volume,
    check_no_pre_listing,
    check_positive_prices,
    check_split_no_overlap,
    check_universe_count,
    run_all_checks,
)

_UNIVERSE = pd.DataFrame(
    {"ticker": ["AAA", "BBB"], "first_trading_date": ["2020-01-01", "2021-01-01"]}
)


def _prices(**overrides) -> pd.DataFrame:
    base = {
        "date": pd.to_datetime(["2022-01-01", "2022-01-02"]),
        "ticker": ["AAA", "AAA"],
        "adjusted_close": [10.0, 11.0],
        "close": [10.0, 11.0],
        "volume": [100, 200],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_check_no_duplicates_pass_and_fail() -> None:
    assert check_no_duplicates(_prices())["status"] == "PASS"

    dup = _prices(date=pd.to_datetime(["2022-01-01", "2022-01-01"]))
    result = check_no_duplicates(dup)
    assert result["status"] == "FAIL"
    assert result["count"] == 1


def test_check_positive_prices_flags_nonpositive() -> None:
    bad = _prices(adjusted_close=[10.0, -1.0])
    result = check_positive_prices(bad)
    assert result["status"] == "WARN"
    assert result["count"] == 1


def test_check_no_negative_volume() -> None:
    bad = _prices(volume=[100, -5])
    result = check_no_negative_volume(bad)
    assert result["status"] == "FAIL"
    assert result["count"] == 1


def test_check_no_pre_listing_detects_row_before_first_trading_date() -> None:
    bad = _prices(date=pd.to_datetime(["2019-01-01", "2022-01-02"]))
    result = check_no_pre_listing(bad, _UNIVERSE)
    assert result["status"] == "FAIL"
    assert result["count"] == 1


def test_check_universe_count() -> None:
    assert check_universe_count(_UNIVERSE, expected=2)["status"] == "PASS"
    assert check_universe_count(_UNIVERSE, expected=8)["status"] == "FAIL"


def test_check_split_no_overlap() -> None:
    ok = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2023-01-01"]),
            "split": ["train", "validation"],
        }
    )
    assert check_split_no_overlap(ok)["status"] == "PASS"

    overlapping = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-01", "2023-01-01"]),
            "split": ["train", "validation"],
        }
    )
    assert check_split_no_overlap(overlapping)["status"] == "FAIL"


def test_run_all_checks_all_pass() -> None:
    prices = _prices()
    returns = pd.DataFrame({"date": prices["date"], "split": ["train", "train"]})
    report_df, all_pass = run_all_checks(
        prices, _UNIVERSE, returns, expected_universe_count=2
    )

    assert all_pass is True
    assert len(report_df) == 6
