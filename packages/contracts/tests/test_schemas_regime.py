# Đỗ Ngọc Tân - test RegimeDailySchema + check_probabilities_sum_to_one (spec đi trước packages/ai).
import pandas as pd
import pandera.pandas as pandera
import pytest
from qshield_contracts.schemas.regime import (
    RegimeDailySchema,
    check_probabilities_sum_to_one,
)


def _valid_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
            "state_id": [0, 2],
            "regime": ["normal", "stress"],
            "prob_normal": [0.7, 0.1],
            "prob_volatile": [0.2, 0.2],
            "prob_stress": [0.1, 0.7],
            "model_version": ["hmm_v1", "hmm_v1"],
            "seed": [42, 42],
        }
    )


def test_valid_regime_passes() -> None:
    validated = RegimeDailySchema.validate(_valid_df())
    check_probabilities_sum_to_one(validated)  # không raise


def test_invalid_regime_label_fails() -> None:
    df = _valid_df()
    df.loc[0, "regime"] = "sideways"  # không nằm trong RegimeName
    with pytest.raises(pandera.errors.SchemaError):
        RegimeDailySchema.validate(df)


def test_probabilities_not_summing_to_one_raises() -> None:
    df = _valid_df()
    df.loc[0, "prob_normal"] = 0.5  # 0.5 + 0.2 + 0.1 = 0.8, không phải 1.0
    validated = RegimeDailySchema.validate(df)
    with pytest.raises(ValueError):
        check_probabilities_sum_to_one(validated)
