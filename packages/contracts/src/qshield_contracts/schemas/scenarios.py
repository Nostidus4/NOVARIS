# Đỗ Ngọc Tân - schema stress_scenarios.npz: tensor (S, H, N). Phối hợp Nguyễn Anh Tú.
"""Schema `stress_scenarios.npz` + sidecar metadata.

Tensor `(num_scenarios, horizon_days, n_assets)`, không phải bảng — không dùng pandera. Kèm
`ScenarioMetadata` (sidecar JSON) để biết seed, regime điều kiện hóa và validation battery.

`num_scenarios` theo profile: demo_fast thường 500; workflow_update dev 2000 / final 5000
(Decision-package TL-005). `n_assets` theo universe/eligibility tại evaluation date (8 hoặc 30).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ScenarioMetadata:
    seed: int
    regime_conditioned_on: str  # giá trị của RegimeName tại ngày sinh kịch bản
    block_length: int
    num_scenarios: int
    horizon_days: int  # 20 (đã khóa)
    n_assets: int
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
