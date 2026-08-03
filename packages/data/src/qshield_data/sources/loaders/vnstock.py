# Nguyễn Đỗ Minh Anh - loader dữ liệu giá/khối lượng từ vnstock.
"""vnstock (source=VCI) loader — port từ `CLEAN.ipynb` (`download_vnindex_vnstock`,
`download_ticker_vnstock`).

Nguồn CHÍNH cho VN-Index (Yahoo không có index VN). Cũng dùng làm alternative cho DNSE khi cần lấy
full history từ HNX/UPCOM cho các mã multi-exchange.
"""

from __future__ import annotations

import logging
import time

import pandas as pd
from vnstock import Vnstock

logger = logging.getLogger(__name__)

_RENAME = {
    "time": "date",
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "volume": "Volume",
}


def download_vnindex(start: str, end: str, max_retries: int = 3) -> pd.DataFrame | None:
    """Tải VN-Index THẬT từ vnstock (nguồn VCI — Vietcap), có retry.

    Trả về DataFrame index=date với cột Open/High/Low/Close/Volume, hoặc `None` nếu fail. Index
    không có Adj Close (index không bị điều chỉnh cổ tức/chia tách như cổ phiếu).
    """
    for attempt in range(max_retries):
        try:
            quote = Vnstock().stock(symbol="VNINDEX", source="VCI").quote
            df = quote.history(start=start, end=end, interval="1D")
            if df is None or df.empty:
                return None
            df = df.rename(columns=_RENAME)
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            return df.set_index("date")[["Open", "High", "Low", "Close", "Volume"]]
        except Exception as e:
            if attempt == max_retries - 1:
                logger.warning("vnstock VNINDEX failed after %d attempts: %s", max_retries, e)
                return None
    return None


def download_ticker(ticker: str, start: str, end: str, max_retries: int = 3) -> pd.DataFrame | None:
    """Tải giá 1 mã VN từ vnstock (source=VCI), có retry — alternative cho DNSE.

    Dùng cho các mã multi-exchange mà Yahoo `.VN` chỉ có data từ ngày lên HOSE. vnstock VCI cho
    phép lấy full history từ ngày niêm yết đầu tiên (kể cả HNX/UPCOM).

    Trả về DataFrame index=date với schema giống hệt yfinance output:
    `[Open, High, Low, Close, Adj Close, Volume]`. `Close = Adj Close` vì vnstock VCI trả về giá đã
    điều chỉnh mặc định, không tách riêng như Yahoo.
    """
    for attempt in range(max_retries):
        try:
            quote = Vnstock().stock(symbol=ticker, source="VCI").quote
            df = quote.history(start=start, end=end, interval="1D")
            if df is None or df.empty:
                return None
            df = df.rename(columns=_RENAME)
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            df = df.set_index("date")
            df["Adj Close"] = df["Close"]
            df = df[["Open", "High", "Low", "Close", "Adj Close", "Volume"]]
            df.index.name = "date"
            return df
        except Exception as e:
            if attempt == max_retries - 1:
                logger.warning("vnstock %s failed after %d attempts: %s", ticker, max_retries, e)
                return None
            time.sleep(1.0 * (attempt + 1))  # backoff nhẹ tránh throttle VCI
    return None
