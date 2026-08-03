# Đỗ Ngọc Tân - schema eligibility_daily.parquet: 1 dòng/(date, ticker) — file mới, xem plan-contracts.md §3.3.
"""Schema `eligibility_daily.parquet` — artifact thứ 3 của chặng Data, khớp cột thật do
`qshield_data.eligibility.build_eligibility` sinh ra (xem
`packages/data/src/qshield_data/eligibility.py`).

Chưa có trong `docs/architecture/data_contracts.md` §3 (bảng đó chỉ liệt kê `returns`/`features`) —
thêm ở đây vì `packages/data` đã thực sự sinh ra artifact này; cần cập nhật lại doc đó ở một PR
review riêng (không phải phạm vi code của package này).
"""

from __future__ import annotations

import pandera.pandas as pandera

EligibilitySchema = pandera.DataFrameSchema(
    {
        "date": pandera.Column("datetime64[ns]"),
        "ticker": pandera.Column(str),
        "eligible_flag": pandera.Column(bool),
        "reason_code": pandera.Column(
            str,
            pandera.Check.isin(
                [
                    "OK",
                    "NOT_LISTED_AT_DATE",
                    "INSUFFICIENT_HISTORY",
                    "LOW_COVERAGE",
                    "SUSPENDED_OR_NO_DATA",
                    "LOW_LIQUIDITY",
                ]
            ),
        ),
        "sessions_available": pandera.Column(int, pandera.Check.ge(0)),
        "coverage_pct": pandera.Column(float),
        "avg_turnover_20d": pandera.Column(float, nullable=True),
    },
    unique=["date", "ticker"],
    coerce=True,
)
