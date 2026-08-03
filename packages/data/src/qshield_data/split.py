# Nguyễn Đỗ Minh Anh - TimeSeriesSplit; scaler fit CHỈ trên train, transform cho validation/test.
"""Gán train/validation/test split — port từ `CLEAN.ipynb` ("TIME SPLITS").

"2 đồng hồ": market-level (dùng cho HMM regime, `packages/ai`) và asset-level (scenarios/CVaR/QUBO)
có `train_start`/`train_end` khác nhau — asset-level bắt đầu muộn hơn để có coverage tốt hơn giữa
các mã trong universe đã chốt (xem `configs/data.yaml` `date_range`). validation/test dùng chung.

Đây chỉ gán NHÃN split theo mốc thời gian đã khóa — không phải fit/transform scaler (đó là việc
của consumer, ví dụ `packages/ai`, và PHẢI fit CHỈ trên phần được gán `"train"` ở đây).
"""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd

Level = Literal["market", "asset"]


def assign_split(dt: pd.Timestamp, level: Level, splits_config: dict[str, Any]) -> str:
    """Trả `"train" | "validation" | "test" | "out_of_scope"` cho một ngày `dt`.

    `splits_config` là `configs/data.yaml["date_range"]` đã parse — cần các key
    `{level}_train_start`, `{level}_train_end`, `validation_start`, `validation_end`, `test_start`,
    `test_end`.
    """
    train_start = pd.to_datetime(splits_config[f"{level}_train_start"])
    train_end = pd.to_datetime(splits_config[f"{level}_train_end"])
    val_start = pd.to_datetime(splits_config["validation_start"])
    val_end = pd.to_datetime(splits_config["validation_end"])
    test_start = pd.to_datetime(splits_config["test_start"])
    test_end = pd.to_datetime(splits_config["test_end"])

    dt = pd.to_datetime(dt)
    if train_start <= dt <= train_end:
        return "train"
    if val_start <= dt <= val_end:
        return "validation"
    if test_start <= dt <= test_end:
        return "test"
    return "out_of_scope"


def apply_splits(
    df: pd.DataFrame, level: Level, splits_config: dict[str, Any]
) -> pd.DataFrame:
    """Thêm cột `split` cho `df` (cần cột `date`) dựa trên `assign_split`.

    Raise `ValueError` nếu train/validation/test overlap nhau (không nên xảy ra với mốc thời gian
    hợp lệ, nhưng kiểm tra tường minh thay vì im lặng tin config — PR-DAT-013).
    """
    out = df.copy()
    out["split"] = out["date"].apply(lambda d: assign_split(d, level, splits_config))

    ranges = {
        "train": (
            pd.to_datetime(splits_config[f"{level}_train_start"]),
            pd.to_datetime(splits_config[f"{level}_train_end"]),
        ),
        "validation": (
            pd.to_datetime(splits_config["validation_start"]),
            pd.to_datetime(splits_config["validation_end"]),
        ),
        "test": (
            pd.to_datetime(splits_config["test_start"]),
            pd.to_datetime(splits_config["test_end"]),
        ),
    }
    names = list(ranges)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            a_start, a_end = ranges[a]
            b_start, b_end = ranges[b]
            if a_start <= b_end and b_start <= a_end:
                raise ValueError(
                    f"Split '{a}' ({a_start.date()}–{a_end.date()}) và '{b}' "
                    f"({b_start.date()}–{b_end.date()}) overlap"
                )
    return out
