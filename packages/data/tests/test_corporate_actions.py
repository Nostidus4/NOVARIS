# Nguyễn Đỗ Minh Anh - apply_registered_adjustments: back-adjust đúng ticker/ngày, không đụng gì khác.
import pandas as pd
import pytest
from qshield_data.clean.corporate_actions import apply_registered_adjustments


def _prices(rows: list[tuple[str, str, float, float]]) -> pd.DataFrame:
    """rows: (ticker, date, close, adjusted_close)."""
    df = pd.DataFrame(rows, columns=["ticker", "date", "close", "adjusted_close"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_prices_before_event_date_are_back_adjusted() -> None:
    prices = _prices(
        [
            ("VCB", "2025-02-27", 92000.0, 92000.0),
            ("VCB", "2025-02-28", 91862.35, 91862.35),
            ("VCB", "2025-03-03", 61446.39, 61446.39),
        ]
    )
    actions = [
        {"ticker": "VCB", "event_date": "2025-03-03", "adjustment_factor": 1.4950}
    ]

    out = apply_registered_adjustments(prices, actions).set_index("date")

    assert out.loc[pd.Timestamp("2025-02-27"), "adjusted_close"] == pytest.approx(
        92000.0 / 1.4950
    )
    assert out.loc[pd.Timestamp("2025-02-28"), "adjusted_close"] == pytest.approx(
        91862.35 / 1.4950
    )
    # Ngày sự kiện trở đi giữ nguyên — chỉ phiên TRƯỚC event_date bị back-adjust.
    assert out.loc[pd.Timestamp("2025-03-03"), "adjusted_close"] == pytest.approx(
        61446.39
    )


def test_raw_close_column_is_never_touched() -> None:
    prices = _prices([("VCB", "2025-02-28", 93300.00, 91862.35)])
    actions = [
        {"ticker": "VCB", "event_date": "2025-03-03", "adjustment_factor": 1.4950}
    ]

    out = apply_registered_adjustments(prices, actions)

    assert out.loc[0, "close"] == pytest.approx(93300.00)
    assert out.loc[0, "adjusted_close"] != pytest.approx(91862.35)


def test_return_after_adjustment_is_approximately_zero() -> None:
    """Khớp phép thử phản chứng trong docs/perf/2026-08-05-kurtosis-fail-vcb.md §5: sau khi sửa,
    return ngày sự kiện phải gần 0 (chia cổ tức không đổi tài sản nhà đầu tư)."""
    prices = _prices(
        [
            ("VCB", "2025-02-28", 93300.00, 91862.35),
            ("VCB", "2025-03-03", 62408.03, 61446.39),
        ]
    )
    actions = [
        {"ticker": "VCB", "event_date": "2025-03-03", "adjustment_factor": 1.4950}
    ]

    out = apply_registered_adjustments(prices, actions).set_index("date")
    prev_adj = out.loc[pd.Timestamp("2025-02-28"), "adjusted_close"]
    event_adj = out.loc[pd.Timestamp("2025-03-03"), "adjusted_close"]
    simple_return = event_adj / prev_adj - 1

    assert abs(simple_return) < 0.001


def test_other_tickers_and_dates_are_untouched() -> None:
    prices = _prices(
        [
            ("VCB", "2025-02-28", 93300.00, 91862.35),
            ("ACB", "2025-02-28", 30000.0, 30000.0),
        ]
    )
    actions = [
        {"ticker": "VCB", "event_date": "2025-03-03", "adjustment_factor": 1.4950}
    ]

    out = apply_registered_adjustments(prices, actions).set_index("ticker")

    assert out.loc["ACB", "adjusted_close"] == pytest.approx(30000.0)


def test_ticker_not_present_in_prices_is_skipped_silently() -> None:
    """Ticker không có trong prices không được raise (eligibility/universe subset)."""
    prices = _prices([("ACB", "2025-02-28", 30000.0, 30000.0)])
    actions = [
        {"ticker": "VCB", "event_date": "2025-03-03", "adjustment_factor": 1.4950}
    ]

    out = apply_registered_adjustments(prices, actions)

    assert len(out) == 1
    assert out.loc[0, "adjusted_close"] == pytest.approx(30000.0)


def test_empty_actions_returns_prices_unchanged() -> None:
    prices = _prices([("VCB", "2025-02-28", 93300.00, 91862.35)])

    out = apply_registered_adjustments(prices, [])

    assert out.loc[0, "adjusted_close"] == pytest.approx(91862.35)


def test_missing_required_key_raises_value_error() -> None:
    prices = _prices([("VCB", "2025-02-28", 93300.00, 91862.35)])
    actions = [{"ticker": "VCB", "event_date": "2025-03-03"}]  # thiếu adjustment_factor

    with pytest.raises(ValueError, match="adjustment_factor"):
        apply_registered_adjustments(prices, actions)


def test_non_positive_factor_raises_value_error() -> None:
    prices = _prices([("VCB", "2025-02-28", 93300.00, 91862.35)])
    actions = [{"ticker": "VCB", "event_date": "2025-03-03", "adjustment_factor": 0.0}]

    with pytest.raises(ValueError, match="> 0"):
        apply_registered_adjustments(prices, actions)
