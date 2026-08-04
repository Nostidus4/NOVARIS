# Nguyễn Anh Tú - dự phòng khi HMM không hội tụ hoặc không có ý nghĩa kinh tế.
"""Nhãn regime theo ngưỡng — dự phòng khi cổng HMM fail (PR-REG-014).

AD-07: fallback CHỈ sinh nhãn, TUYỆT ĐỐI không sinh cột xác suất. `RegimeDailySchema` bắt buộc ba
cột xác suất non-null, nên một run fallback ghi 1.0/0.0 vào đó sẽ trông y hệt một xác suất đã
hiệu chỉnh. Vì vậy fallback ghi ra artifact RIÊNG (`regime_daily_rule_based.parquet`) với hình dạng
của riêng nó, và chặn chặng scenarios (PR-REG-015).

Ngưỡng volatility lấy từ phân vị trên DÒNG TRAIN (quy tắc 4) — ngày test biến động cực đại không
được phép làm dịch ngưỡng.

Luật (PROVISIONAL, `configs/regime.yaml: fallback`, chờ Ngọc/Phúc duyệt):
    stress   ⇐ volatility >= q(train) VÀ drawdown <= ngưỡng
    volatile ⇐ volatility >= q(train)
    normal   ⇐ còn lại
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from qshield_contracts.enums import RegimeName

RULE_BASED_METHOD = "rule_based"

_TRAIN_SPLIT = "train"
_STRESS_RULE = "vol>=q AND drawdown<=threshold"
_VOLATILE_RULE = "vol>=q"
_DEFAULT_RULE = "default"


def rule_based_labels(
    raw_frame: pd.DataFrame,
    *,
    volatility_column: str,
    drawdown_column: str,
    vol_quantile: float,
    drawdown_threshold: float,
) -> pd.DataFrame:
    """`date, regime, rule_fired, method` — KHÔNG có cột xác suất, theo thiết kế."""
    if not 0.0 < vol_quantile < 1.0:
        raise ValueError(f"vol_quantile phải nằm trong (0,1), nhận {vol_quantile}.")
    train = raw_frame.loc[raw_frame["split"] == _TRAIN_SPLIT, volatility_column]
    if train.empty:
        raise ValueError(
            "Không có dòng split=='train' để tính ngưỡng volatility của fallback "
            "trong rule_based_labels (qshield_ai.baseline.rule_based_regime)."
        )
    threshold = float(np.quantile(train.to_numpy(dtype=float), vol_quantile))

    volatility = raw_frame[volatility_column].to_numpy(dtype=float)
    drawdown = raw_frame[drawdown_column].to_numpy(dtype=float)
    is_high_volatility = volatility >= threshold
    is_deep_drawdown = drawdown <= drawdown_threshold

    regime = np.where(
        is_high_volatility & is_deep_drawdown,
        RegimeName.STRESS.value,
        np.where(
            is_high_volatility, RegimeName.VOLATILE.value, RegimeName.NORMAL.value
        ),
    )
    rule_fired = np.where(
        is_high_volatility & is_deep_drawdown,
        _STRESS_RULE,
        np.where(is_high_volatility, _VOLATILE_RULE, _DEFAULT_RULE),
    )
    return pd.DataFrame(
        {
            "date": raw_frame["date"].to_numpy(),
            "regime": regime,
            "rule_fired": rule_fired,
            "method": RULE_BASED_METHOD,
        }
    )
