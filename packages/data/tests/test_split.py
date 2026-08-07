# Nguyễn Đỗ Minh Anh - test assign_split/apply_splits: 2 đồng hồ market/asset, không overlap.
import pandas as pd
import pytest
from qshield_data.split import apply_splits, assign_split

_SPLITS_CONFIG = {
    "market_train_start": "2016-01-01",
    "market_train_end": "2022-12-31",
    "asset_train_start": "2016-01-01",
    "asset_train_end": "2022-12-31",
    "validation_start": "2023-01-01",
    "validation_end": "2023-12-31",
    "test_start": "2024-01-01",
    "test_end": "2026-07-31",
}


@pytest.mark.parametrize(
    "level,dt,expected",
    [
        ("market", "2016-01-01", "train"),  # đầu train market
        ("asset", "2016-06-01", "train"),
        ("asset", "2016-01-01", "train"),  # đầu train asset (TL-003)
        ("market", "2023-06-15", "validation"),
        ("asset", "2025-01-01", "test"),
        ("market", "2027-01-01", "out_of_scope"),  # sau test_end
    ],
)
def test_assign_split(level: str, dt: str, expected: str) -> None:
    assert assign_split(pd.Timestamp(dt), level, _SPLITS_CONFIG) == expected


def test_apply_splits_adds_column_and_no_overlap() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2020-01-01", "2023-06-01", "2025-01-01", "2027-01-01"]
            )
        }
    )
    out = apply_splits(df, level="market", splits_config=_SPLITS_CONFIG)

    assert list(out["split"]) == ["train", "validation", "test", "out_of_scope"]


def test_apply_splits_raises_on_overlap() -> None:
    bad_config = dict(
        _SPLITS_CONFIG, market_train_end="2023-06-01"
    )  # đè lên validation
    df = pd.DataFrame({"date": pd.to_datetime(["2023-03-01"])})

    with pytest.raises(ValueError):
        apply_splits(df, level="market", splits_config=bad_config)
