# Đỗ Ngọc Tân - test EligibilitySchema khớp cột thật của qshield_data.eligibility.
import pandas as pd
import pandera.pandas as pandera
import pytest
from qshield_contracts.schemas.eligibility import EligibilitySchema


def _valid_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2016-01-04", "2016-01-05"]),
            "ticker": ["ACB", "ACB"],
            "eligible_flag": [False, False],
            "reason_code": ["INSUFFICIENT_HISTORY", "INSUFFICIENT_HISTORY"],
            "sessions_available": [1, 2],
            "coverage_pct": [1.0, 1.0],
            "avg_turnover_20d": [float("nan"), float("nan")],
        }
    )


def test_valid_eligibility_passes() -> None:
    validated = EligibilitySchema.validate(_valid_df())
    assert len(validated) == 2


def test_invalid_reason_code_fails() -> None:
    df = _valid_df()
    df.loc[0, "reason_code"] = "MADE_UP_REASON"
    with pytest.raises(pandera.errors.SchemaError):
        EligibilitySchema.validate(df)


def test_negative_sessions_available_fails() -> None:
    df = _valid_df()
    df.loc[0, "sessions_available"] = -1
    with pytest.raises(pandera.errors.SchemaError):
        EligibilitySchema.validate(df)
