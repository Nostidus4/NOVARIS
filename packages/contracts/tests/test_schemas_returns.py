# Đỗ Ngọc Tân - test ReturnsSchema khớp cột thật của qshield_data.returns + split.
import pandas as pd
import pandera.pandas as pandera
import pytest
from qshield_contracts.schemas.returns import ReturnsSchema


def _valid_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2016-01-04", "2016-01-05"]),
            "ticker": ["ACB", "ACB"],
            "open": [2710.0, 2680.0],
            "high": [2710.0, 2680.0],
            "low": [2680.0, 2640.0],
            "close": [2690.0, 2650.0],
            "adjusted_close": [2690.0, 2650.0],
            "volume": [36439, 47676],
            "source_id": ["DNSE_PRICES", "DNSE_PRICES"],
            "data_version": ["v1.0.0", "v1.0.0"],
            "quality_flag": ["OK", "OK"],
            "turnover_value": [98020910.0, 126341400.0],
            "prev_adj": [float("nan"), 2690.0],
            "simple_return": [float("nan"), -0.014870],
            "log_return": [float("nan"), -0.014982],
            "split": ["train", "train"],
        }
    )


def test_valid_returns_passes() -> None:
    validated = ReturnsSchema.validate(_valid_df())
    assert len(validated) == 2


def test_negative_price_fails() -> None:
    df = _valid_df()
    df.loc[0, "adjusted_close"] = -1.0
    with pytest.raises(pandera.errors.SchemaError):
        ReturnsSchema.validate(df)


def test_invalid_split_label_fails() -> None:
    df = _valid_df()
    df.loc[0, "split"] = "bogus"
    with pytest.raises(pandera.errors.SchemaError):
        ReturnsSchema.validate(df)


def test_duplicate_date_ticker_fails() -> None:
    df = _valid_df()
    df.loc[1, "date"] = df.loc[0, "date"]
    with pytest.raises(pandera.errors.SchemaError):
        ReturnsSchema.validate(df)
