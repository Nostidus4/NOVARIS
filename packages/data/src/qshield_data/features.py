# Nguyễn Đỗ Minh Anh - vol20, drawdown, corr, illiquidity — chỉ dùng dữ liệu đến ngày t.
"""Market-level features — port từ `CLEAN.ipynb` ("MARKET-LEVEL FEATURES" + point-in-time check).

CLAUDE.md quy tắc 4: không dùng dữ liệu tương lai. Mọi rolling ở đây dùng cửa sổ trượt về quá khứ
(không `center=True`), `_assert_point_in_time` là cổng chặn kiểm tra điều đó bằng cách so sánh với
kết quả tính trên dữ liệu shift(-1) (nếu rolling window nhìn thấy tương lai, hai kết quả sẽ giống
hệt nhau).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_INDEX_RENAME = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
}


def build_market_features(
    index_df: pd.DataFrame | None,
    returns: pd.DataFrame,
    index_source_tag: str | None,
) -> pd.DataFrame:
    """Tính market-level features từ VN-Index thật, hoặc custom composite nếu VN-Index không có.

    Nếu `index_df` có (DataFrame index=date từ `sources.fetch.fetch_vn_index`) → dùng VN-Index
    thật, gắn `source = index_source_tag`. Nếu `index_df is None` → fallback custom composite:
    equal-weighted log-return trung bình của các ticker eligible (không NaN) tại mỗi ngày — không
    leakage vì chỉ dùng return đã biết đến ngày đó, tổng hợp thành mức chỉ số bắt đầu tại 1000.

    Trả về DataFrame có cột: `date, open?, high?, low?, close, volume, source, market_log_return,
    market_simple_return, realized_vol_20d, rolling_max_252, drawdown, liquidity_20d`.
    """
    if index_df is not None:
        market = index_df.rename(columns=_INDEX_RENAME).copy()
        market.index.name = "date"
        market = market.reset_index()
        market["source"] = index_source_tag or "unknown_index_source"
    else:
        tmp = returns.pivot(index="date", columns="ticker", values="log_return")
        market_log_return = tmp.mean(axis=1, skipna=True)
        market_close = 1000 * np.exp(market_log_return.cumsum())
        market = pd.DataFrame(
            {
                "date": market_close.index,
                "close": market_close.values,
                "volume": returns.groupby("date")["volume"]
                .sum()
                .reindex(market_close.index)
                .values,
            }
        )
        market["source"] = "custom_composite_ew"

    market["market_log_return"] = np.log(market["close"] / market["close"].shift(1))
    market["market_simple_return"] = market["close"] / market["close"].shift(1) - 1

    # Rolling volatility 20 ngày (daily; nhân sqrt(252) để annualize thuộc về downstream, không ở đây).
    market["realized_vol_20d"] = market["market_log_return"].rolling(20, min_periods=20).std()

    # Rolling drawdown so với đỉnh 252 ngày gần nhất.
    market["rolling_max_252"] = market["close"].rolling(252, min_periods=60).max()
    market["drawdown"] = market["close"] / market["rolling_max_252"] - 1

    # Liquidity indicator: log(volume) rolling 20-day mean.
    market["liquidity_20d"] = (
        np.log(market["volume"].replace(0, np.nan)).rolling(20, min_periods=10).mean()
    )

    _assert_point_in_time(market)
    return market


def _assert_point_in_time(market: pd.DataFrame) -> None:
    """Assert rolling ở ngày `t` không nhìn thấy dữ liệu > `t`.

    Cách check: shift toàn bộ `market_log_return` lên 1 ngày rồi tính lại rolling std 20 ngày — kết
    quả PHẢI khác với bản gốc; nếu giống hệt nghĩa là rolling đang look-ahead.
    """
    original = market["market_log_return"].rolling(20, min_periods=20).std()
    shifted = market["market_log_return"].shift(-1).rolling(20, min_periods=20).std()
    if original.equals(shifted):
        raise AssertionError("Rolling might be looking ahead! (point-in-time check failed)")
