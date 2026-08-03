# Nguyễn Đỗ Minh Anh - kiểm tra giá âm/bằng 0, volume bất thường.
"""Dedup, loại phantom day của Yahoo, gắn cờ chất lượng giá.

Port từ `CLEAN.ipynb` "Bước 3" (cell dedup/phantom/quality_flag), đã bao gồm 2 bug fix thực hiện
trong quá trình debug notebook:

1. Dedup ưu tiên row volume cao nhất khi trùng `(date, ticker)` (thay vì `keep="first"` mặc định —
   DNSE thỉnh thoảng trả 2 row cho cùng ngày, ví dụ ACB 2022-12-27: volume 418.000 vs 2.040.100; row
   volume cao hơn là bản đã tổng hợp đầy đủ cuối phiên).
2. Loại "phantom day" của Yahoo: Yahoo forward-fill 1 row cho ngày HOSE nghỉ lễ (close = close ngày
   trước, volume = 0) để chart không bị gap — không phải phiên giao dịch thật. Dùng VN-Index (feed
   thật từ broker VN, không có phantom day) làm trading calendar chuẩn: ngày nào Yahoo có nhưng
   VN-Index không có thì xóa. Khác `ZERO_VOLUME` thật (có phiên nhưng không ai khớp lệnh) — cái đó
   vẫn giữ nguyên, chỉ gắn cờ.
"""

from __future__ import annotations

import pandas as pd

_YAHOO_SOURCE_IDS = ("YF_PRICES", "YF_PRICES_FALLBACK")


def dedup_prices(prices: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Loại row trùng `(date, ticker)`, ưu tiên giữ row có volume cao nhất.

    Sort theo `(date, ticker, volume)` tăng dần rồi `drop_duplicates(keep="last")` — đảm bảo row
    volume lớn nhất trong nhóm trùng nằm cuối và được giữ lại.

    Trả về `(df_deduped, n_removed)`.
    """
    before = len(prices)
    sorted_df = prices.sort_values(
        ["date", "ticker", "volume"], ascending=[True, True, True], na_position="first"
    )
    deduped = sorted_df.drop_duplicates(subset=["date", "ticker"], keep="last")
    return deduped, before - len(deduped)


def remove_yahoo_phantom_days(
    prices: pd.DataFrame, vn_index: pd.DataFrame | None
) -> tuple[pd.DataFrame, int]:
    """Loại ngày Yahoo forward-fill (phantom day) mà VN-Index không có phiên giao dịch.

    `vn_index`: DataFrame index=date của VN-Index thật (từ `sources.fetch.fetch_vn_index`), hoặc
    `None` nếu VN-Index không tải được — trong trường hợp đó bỏ qua bước này (không có trading
    calendar chuẩn để đối chiếu) và trả về `prices` nguyên vẹn với `n_removed=0`.

    Chỉ áp dụng cho `source_id` thuộc Yahoo (`YF_PRICES`, `YF_PRICES_FALLBACK`) — DNSE là feed thật
    nên không có phantom day.
    """
    if vn_index is None:
        return prices, 0

    vn_trading_days = set(pd.to_datetime(vn_index.index).normalize())
    is_yahoo_source = prices["source_id"].isin(_YAHOO_SOURCE_IDS)
    is_phantom = is_yahoo_source & ~prices["date"].isin(vn_trading_days)

    n_phantom = int(is_phantom.sum())
    cleaned = prices[~is_phantom].reset_index(drop=True)
    return cleaned, n_phantom


def flag_price_quality(prices: pd.DataFrame) -> pd.DataFrame:
    """Thêm cột `quality_flag` (bitmask pipe-separated) và `turnover_value`.

    `quality_flag`: `"OK"` hoặc kết hợp của `NONPOS_PRICE|NONPOS_CLOSE|NEG_VOLUME|ZERO_VOLUME`.
    Đây là gắn cờ, KHÔNG xóa row (CLAUDE.md quy tắc 5: không tự xóa outlier).

    `turnover_value = close * volume` (VNĐ) — dùng cho eligibility (rolling turnover 20 ngày).
    """
    out = prices.copy()

    nonpos_price = out["adjusted_close"].isna() | (out["adjusted_close"] <= 0)
    nonpos_close = out["close"].isna() | (out["close"] <= 0)
    neg_volume = out["volume"].notna() & (out["volume"] < 0)
    zero_volume = out["volume"].notna() & (out["volume"] == 0)

    flags = pd.Series([""] * len(out), index=out.index)
    for mask, name in [
        (nonpos_price, "NONPOS_PRICE"),
        (nonpos_close, "NONPOS_CLOSE"),
        (neg_volume, "NEG_VOLUME"),
        (zero_volume, "ZERO_VOLUME"),
    ]:
        flags = flags.where(~mask, flags + "|" + name)
    flags = flags.str.lstrip("|")
    out["quality_flag"] = flags.where(flags != "", "OK")

    out["turnover_value"] = out["close"] * out["volume"]
    return out
