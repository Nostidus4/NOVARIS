# Nguyễn Anh Tú - test resolve sàn theo ngày và phát hiện vượt biên độ (DQ-007).
import math

import pandas as pd
import pytest
from qshield_data.quality.price_limits import (
    find_price_limit_violations,
    resolve_exchange_column,
)
from qshield_data.quality.report import write_violations

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


def test_exchange_current_mismatch_with_periods_raises_naming_both_values() -> None:
    """`exchange_current` và `exchange_periods` là hai nguồn ghi lịch sử sàn độc lập trong
    configs/universe.yaml — chỉ `exchange_periods` được đọc, nên nếu chúng lệch nhau (một cái
    được sửa, cái kia bị quên) thì phải nổ lỗi ngay, không được im lặng dùng `exchange_periods`
    và bỏ qua `exchange_current` (finding Important 1, review round cuối).
    """
    mismatched = pd.DataFrame(
        {
            "ticker": ["ACB"],
            "exchange_current": ["HNX"],  # cố tình lệch: period đang hiệu lực là HOSE
            "exchange_periods": [[{"exchange": "HOSE"}]],
        }
    )
    with pytest.raises(ValueError, match="ACB.*HOSE.*HNX|ACB.*HNX.*HOSE"):
        resolve_exchange_column(_returns(["2022-01-04"], ["ACB"]), mismatched)


def test_exchange_current_absent_column_does_not_trigger_cross_check() -> None:
    """Universe không có cột `exchange_current` (vd. các test helper thuần trong module này)
    phải tiếp tục hoạt động không bị chặn bởi validation mới — guard trên sự hiện diện của cột."""
    out = resolve_exchange_column(
        _returns(["2022-01-04"], ["VCB"]),
        _universe(),  # _universe() không có exchange_current
    )
    assert list(out) == ["HOSE"]


def test_exchange_periods_as_repr_string_raises_naming_ticker() -> None:
    """Round-trip YAML → `registry.save_universe_and_sources` (CSV) → `pd.read_csv` biến
    `exchange_periods` (list[dict]) thành chuỗi repr Python. Một `str` cũng là `Sequence` nên
    `isinstance(x, Sequence)` một mình sẽ cho qua — phải loại `str` tường minh (finding
    Important 3, review round cuối)."""
    malformed = pd.DataFrame(
        {"ticker": ["ACB"], "exchange_periods": ["[{'exchange': 'HOSE'}]"]}
    )
    with pytest.raises(ValueError, match="ACB"):
        resolve_exchange_column(_returns(["2022-01-04"], ["ACB"]), malformed)


def test_period_missing_exchange_key_raises_naming_ticker() -> None:
    """Period thiếu khoá 'exchange' phải raise `ValueError` có ngữ cảnh, không phải `KeyError`
    trần (Minor 3, review round cuối)."""
    bad_period = _universe(
        exchange_periods=[[{"until": "2020-11-30"}], [{"exchange": "HOSE"}]]
    )
    with pytest.raises(ValueError, match="ACB"):
        resolve_exchange_column(_returns(["2020-01-04"], ["ACB"]), bad_period)


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
    # Dùng đúng float mà implementation tính (_BANDS["HOSE"] + _TOL), không gõ tay 0.075 —
    # 0.075 gõ tay nằm DƯỚI ngưỡng do sai số biểu diễn nhị phân, nên test sẽ pass dù dùng
    # ">" hay ">=", không phân biệt được strict inequality (xem finding 1 review round 1).
    threshold = _BANDS["HOSE"] + _TOL
    at_boundary = _returns_with([threshold], ["2022-01-04"], ["VCB"])
    out = find_price_limit_violations(
        at_boundary, _universe(), bands_by_exchange=_BANDS, tolerance_pct=_TOL
    )
    assert out.empty


def test_value_just_over_boundary_is_a_violation() -> None:
    # math.nextafter(threshold, inf) là giá trị float nhỏ nhất CHỨNG MINH được lớn hơn threshold —
    # loại bỏ mọi nghi ngờ về sai số làm tròn khi so với giá trị "gõ tay lớn hơn một chút".
    threshold = _BANDS["HOSE"] + _TOL
    just_over = math.nextafter(threshold, math.inf)
    over = _returns_with([just_over], ["2022-01-04"], ["VCB"])
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


