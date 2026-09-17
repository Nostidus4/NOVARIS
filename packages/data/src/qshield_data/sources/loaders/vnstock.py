# Nguyễn Đỗ Minh Anh - loader VN-Index từ vnstock.
"""vnstock (source=VCI) loader cho VN-Index — port từ `CLEAN.ipynb` bản 2026-09-17.

`Full_Prices.xlsx` (FiinPro) không có chỉ số nên VN-Index vẫn tải qua API. Hai điểm bắt buộc:

- Dùng `vnstock.api.quote.Quote` — lớp `Vnstock()` đã ngừng hỗ trợ từ 31/08/2025.
- Tải THEO TỪNG NĂM rồi ghép: API VCI chỉ trả tối đa ~2.000 phiên mỗi lần, đếm lùi từ `end`. Gọi
  một lần cho 2016→2026 sẽ mất toàn bộ dữ liệu trước 08/2018 — và vì VN-Index là lịch giao dịch
  chuẩn, thiếu lịch sẽ âm thầm xoá giá cổ phiếu thật ở bước clean.
"""

from __future__ import annotations

import logging
import time

import pandas as pd
from vnstock.api.quote import Quote

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
    """Tải VN-Index THẬT từ vnstock (nguồn VCI — Vietcap) theo từng năm, có retry.

    Trả về DataFrame index=date với cột Open/High/Low/Close/Volume, hoặc `None` nếu một năm nào đó
    fail sau `max_retries` lần (không trả dữ liệu thiếu năm).
    """
    quote = Quote(symbol="VNINDEX", source="VCI")
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    parts = []
    for year in range(start_ts.year, end_ts.year + 1):
        y_start = max(start_ts, pd.Timestamp(f"{year}-01-01")).strftime("%Y-%m-%d")
        y_end = min(end_ts, pd.Timestamp(f"{year}-12-31")).strftime("%Y-%m-%d")
        for attempt in range(max_retries):
            try:
                part = quote.history(start=y_start, end=y_end, interval="1D")
                if part is not None and not part.empty:
                    parts.append(part)
                break
            except Exception as e:  # noqa: BLE001 -- vnstock SDK không có exception hierarchy công khai
                if attempt == max_retries - 1:
                    logger.warning(
                        "VNINDEX %d failed after %d attempts: %s", year, max_retries, e
                    )
                    return None
                time.sleep(2.0 * (attempt + 1))

    if not parts:
        return None
    df = pd.concat(parts, ignore_index=True).rename(columns=_RENAME)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df = (
        df.drop_duplicates("date", keep="last")
        .set_index("date")
        .sort_index()
        .loc[start_ts:end_ts, ["Open", "High", "Low", "Close", "Volume"]]
    )
    df.index.name = "date"
    return df
