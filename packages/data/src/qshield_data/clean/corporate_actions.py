# Nguyễn Đỗ Minh Anh - xử lý sự kiện chia tách/cổ tức qua adjusted price.
"""Loại giá trước ngày niêm yết — port từ `CLEAN.ipynb` ("Kiểm tra không có giá trước ngày niêm
yết", PR-DAT-017).

Split/dividend adjustment KHÔNG làm ở đây: nguồn FiinPro trả `adjusted_close` đã điều chỉnh sẵn mọi
corporate action. Registry back-adjust thủ công (VCB 2025-03-03, TCB 2024-06-11) chỉ dùng để vá
lỗi của Yahoo và đã bị gỡ — áp lên dữ liệu FiinPro sẽ điều chỉnh hai lần (xem
`docs/data/2026-09-17-chuyen-nguon-gia-fiinpro.md` §3.1).

`first_trading_date` là chốt chặn DUY NHẤT cho lịch sử bị vendor gộp trước ngày niêm yết (vd VHM
có 381 phiên 2016-2017 trong FiinPro) — khai sai ngày này thì dữ liệu gộp lọt thẳng vào returns.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def remove_pre_listing(prices: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """Loại các row có `date < first_trading_date` của ticker tương ứng (PR-DAT-017, BR-002:
    không nội suy dữ liệu trước ngày niêm yết).
    """
    merged = prices.merge(
        universe[["ticker", "first_trading_date"]], on="ticker", how="left"
    )
    merged["first_trading_date"] = pd.to_datetime(merged["first_trading_date"])

    pre_listing = merged["date"] < merged["first_trading_date"]
    n_removed = int(pre_listing.sum())
    if n_removed:
        logger.warning(
            "Loại %d row có date < first_trading_date (theo quy tắc PR-DAT-017): %s",
            n_removed,
            merged.loc[pre_listing, "ticker"].value_counts().to_dict(),
        )

    cleaned = merged[~pre_listing].drop(columns=["first_trading_date"])
    return cleaned.reset_index(drop=True)
