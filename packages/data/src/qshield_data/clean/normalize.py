# Nguyễn Đỗ Minh Anh - chuẩn hóa ticker & ngày, bỏ trùng, đồng bộ lịch giao dịch.
"""Đọc raw CSV theo `raw_manifest` → concat → chuẩn hoá schema.

Port từ `CLEAN.ipynb` (cell "Đọc raw của từng ticker → concat → chuẩn hoá schema"), nguồn FiinPro.
Cột `AdjRatio` của raw CSV cố ý KHÔNG đưa vào processed (FiinPro bỏ sót sự kiện, không phép tính
nào cần nó).
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
    "Value": "turnover_value",  # giá trị khớp lệnh THẬT
    "VolumeTT": "volume_negotiated",
    "ValueTT": "turnover_negotiated",
}
_OUTPUT_COLS = [
    "date",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
    "turnover_value",
    "volume_negotiated",
    "turnover_negotiated",
    "source_id",
    "data_version",
]
_NUMERIC_COLS = _OUTPUT_COLS[2:11]


def load_and_normalize(raw_manifest: pd.DataFrame, data_version: str) -> pd.DataFrame:
    """Đọc từng file raw CSV `status == "OK"` trong `raw_manifest` → concat → chuẩn hoá schema.

    `open/high/low/close` là giá GỐC, `adjusted_close` là giá đóng cửa đã điều chỉnh của vendor.
    Raise `ValueError` nếu không có ticker nào `OK` hoặc file raw thiếu cột.
    """
    ok_rows = raw_manifest[raw_manifest["status"] == "OK"]
    if ok_rows.empty:
        raise ValueError(
            "raw_manifest không có ticker nào status='OK' — không thể normalize."
        )

    frames = []
    for _, m in ok_rows.iterrows():
        df = pd.read_csv(m["file"], parse_dates=["date"]).rename(columns=_RENAME)
        missing = set(_NUMERIC_COLS) - set(df.columns)
        if missing:
            raise ValueError(
                f"{m['file']}: thiếu cột {sorted(missing)} — raw CSV không đúng định dạng FiinPro, "
                "chạy lại `qshield-data fetch`."
            )
        for col in _NUMERIC_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["ticker"] = m["ticker"]
        df["source_id"] = m["source"]
        df["data_version"] = data_version
        frames.append(df[_OUTPUT_COLS])

    return pd.concat(frames, ignore_index=True)
