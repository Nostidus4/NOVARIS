# Nguyễn Đỗ Minh Anh - chuẩn hóa ticker & ngày, bỏ trùng, đồng bộ lịch giao dịch.
"""Đọc raw CSV theo `raw_manifest` → concat → chuẩn hoá schema.

Port từ `CLEAN.ipynb` (cell "Đọc raw của từng ticker → concat → chuẩn hoá schema").
"""

from __future__ import annotations

import pandas as pd

_RENAME = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adjusted_close",
    "Volume": "volume",
}
_NUMERIC_COLS = ["open", "high", "low", "close", "adjusted_close", "volume"]
_OUTPUT_COLS = [
    "date",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
    "source_id",
    "data_version",
]


def load_and_normalize(raw_manifest: pd.DataFrame, data_version: str) -> pd.DataFrame:
    """Đọc từng file raw CSV `status == "OK"` trong `raw_manifest` → concat → chuẩn hoá schema.

    Rename cột Yahoo/DNSE-style (`Open`, `Adj Close`, ...) sang schema chuẩn của package
    (`open`, `adjusted_close`, ...), ép kiểu numeric, gắn `ticker`/`source_id`/`data_version`.

    `source_id` lấy từ cột `source` của `raw_manifest` (vd `YF_PRICES`, `DNSE_PRICES`,
    `YF_PRICES_FALLBACK`) — manifest dùng cột không có suffix `_id`, đây là schema đích downstream.

    Trả về DataFrame long-format, một dòng / (`date`, `ticker`). Raise `ValueError` nếu không có
    ticker nào `OK`.
    """
    ok_rows = raw_manifest[raw_manifest["status"] == "OK"]
    if ok_rows.empty:
        raise ValueError("raw_manifest không có ticker nào status='OK' — không thể normalize.")

    frames = []
    for _, m in ok_rows.iterrows():
        df = pd.read_csv(m["file"], parse_dates=["date"])
        df = df.rename(columns=_RENAME)
        for col in _NUMERIC_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["ticker"] = m["ticker"]
        df["source_id"] = m["source"]
        df["data_version"] = data_version
        frames.append(df[_OUTPUT_COLS])

    return pd.concat(frames, ignore_index=True)
