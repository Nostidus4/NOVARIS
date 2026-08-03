# Nguyễn Đỗ Minh Anh - xử lý sự kiện chia tách/cổ tức qua adjusted price.
"""Loại giá trước ngày niêm yết — port từ `CLEAN.ipynb` ("Kiểm tra không có giá trước ngày niêm
yết", PR-DAT-017).

Split/dividend adjustment KHÔNG cần re-implement ở đây: Yahoo (`Adj Close`) và DNSE (`c` × 1000,
gán làm `Adj Close`) đều đã trả giá điều chỉnh cổ tức + chia tách sẵn — xem
`sources/loaders/yahoo.py`, `sources/loaders/dnse.py`. File này giữ tên `corporate_actions.py`
(không đổi thành `pre_listing.py`) để có chỗ mở rộng nếu sau này chuyển sang raw price + tự tính
adjustment factor.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def remove_pre_listing(prices: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """Loại các row có `date < first_trading_date` của ticker tương ứng (PR-DAT-017, BR-002:
    không nội suy dữ liệu trước ngày niêm yết).
    """
    merged = prices.merge(universe[["ticker", "first_trading_date"]], on="ticker", how="left")
    merged["first_trading_date"] = pd.to_datetime(merged["first_trading_date"])

    pre_listing = merged["date"] < merged["first_trading_date"]
    n_removed = int(pre_listing.sum())
    if n_removed:
        logger.warning(
            "Loại %d row có date < first_trading_date (theo quy tắc PR-DAT-017)", n_removed
        )

    cleaned = merged[~pre_listing].drop(columns=["first_trading_date"])
    return cleaned.reset_index(drop=True)
