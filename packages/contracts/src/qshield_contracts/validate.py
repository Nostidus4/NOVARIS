# Đỗ Ngọc Tân - validate_or_raise() dùng ở mọi ranh giới module — fail fast, không để dữ liệu sai trôi xuống các tầng sau.
"""`validate_or_raise()` — gọi ở MỌI ranh giới module (input lẫn output, CLAUDE.md quy tắc 12).

Chỉ cover `pandera.DataFrameSchema` (artifact dạng bảng: returns/features/eligibility/regime/risk).
`scenarios` (tensor `(500,20,8)`) và `optimization` (json lồng nhau) không hợp với pandera — mỗi
schema đó tự có hàm validate riêng (`validate_scenarios`, `validate_qaoa_result` trong
`schemas/scenarios.py`/`schemas/optimization.py`), không đi qua hàm này
(plan-contracts.md §6 câu 4).
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pandera


def validate_or_raise(
    data: pd.DataFrame, schema: pandera.DataFrameSchema, *, context: str
) -> pd.DataFrame:
    """Validate `data` bằng `schema` (lazy — gom hết lỗi thay vì dừng ở lỗi đầu tiên).

    `context` là tên module/artifact gọi hàm này (vd. `"qshield_data.returns"`) — được đưa vào
    thông báo lỗi để biết ngay lỗi validate xảy ra ở đâu, không phải đoán từ traceback.
    """
    try:
        return schema.validate(data, lazy=True)
    except pandera.errors.SchemaErrors as e:
        raise ValueError(
            f"[{context}] schema validation failed:\n{e.failure_cases}"
        ) from e
