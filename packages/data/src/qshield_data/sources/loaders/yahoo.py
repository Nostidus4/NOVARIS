# Nguyễn Đỗ Minh Anh - loader dữ liệu giá/khối lượng từ Yahoo Finance.
"""Yahoo Finance loader — port từ `CLEAN.ipynb` (hàm `download_ticker`).

Logic giữ nguyên như notebook: retry `max_retries` lần, `timeout=30` (mặc định curl ~10s hay
timeout khi tải liên tiếp nhiều mã) và backoff `2.0 * (attempt + 1)` giây giữa các lần thử — hai
điểm này đã được thêm vào notebook sau khi GAS.VN/MSN.VN bị timeout dồn dập lúc tải 30 mã liên tục.

Khác notebook: dùng `logging` thay vì `print()` (CLAUDE.md: "Không print() trong package").
"""

from __future__ import annotations

import logging
import time

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def download_ticker(
    symbol: str, start: str, end: str, max_retries: int = 3
) -> pd.DataFrame | None:
    """Tải giá 1 mã từ Yahoo Finance, có retry + backoff.

    Trả về DataFrame index=date (cột Open/High/Low/Close/Adj Close/Volume), hoặc `None` nếu fail
    sau `max_retries` lần thử.
    """
    for attempt in range(max_retries):
        try:
            df = yf.download(
                symbol,
                start=start,
                end=end,
                progress=False,
                auto_adjust=False,  # KHÔNG dùng auto_adjust để giữ cả Close và Adj Close
                actions=False,
                threads=False,
                timeout=30,
            )
            if df is None or df.empty:
                return None
            # yfinance đôi khi trả MultiIndex columns nếu list symbols; ép về flat
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df.index.name = "date"
            return df
        except Exception as e:
            if attempt == max_retries - 1:
                logger.warning(
                    "Yahoo %s failed after %d attempts: %s", symbol, max_retries, e
                )
                return None
            time.sleep(2.0 * (attempt + 1))
    return None
