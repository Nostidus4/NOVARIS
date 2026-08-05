import numpy as np
import pytest
from qshield_risk.metrics import conditional_value_at_risk, value_at_risk


@pytest.mark.parametrize(
    ("alpha", "expected_var", "expected_cvar", "expected_count"),
    [
        (0.95, 95.05, 98.0, 5),
        (0.975, 97.525, 99.0, 3),
        (0.99, 99.01, 100.0, 1),
    ],
)
def test_var_cvar_and_tail_count_by_hand(
    alpha: float, expected_var: float, expected_cvar: float, expected_count: int
) -> None:
    losses = np.arange(1.0, 101.0)
    var, cvar, count = conditional_value_at_risk(losses, alpha)
    assert var == pytest.approx(expected_var)
    assert cvar == pytest.approx(expected_cvar)
    assert count == expected_count


def test_all_observations_tied_at_var_are_included() -> None:
    losses = np.array([0.0] * 96 + [1.0] * 4)
    var, cvar, count = conditional_value_at_risk(losses, 0.95)
    assert var == 0.0
    assert cvar == pytest.approx(0.04)
    assert count == 100


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, np.nan])
def test_invalid_alpha_is_rejected(alpha: float) -> None:
    with pytest.raises(ValueError, match="alpha"):
        value_at_risk([0.0, 1.0], alpha)


def test_non_finite_losses_are_rejected() -> None:
    with pytest.raises(ValueError, match="NaN or infinite"):
        conditional_value_at_risk([0.0, np.inf], 0.95)
