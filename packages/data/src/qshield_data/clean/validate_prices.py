# Nguyễn Đỗ Minh Anh - kiểm tra giá âm/bằng 0, volume bất thường.
"""Dedup, loại ngày không có giao dịch thật, gắn cờ chất lượng giá.

Port từ `CLEAN.ipynb` "Bước 3" (bản 2026-09-17, nguồn FiinPro):

1. Dedup ưu tiên row volume cao nhất khi trùng `(date, ticker)`.
2. Loại ngày không có trong lịch VN-Index — áp cho MỌI nguồn (lịch giao dịch là chuẩn chung). Với
   FiinPro kỳ vọng xoá 0 dòng; khác 0 là dấu hiệu cần xem lại.
3. Gắn cờ (không xoá): giá ≤ 0, volume âm/bằng 0, OHLC tự mâu thuẫn.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def dedup_prices(prices: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Loại row trùng `(date, ticker)`, ưu tiên giữ row có volume cao nhất.

    Trả về `(df_deduped, n_removed)`.
    """
    before = len(prices)
    sorted_df = prices.sort_values(
        ["date", "ticker", "volume"], ascending=[True, True, True], na_position="first"
    )
    deduped = sorted_df.drop_duplicates(subset=["date", "ticker"], keep="last")
    return deduped, before - len(deduped)


def remove_non_trading_days(
    prices: pd.DataFrame, vn_index: pd.DataFrame | None
) -> tuple[pd.DataFrame, int]:
    """Loại row có ngày không nằm trong lịch giao dịch VN-Index.

    `vn_index`: DataFrame index=date của VN-Index thật, hoặc `None` — khi đó bỏ qua bước này và trả
    về `prices` nguyên vẹn với `n_removed=0`.
    """
    if vn_index is None:
        return prices, 0

    trading_days = set(pd.to_datetime(vn_index.index).normalize())
    off_calendar = ~prices["date"].isin(trading_days)
    n_removed = int(off_calendar.sum())
    if n_removed:
        logger.warning(
            "Loại %d row không khớp lịch VN-Index: %s",
            n_removed,
            prices.loc[off_calendar, "ticker"].value_counts().to_dict(),
        )
    return prices[~off_calendar].reset_index(drop=True), n_removed


def flag_price_quality(prices: pd.DataFrame) -> pd.DataFrame:
    """Thêm cột `quality_flag` (pipe-separated) và điền `turnover_value` còn thiếu.

    `quality_flag`: `"OK"` hoặc kết hợp của
    `NONPOS_PRICE|NONPOS_CLOSE|NEG_VOLUME|ZERO_VOLUME|INVALID_OHLC`. Gắn cờ, KHÔNG xóa row
    (CLAUDE.md quy tắc 5).

    `INVALID_OHLC`: `high < low` hoặc `open` ngoài `[low, high]`. Không kiểm tra `close`: giá đóng
    cửa có thể là bình quân gia quyền (UPCOM) nên nằm ngoài `[low, high]` không phải lỗi
    (vd VIB 2019-07-04).

    `turnover_value`: giữ giá trị khớp lệnh thật của vendor; chỉ row thiếu mới ước lượng
    `close × volume` (log số row phải ước lượng).
    """
    out = prices.copy()

    nonpos_price = out["adjusted_close"].isna() | (out["adjusted_close"] <= 0)
    nonpos_close = out["close"].isna() | (out["close"] <= 0)
    neg_volume = out["volume"].notna() & (out["volume"] < 0)
    zero_volume = out["volume"].notna() & (out["volume"] == 0)
    has_hl = out["low"].notna() & out["high"].notna()
    invalid_ohlc = has_hl & (
        (out["high"] < out["low"])
        | (out["open"] < out["low"])
        | (out["open"] > out["high"])
    )

    flags = pd.Series([""] * len(out), index=out.index)
    for mask, name in [
        (nonpos_price, "NONPOS_PRICE"),
        (nonpos_close, "NONPOS_CLOSE"),
        (neg_volume, "NEG_VOLUME"),
        (zero_volume, "ZERO_VOLUME"),
        (invalid_ohlc, "INVALID_OHLC"),
    ]:
        flags = flags.where(~mask, flags + "|" + name)
    flags = flags.str.lstrip("|")
    out["quality_flag"] = flags.where(flags != "", "OK")

    missing_tv = out["turnover_value"].isna()
    if missing_tv.any():
        logger.warning(
            "turnover_value thiếu ở %d row — ước lượng close × volume",
            int(missing_tv.sum()),
        )
    out.loc[missing_tv, "turnover_value"] = (
        out.loc[missing_tv, "close"] * out.loc[missing_tv, "volume"]
    )
    return out
