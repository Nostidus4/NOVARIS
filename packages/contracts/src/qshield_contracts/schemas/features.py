# Đỗ Ngọc Tân - schema features.parquet: 1 dòng/ngày. Phối hợp Nguyễn Đỗ Minh Anh.
"""Schema `market_features.parquet` — khớp cột thật do `qshield_data.features.build_market_features`
sinh ra (xem `packages/data/src/qshield_data/features.py`).

Tên file thật là `market_features.parquet` (không phải `features.parquet` như tên gọi chung trong
`docs/architecture/data_contracts.md`) — dùng tên thật vì code là nguồn sự thật.

`open`/`high`/`low` là `required=False`: nhánh custom-composite (khi VN-Index không tải được) không
sinh 3 cột này — THIẾU HẲN CỘT, không phải NaN. Validate với `required=True` sẽ fail oan ở nhánh
fallback dù dữ liệu đúng thiết kế.
"""

from __future__ import annotations

import pandera.pandas as pandera

MarketFeaturesSchema = pandera.DataFrameSchema(
    {
        "date": pandera.Column("datetime64[ns]"),
        "open": pandera.Column(float, nullable=True, required=False),
        "high": pandera.Column(float, nullable=True, required=False),
        "low": pandera.Column(float, nullable=True, required=False),
        "close": pandera.Column(float),
        "volume": pandera.Column(float),
        "source": pandera.Column(str),
        "market_log_return": pandera.Column(float, nullable=True),
        "market_simple_return": pandera.Column(float, nullable=True),
        "realized_vol_20d": pandera.Column(float, nullable=True),
        "rolling_max_252": pandera.Column(float, nullable=True),
        "drawdown": pandera.Column(float, nullable=True),
        "liquidity_20d": pandera.Column(float, nullable=True),
        "split": pandera.Column(
            str, pandera.Check.isin(["train", "validation", "test", "out_of_scope"])
        ),
    },
    unique=["date"],
    coerce=True,
)
