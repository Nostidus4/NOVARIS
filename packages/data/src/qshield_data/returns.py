# Nguyễn Đỗ Minh Anh - simple + log return — KHÔNG forward-fill.
"""Tính asset-level return — port từ `CLEAN.ipynb` ("ASSET-LEVEL RETURNS").

CLAUDE.md quy tắc 3: không forward-fill lợi suất. `groupby("ticker").shift(1)` chỉ lấy phiên liền
trước THỰC SỰ tồn tại của từng mã — ngày đầu tiên mỗi ticker luôn `NaN` (đúng ý, không fill).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_asset_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Tính `simple_return` và `log_return` per ticker, không cross-ticker leakage.

    Trả về `prices` (sort theo `ticker`, `date`) kèm 3 cột mới: `prev_adj`, `simple_return`,
    `log_return`.
    """
    df = prices.sort_values(["ticker", "date"]).copy()
    df["prev_adj"] = df.groupby("ticker")["adjusted_close"].shift(1)
    df["simple_return"] = df["adjusted_close"] / df["prev_adj"] - 1
    df["log_return"] = np.log(df["adjusted_close"] / df["prev_adj"])
    return df