def test_ties_in_excess_break_deterministically_by_date_then_ticker() -> None:
    # Hai mã, hai ngày, cùng |simple_return| -> cùng "excess". Không có unstable sort nào được
    # tin cậy để quyết định thứ tự các dòng bằng nhau; sort phải có khóa phụ tường minh
    # (date, rồi ticker) để artifact CSV có thứ tự lặp lại được giữa các lần chạy.
    tied = _returns_with(
        [0.12, 0.12, 0.12, 0.12],
        ["2022-01-05", "2022-01-04", "2022-01-04", "2022-01-05"],
        ["VCB", "VCB", "ACB", "ACB"],
    )
    universe_two = _universe(
        exchange_periods=[[{"exchange": "HOSE"}], [{"exchange": "HOSE"}]]
    )
    out = find_price_limit_violations(
        tied, universe_two, bands_by_exchange=_BANDS, tolerance_pct=_TOL
    )
    expected = [
        (pd.Timestamp("2022-01-04"), "ACB"),
        (pd.Timestamp("2022-01-04"), "VCB"),
        (pd.Timestamp("2022-01-05"), "ACB"),
        (pd.Timestamp("2022-01-05"), "VCB"),
    ]
    assert list(zip(out["date"], out["ticker"], strict=True)) == expected

    # Đổi thứ tự input ngược lại: kết quả phải giống hệt — đây mới là phần chứng minh tính
    # xác định, vì một unstable sort có thể tình cờ đúng thứ tự ở một chiều input.
    tied_reversed = tied.iloc[::-1].reset_index(drop=True)
    out_reversed = find_price_limit_violations(
        tied_reversed, universe_two, bands_by_exchange=_BANDS, tolerance_pct=_TOL
    )
    assert (
        list(zip(out_reversed["date"], out_reversed["ticker"], strict=True)) == expected
    )


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


def test_write_violations_writes_even_when_empty(tmp_path) -> None:
    """Ghi cả khi rỗng: thiếu file phải có nghĩa 'gate chưa chạy', khác với 'không tìm thấy gì'."""
    empty = pd.DataFrame(
        columns=[
            "date",
            "ticker",
            "exchange",
            "simple_return",
            "band",
            "tolerance",
            "excess",
        ]
    )
    out = write_violations(empty, tmp_path / "reports" / "price_limit_violations.csv")
    assert out.exists()
    assert pd.read_csv(out).empty


def test_write_violations_round_trips_columns_and_row_order(tmp_path) -> None:
    """Khung có dữ liệu, đã sort theo `excess` giảm dần trước khi truyền vào (đúng như CLI làm) —
    phải đọc lại được ĐÚNG bộ cột và ĐÚNG thứ tự dòng. Bug `to_csv` xáo trộn dòng hoặc rớt cột sẽ
    không bị `test_write_violations_writes_even_when_empty` bắt (khung đó không có dòng nào để mà
    xáo trộn), nên cần một test riêng trên khung 3 dòng.
    """
    columns = [
        "date",
        "ticker",
        "exchange",
        "simple_return",
        "band",
        "tolerance",
        "excess",
    ]
    populated = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-03-03", "2025-10-13", "2021-07-09"]),
            "ticker": ["VCB", "VIC", "MWG"],
            "exchange": ["HOSE", "HOSE", "HOSE"],
            "simple_return": [-0.331104, 0.144290, 0.125638],
            "band": [0.07, 0.07, 0.07],
            "tolerance": [0.005, 0.005, 0.005],
            "excess": [0.261104, 0.074290, 0.055638],
        }
    )[columns]

    out = write_violations(
        populated, tmp_path / "reports" / "price_limit_violations.csv"
    )
    read_back = pd.read_csv(out, parse_dates=["date"])

    assert list(read_back.columns) == columns
    assert list(read_back["ticker"]) == ["VCB", "VIC", "MWG"]
    assert list(read_back["excess"]) == sorted(read_back["excess"], reverse=True)
