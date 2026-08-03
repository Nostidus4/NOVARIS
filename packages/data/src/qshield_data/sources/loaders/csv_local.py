# Nguyễn Đỗ Minh Anh - loader dữ liệu từ CSV local — fallback source.
"""CSV local loader — offline mode / demo, khi không có mạng hoặc mọi API nguồn đều fail.

Đọc raw CSV đã tải sẵn (từ chính `fetch.fetch_all_prices`/`fetch_vn_index`, hoặc snapshot dùng cho
demo offline — xem `docs/runbook/demo_script.md` §8). Schema đầu ra khớp với các loader khác trong
`sources/loaders/` để `clean/normalize.py` xử lý đồng nhất bất kể nguồn.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


def load_from_csv(csv_path: Path) -> pd.DataFrame:
    """Đọc raw CSV đã tải sẵn, trả về DataFrame index=date, cột `_REQUIRED_COLUMNS`.

    Raise `ValueError` nếu thiếu cột bắt buộc — fail fast thay vì âm thầm tạo NaN.
    """
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.set_index("date")
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "date"

    missing = set(_REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{csv_path}: thiếu cột bắt buộc {sorted(missing)}")
    return df[_REQUIRED_COLUMNS]
