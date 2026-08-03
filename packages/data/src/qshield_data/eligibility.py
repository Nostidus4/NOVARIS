# Nguyễn Đỗ Minh Anh - eligibility engine (file mới, Structure.md chưa liệt kê — xem plan.md §3.3/§6 câu 2).
"""Eligibility Engine — port từ `CLEAN.ipynb` (`build_eligibility`, PR-DAT-015/016).

File riêng thay vì gộp vào `features.py`: eligibility là một *gate* point-in-time (điều kiện đủ để
một mã được coi là ứng viên tại một ngày đánh giá — PR-DAT-019), không phải một feature đưa vào
model. Logic đã fix 2 bug trong lúc debug notebook:

- BUG FIX 1 (PR-DAT-016): coverage chỉ cần `adjusted_close > 0`, KHÔNG yêu cầu `quality_flag=="OK"`
  — ngày `ZERO_VOLUME` (mã ít giao dịch, vẫn có giá tham chiếu) không bị coi là "không có data".
  Vấn đề thanh khoản đã có `LOW_LIQUIDITY` (rolling turnover) lo riêng.
- BUG FIX 2: coverage tính từ `first_data_date` (ngày dữ liệu thực sự bắt đầu), không phải luôn từ
  `first_trading_date` khai báo — nếu nguồn chính (DNSE) fail và fallback Yahoo (chỉ có HOSE), mã
  đó không bị phạt oan vì "thiếu" phần lịch sử mà thực ra chưa từng tải được.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_eligibility(
    prices: pd.DataFrame,
    universe: pd.DataFrame,
    min_history_sessions: int,
    min_coverage_pct: float,
    min_turnover_20d_vnd: float,
) -> pd.DataFrame:
    """Tính eligibility point-in-time cho từng (`date`, `ticker`).

    `all_dates` = union ngày có trong `prices` — an toàn làm trading calendar vì phantom days của
    Yahoo đã bị loại ở `clean.validate_prices.remove_yahoo_phantom_days` trước khi `prices` được
    truyền vào đây (không cần đọc riêng VN-Index calendar nữa).

    Trả về DataFrame `[date, ticker, eligible_flag, reason_code, sessions_available, coverage_pct,
    avg_turnover_20d]`, `reason_code` ∈ {OK, NOT_LISTED_AT_DATE, INSUFFICIENT_HISTORY,
    LOW_COVERAGE, SUSPENDED_OR_NO_DATA, LOW_LIQUIDITY}.
    """
    universe_lookup = (
        universe.set_index("ticker")["first_trading_date"]
        .apply(pd.to_datetime)
        .to_dict()
    )
    all_dates = pd.Series(sorted(prices["date"].unique()), name="date")

    out = []
    for ticker in universe["ticker"]:
        first_dt = universe_lookup[ticker]
        sub = prices[prices["ticker"] == ticker].sort_values("date").set_index("date")
        sub_full = sub.reindex(all_dates)

        has_data = sub_full["adjusted_close"].notna() & (sub_full["adjusted_close"] > 0)
        sessions_avail = has_data.cumsum()

        first_data_idx = has_data[has_data].index
        first_data_date = (
            pd.Timestamp(first_data_idx[0])
            if len(first_data_idx) > 0
            else pd.Timestamp("2999-12-31")
        )
        effective_start = max(first_dt, first_data_date)

        listed_flag = pd.Series(
            all_dates.values >= effective_start, index=all_dates.values
        )
        expected_sessions = listed_flag.cumsum()

        with np.errstate(divide="ignore", invalid="ignore"):
            coverage = sessions_avail.values / np.maximum(expected_sessions.values, 1)

        avg_turnover = sub_full["turnover_value"].rolling(20, min_periods=10).mean()

        for i, dt in enumerate(all_dates):
            reason = "OK"
            eligible = True

            if dt < first_dt:
                reason, eligible = "NOT_LISTED_AT_DATE", False
            elif sessions_avail.iloc[i] < min_history_sessions:
                reason, eligible = "INSUFFICIENT_HISTORY", False
            elif coverage[i] < min_coverage_pct:
                reason, eligible = "LOW_COVERAGE", False
            elif not has_data.iloc[i]:
                reason, eligible = "SUSPENDED_OR_NO_DATA", False
            elif (
                pd.isna(avg_turnover.iloc[i])
                or avg_turnover.iloc[i] < min_turnover_20d_vnd
            ):
                reason, eligible = "LOW_LIQUIDITY", False

            out.append(
                {
                    "date": dt,
                    "ticker": ticker,
                    "eligible_flag": eligible,
                    "reason_code": reason,
                    "sessions_available": int(sessions_avail.iloc[i]),
                    "coverage_pct": float(coverage[i]),
                    "avg_turnover_20d": (
                        float(avg_turnover.iloc[i])
                        if pd.notna(avg_turnover.iloc[i])
                        else np.nan
                    ),
                }
            )
    return pd.DataFrame(out)
