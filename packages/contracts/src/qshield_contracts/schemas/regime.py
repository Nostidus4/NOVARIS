# Đỗ Ngọc Tân - schema regime_daily.parquet: 1 dòng/ngày + 3 xác suất trạng thái. Phối hợp Nguyễn Anh Tú.
"""Schema `regime_daily.parquet` — SPEC ĐI TRƯỚC, `packages/ai/regime/` còn là scaffold nên chưa có
code thật để đối chiếu. Bám theo `docs/architecture/data_contracts.md` §4.3 và CLAUDE.md quy tắc 7.

`state_id` là state thô HMM trả về (0/1/2, thứ tự ngẫu nhiên tùy seed) — CHỈ để trace/debug, KHÔNG
được dùng để suy ra tên trạng thái. `regime` là nhãn đã gán THEO ĐẶC TRƯNG THỐNG KÊ (return/
volatility/drawdown) sau khi fit — đây mới là cột downstream (`packages/risk`, dashboard) được dùng.
"""

from __future__ import annotations

import pandera.pandas as pandera

from qshield_contracts.enums import RegimeName

RegimeDailySchema = pandera.DataFrameSchema(
    {
        "date": pandera.Column("datetime64[ns]"),
        "state_id": pandera.Column(int, pandera.Check.isin([0, 1, 2])),
        "regime": pandera.Column(
            str, pandera.Check.isin([e.value for e in RegimeName])
        ),
        "prob_normal": pandera.Column(float, pandera.Check.in_range(0, 1)),
        "prob_volatile": pandera.Column(float, pandera.Check.in_range(0, 1)),
        "prob_stress": pandera.Column(float, pandera.Check.in_range(0, 1)),
        "model_version": pandera.Column(str),
        "seed": pandera.Column(int),
    },
    unique=["date"],
    coerce=True,
)


def check_probabilities_sum_to_one(
    df: pandera.typing.DataFrame, tolerance: float = 1e-6
) -> None:
    """Check bổ sung không nhét được vào `DataFrameSchema` cột-độc-lập: tổng 3 xác suất phải ≈ 1.0.

    Gọi riêng sau `RegimeDailySchema.validate(...)` (hoặc `validate_or_raise`), vì pandera
    column-level check không so sánh được nhiều cột với nhau trong một `Check` đơn giản.
    """
    total = df["prob_normal"] + df["prob_volatile"] + df["prob_stress"]
    bad = (total - 1.0).abs() > tolerance
    if bad.any():
        raise ValueError(
            f"prob_normal + prob_volatile + prob_stress phải ≈ 1.0 — {int(bad.sum())} dòng vi phạm."
        )
