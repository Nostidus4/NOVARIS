# Nguyễn Đỗ Minh Anh - xử lý sự kiện chia tách/cổ tức qua adjusted price.
"""Loại giá trước ngày niêm yết — port từ `CLEAN.ipynb` ("Kiểm tra không có giá trước ngày niêm
yết", PR-DAT-017).

Split/dividend adjustment nói chung KHÔNG cần re-implement ở đây: Yahoo (`Adj Close`) và DNSE
(`c` × 1000, gán làm `Adj Close`) thường đã trả giá điều chỉnh cổ tức + chia tách sẵn — xem
`sources/loaders/yahoo.py`, `sources/loaders/dnse.py`. **Ngoại lệ đã xác nhận:** VCB 2025-03-03 —
Yahoo KHÔNG điều chỉnh sự kiện này (`Adj Close` mang cùng bước nhảy với `Close`), phát hiện qua
DQ-007 (`quality/price_limits.py`), điều tra đầy đủ ở `docs/perf/2026-08-05-kurtosis-fail-vcb.md`.
`apply_registered_adjustments` xử lý đúng các ngoại lệ đã xác nhận thủ công này — file giữ tên
`corporate_actions.py` (không đổi thành `pre_listing.py`) đúng như dự tính ban đầu: "để có chỗ mở
rộng nếu sau này chuyển sang raw price + tự tính adjustment factor".
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

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
            "Loại %d row có date < first_trading_date (theo quy tắc PR-DAT-017)",
            n_removed,
        )

    cleaned = merged[~pre_listing].drop(columns=["first_trading_date"])
    return cleaned.reset_index(drop=True)


def apply_registered_adjustments(
    prices: pd.DataFrame, actions: Sequence[Mapping[str, Any]]
) -> pd.DataFrame:
    """Back-adjust `adjusted_close` cho các sự kiện corporate action đã XÁC NHẬN THỦ CÔNG trong
    `configs/base.yaml["corporate_actions"]`.

    Với mỗi entry `{ticker, event_date, adjustment_factor, ...}`: nhân `adjusted_close` của MỌI
    dòng `date < event_date` (đúng ticker) với `1 / adjustment_factor` — quy ước back-adjustment
    chuẩn, đúng cách Yahoo/DNSE tự áp dụng cho các sự kiện họ CÓ xử lý. Chỉ `adjusted_close` bị
    đổi; `open/high/low/close/volume` giữ nguyên làm bằng chứng lịch sử (đối chiếu khi cần).

    KHÔNG suy diễn hệ số điều chỉnh từ thống kê — `actions` phải được liệt kê tường minh sau khi
    con người đã điều tra và xác nhận (CLAUDE.md quy tắc 5: không tự sửa/xóa outlier). Entry cho
    ticker/ngày không có trong `prices` bị bỏ qua im lặng (universe/eligibility có thể thiếu
    một số ticker đã đăng ký trong bảng corporate actions).

    Raise `ValueError` nếu một entry thiếu khóa bắt buộc, hoặc `adjustment_factor <= 0`.
    """
    adjusted = prices.copy()
    for action in actions:
        missing = [
            k for k in ("ticker", "event_date", "adjustment_factor") if k not in action
        ]
        if missing:
            raise ValueError(
                f"Entry corporate_actions thiếu khóa {missing}: {dict(action)!r} — "
                "sửa configs/base.yaml (corporate_actions)."
            )
        ticker = str(action["ticker"])
        event_date = pd.Timestamp(action["event_date"])
        factor = float(action["adjustment_factor"])
        if factor <= 0:
            raise ValueError(
                f"adjustment_factor phải > 0 cho {ticker} @ {event_date.date()}, nhận {factor} "
                "(configs/base.yaml: corporate_actions)."
            )

        target = (adjusted["ticker"] == ticker) & (adjusted["date"] < event_date)
        n_rows = int(target.sum())
        if n_rows == 0:
            logger.warning(
                "corporate_actions: %s @ %s không khớp dòng nào trong prices (ticker không có "
                "trong universe hiện tại, hoặc không còn dữ liệu trước event_date) — bỏ qua.",
                ticker,
                event_date.date(),
            )
            continue

        adjusted.loc[target, "adjusted_close"] = (
            adjusted.loc[target, "adjusted_close"] / factor
        )
        logger.warning(
            "corporate_actions: back-adjust %d phiên của %s trước %s theo hệ số %.4f "
            "(xem evidence trong configs/base.yaml).",
            n_rows,
            ticker,
            event_date.date(),
            factor,
        )

    return adjusted
