# Đỗ Ngọc Tân - test ActionEffectsSchema/PairwiseEffectsSchema (spec đi trước packages/risk).
import pandas as pd
import pandera.pandas as pandera
import pytest
from qshield_contracts.schemas.risk import (
    ActionEffectsSchema,
    BaselineRisk,
    PairwiseEffectsSchema,
)


def test_baseline_risk_dataclass_holds_fields() -> None:
    baseline = BaselineRisk(
        var_0=0.03, cvar_0=0.05, portfolio_weights={"ACB": 0.5, "FPT": 0.5}, alpha=0.95
    )
    assert baseline.cvar_0 == 0.05
    assert sum(baseline.portfolio_weights.values()) == 1.0


def test_valid_action_effects_passes() -> None:
    df = pd.DataFrame(
        {
            "action_id": [0, 1],
            "ticker": ["ACB", "FPT"],
            "g": [0.01, 0.02],
            "c": [0.001, 0.002],
        }
    )
    validated = ActionEffectsSchema.validate(df)
    assert len(validated) == 2


def test_negative_cost_fails() -> None:
    df = pd.DataFrame({"action_id": [0], "ticker": ["ACB"], "g": [0.01], "c": [-0.001]})
    with pytest.raises(pandera.errors.SchemaError):
        ActionEffectsSchema.validate(df)


def test_valid_pairwise_effects_passes() -> None:
    df = pd.DataFrame({"action_i": [0, 0], "action_j": [1, 2], "C_ij": [0.001, 0.002]})
    validated = PairwiseEffectsSchema.validate(df)
    assert len(validated) == 2


def test_duplicate_action_pair_fails() -> None:
    df = pd.DataFrame({"action_i": [0, 0], "action_j": [1, 1], "C_ij": [0.001, 0.002]})
    with pytest.raises(pandera.errors.SchemaError):
        PairwiseEffectsSchema.validate(df)
