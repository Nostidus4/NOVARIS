# Đỗ Ngọc Tân - test MarketFeaturesSchema: open/high/low required=False (nhánh custom-composite).
import pandas as pd
import pandera.pandas as pandera
import pytest
from qshield_contracts.schemas.features import MarketFeaturesSchema


def _with_index_columns() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
            "open": [1000.0, 1001.0],
            "high": [1005.0, 1006.0],
            "low": [995.0, 996.0],
            "close": [1000.0, 1001.0],
            "volume": [1_000_000.0, 1_100_000.0],
            "source": ["vnstock_VCI_VNINDEX", "vnstock_VCI_VNINDEX"],
            "market_log_return": [float("nan"), 0.001],
            "market_simple_return": [float("nan"), 0.001],
            "realized_vol_20d": [float("nan"), float("nan")],
            "rolling_max_252": [float("nan"), float("nan")],
            "drawdown": [float("nan"), float("nan")],
            "liquidity_20d": [float("nan"), float("nan")],
            "split": ["train", "train"],
        }
    )


def test_valid_with_index_columns_passes() -> None:
    validated = MarketFeaturesSchema.validate(_with_index_columns())
    assert len(validated) == 2


def test_custom_composite_without_ohl_columns_passes() -> None:
    """Nhánh fallback custom-composite không có cột open/high/low — PHẢI pass, không fail oan."""
    df = _with_index_columns().drop(columns=["open", "high", "low"])
    df["source"] = "custom_composite_ew"

    validated = MarketFeaturesSchema.validate(df)

    assert "open" not in validated.columns


def test_invalid_split_label_fails() -> None:
    df = _with_index_columns()
    df.loc[0, "split"] = "bogus"
    with pytest.raises(pandera.errors.SchemaError):
        MarketFeaturesSchema.validate(df)


def test_duplicate_date_fails() -> None:
    df = _with_index_columns()
    df.loc[1, "date"] = df.loc[0, "date"]
    with pytest.raises(pandera.errors.SchemaError):
        MarketFeaturesSchema.validate(df)
