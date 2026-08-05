# Nguyễn Anh Tú - test resolve sàn theo ngày và phát hiện vượt biên độ (DQ-007).
import pandas as pd
import pytest
from qshield_data.quality.price_limits import (
    find_price_limit_violations,
    resolve_exchange_column,
)

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


def test_multi_ticker_interleaved_rows_resolve_independently() -> None:
    # Trình pipeline thật gọi resolve_exchange_column một lần cho cả 8 mã, xen kẽ theo ngày —
    # không nhóm theo ticker như các test trên. Dùng index không mặc định để phơi ra bất kỳ
    # nhầm lẫn positional-vs-label nào trong `resolved[in_period] = ...`, và bố trí ACB ở cả
    # hai phía của mốc chuyển sàn để phơi ra bộ đếm `hits` bị rò rỉ giữa các ticker.
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2020-11-30", "2020-01-01", "2020-12-01", "2021-01-01"]
            ),
            "ticker": ["ACB", "VCB", "ACB", "VCB"],
        },
        index=pd.Index([5, 2, 9, 7]),
    )

    out = resolve_exchange_column(frame, _universe())

    assert out.index.equals(frame.index)
    assert out.loc[5] == "HNX"
    assert out.loc[2] == "HOSE"
    assert out.loc[9] == "HOSE"
    assert out.loc[7] == "HOSE"


def test_empty_periods_raise() -> None:
    empty = _universe(exchange_periods=[[], [{"exchange": "HOSE"}]])
    with pytest.raises(ValueError, match="ACB"):
        resolve_exchange_column(_returns(["2022-01-04"], ["ACB"]), empty)


_BANDS = {"HOSE": 0.07, "HNX": 0.10}
_TOL = 0.005


def _returns_with(
    values: list[float], dates: list[str], tickers: list[str]
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "ticker": tickers,
            "simple_return": values,
        }
    )


def test_value_exactly_at_boundary_is_not_a_violation() -> None:
    at_boundary = _returns_with([0.075], ["2022-01-04"], ["VCB"])
    out = find_price_limit_violations(
        at_boundary, _universe(), bands_by_exchange=_BANDS, tolerance_pct=_TOL
    )
    assert out.empty


def test_value_just_over_boundary_is_a_violation() -> None:
    over = _returns_with([0.0751], ["2022-01-04"], ["VCB"])
    out = find_price_limit_violations(
        over, _universe(), bands_by_exchange=_BANDS, tolerance_pct=_TOL
    )
    assert len(out) == 1
    assert out.iloc[0]["exchange"] == "HOSE"


def test_golden_case_vcb_2025_03_03() -> None:
    """Quan sát thật đã gây FAIL kurtosis — xem docs/perf/2026-08-05-kurtosis-fail-vcb.md."""
    vcb = _returns_with([-0.331104], ["2025-03-03"], ["VCB"])
    out = find_price_limit_violations(
        vcb, _universe(), bands_by_exchange=_BANDS, tolerance_pct=_TOL
    )
    assert len(out) == 1
    row = out.iloc[0]
    assert row["band"] == 0.07
    assert row["excess"] == pytest.approx(0.261104)


def test_acb_move_legal_on_hnx_but_illegal_on_hose() -> None:
    same_move = _returns_with(
        [-0.095, -0.095], ["2020-11-30", "2020-12-01"], ["ACB", "ACB"]
    )
    out = find_price_limit_violations(
        same_move, _universe(), bands_by_exchange=_BANDS, tolerance_pct=_TOL
    )
    assert len(out) == 1
    assert out.iloc[0]["exchange"] == "HOSE"


def test_null_return_is_skipped_not_flagged_and_not_an_error() -> None:
    """Phiên đầu tiên của mỗi mã không có giá trước đó nên simple_return là NaN (8 dòng thật)."""
    with_nan = _returns_with([float("nan")], ["2016-01-04"], ["VCB"])
    out = find_price_limit_violations(
        with_nan, _universe(), bands_by_exchange=_BANDS, tolerance_pct=_TOL
    )
    assert out.empty


def test_empty_result_carries_full_column_set() -> None:
    clean = _returns_with([0.01], ["2022-01-04"], ["VCB"])
    out = find_price_limit_violations(
        clean, _universe(), bands_by_exchange=_BANDS, tolerance_pct=_TOL
    )
    assert out.empty
    assert list(out.columns) == [
        "date",
        "ticker",
        "exchange",
        "simple_return",
        "band",
        "tolerance",
        "excess",
    ]


def test_output_sorted_by_excess_descending() -> None:
    mixed = _returns_with(
        [-0.331104, 0.09, 0.12],
        ["2025-03-03", "2022-01-04", "2022-01-05"],
        ["VCB", "VCB", "VCB"],
    )
    out = find_price_limit_violations(
        mixed, _universe(), bands_by_exchange=_BANDS, tolerance_pct=_TOL
    )
    assert list(out["excess"]) == sorted(out["excess"], reverse=True)
    assert out.iloc[0]["date"] == pd.Timestamp("2025-03-03")


def test_unknown_exchange_raises_naming_available_bands() -> None:
    upcom = pd.DataFrame(
        {"ticker": ["VCB"], "exchange_periods": [[{"exchange": "UPCOM"}]]}
    )
    rows = _returns_with([0.20], ["2022-01-04"], ["VCB"])
    with pytest.raises(ValueError, match="UPCOM"):
        find_price_limit_violations(
            rows, upcom, bands_by_exchange=_BANDS, tolerance_pct=_TOL
        )


def test_negative_tolerance_raises() -> None:
    rows = _returns_with([0.01], ["2022-01-04"], ["VCB"])
    with pytest.raises(ValueError, match="tolerance_pct"):
        find_price_limit_violations(
            rows, _universe(), bands_by_exchange=_BANDS, tolerance_pct=-0.01
        )
