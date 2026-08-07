# Đỗ Ngọc Tân - schema stress_scenarios.npz: tensor (num_scenarios, 20, n_assets).
# Phối hợp Nguyễn Anh Tú.
"""Schema `stress_scenarios.npz` — SPEC ĐI TRƯỚC, `packages/ai/scenarios/` còn là scaffold.

Tensor `(num_scenarios, horizon_days, n_assets)`, không phải bảng — không dùng pandera. Kèm
`ScenarioMetadata` (sidecar, thường ghi cùng file `.json` cạnh `.npz`) để biết seed, regime điều
kiện hóa, và kết quả validation battery (mean/std/quantile/skew/kurtosis/tail coverage — CLAUDE.md
quy tắc 15 "Chạy verify trước khi tin" áp dụng tương tự cho scenarios: không tin tensor nếu chưa có
`validation` đi kèm).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ScenarioMetadata:
    seed: int
    regime_conditioned_on: str  # giá trị của RegimeName tại ngày sinh kịch bản
    block_length: int
    num_scenarios: int  # TL-005: dev 2.000, final ưu tiên 5.000 (2.000–4.999 cần lý do)
    horizon_days: int  # 20 (phạm vi đã khóa)
    n_assets: int  # 8 (phạm vi đã khóa)
    validation: dict[str, float]  # mean/std/quantile/skew/kurtosis/tail_coverage


def validate_scenarios(tensor: np.ndarray, meta: ScenarioMetadata) -> None:
    """Raise `ValueError` nếu shape sai hoặc tensor chứa NaN/Inf.

    Không kiểm tra tương quan chéo giữa các tài sản ở đây — đó là việc của
    `packages/ai/scenarios/validate.py` (cần toàn bộ dữ liệu lịch sử để so sánh), hàm này chỉ đảm
    bảo shape/kiểu dữ liệu đúng hợp đồng trước khi artifact được ghi ra đĩa.
    """
    expected_shape = (meta.num_scenarios, meta.horizon_days, meta.n_assets)
    if tensor.shape != expected_shape:
        raise ValueError(
            f"Scenario tensor shape {tensor.shape} != expected {expected_shape}"
        )
    if not np.isfinite(tensor).all():
        raise ValueError("Scenario tensor chứa NaN/Inf — kịch bản không hợp lệ.")
