# Đỗ Ngọc Tân - test validate_scenarios: shape (500,20,8) + không NaN/Inf (spec đi trước packages/ai).
import numpy as np
import pytest
from qshield_contracts.schemas.scenarios import ScenarioMetadata, validate_scenarios

_META = ScenarioMetadata(
    seed=42,
    regime_conditioned_on="stress",
    block_length=5,
    num_scenarios=500,
    horizon_days=20,
    n_assets=8,
    validation={"mean": 0.0, "std": 0.02},
)


def test_valid_tensor_passes() -> None:
    tensor = np.random.default_rng(0).normal(size=(500, 20, 8))
    validate_scenarios(tensor, _META)  # không raise


def test_wrong_shape_fails() -> None:
    tensor = np.zeros((100, 20, 8))
    with pytest.raises(ValueError, match="shape"):
        validate_scenarios(tensor, _META)


def test_nan_in_tensor_fails() -> None:
    tensor = np.zeros((500, 20, 8))
    tensor[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        validate_scenarios(tensor, _META)
