# Đỗ Ngọc Tân - schema returns.parquet: long format (date, ticker), simple + log return. Phối hợp Nguyễn Đỗ Minh Anh.
"""Schema `returns.parquet` — khớp cột thật do `qshield_data.returns.compute_asset_returns` +
`qshield_data.split.apply_splits` sinh ra (đã chạy thật trên dữ liệu thật, xem
`packages/data/src/qshield_data/returns.py`), không phải suy đoán từ tài liệu.

Long format, khóa chính `(date, ticker)`. `prev_adj`/`simple_return`/`log_return` là `NaN` ở ngày
đầu tiên mỗi ticker — ĐÚNG Ý (CLAUDE.md quy tắc 3: không forward-fill lợi suất).
"""

from __future__ import annotations

import pandera.pandas as pandera

ReturnsSchema = pandera.DataFrameSchema(
    {
        "date": pandera.Column("datetime64[ns]"),
        "ticker": pandera.Column(str),
        "open": pandera.Column(float),
        "high": pandera.Column(float),
        "low": pandera.Column(float),
        "close": pandera.Column(float),
        "adjusted_close": pandera.Column(float, pandera.Check.gt(0)),
        "volume": pandera.Column(int, pandera.Check.ge(0)),
        "source_id": pandera.Column(str),
        "data_version": pandera.Column(str),
        "quality_flag": pandera.Column(str),
        "turnover_value": pandera.Column(float, nullable=True),
        "prev_adj": pandera.Column(float, nullable=True),
        "simple_return": pandera.Column(float, nullable=True),
        "log_return": pandera.Column(float, nullable=True),
        "split": pandera.Column(
            str, pandera.Check.isin(["train", "validation", "test", "out_of_scope"])
        ),
    },
    unique=["date", "ticker"],
    coerce=True,
)
