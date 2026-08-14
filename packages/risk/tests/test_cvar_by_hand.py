import numpy as np
import pytest
from qshield_risk.metrics import (
    bootstrap_cvar_uncertainty,
    conditional_value_at_risk,
    risk_metrics_from_wealth,
    value_at_risk,
)


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


def test_bootstrap_cvar_uncertainty_is_reproducible_and_warns_on_small_tail() -> None:
    losses = np.linspace(-0.02, 0.20, 100)
    first = bootstrap_cvar_uncertainty(
        losses,
        0.99,
        bootstrap_resamples=100,
        seed=17,
        low_tail_threshold=5,
    )
    second = bootstrap_cvar_uncertainty(
        losses,
        0.99,
        bootstrap_resamples=100,
        seed=17,
        low_tail_threshold=5,
    )
    assert first == second
    assert first.lower <= first.upper
    assert first.low_tail_sample is True
    assert first.warning == "LOW_TAIL_SAMPLE"
    assert first.uncertainty_scope == "scenario_monte_carlo_only"


def test_risk_metrics_include_configured_tail_uncertainty() -> None:
    terminal_wealth = np.linspace(0.8, 1.1, 100).reshape(100, 1)
    result = risk_metrics_from_wealth(
        terminal_wealth,
        [0.95, 0.99],
        uncertainty_config={
            "tail_uncertainty": {
                "confidence_level": 0.95,
                "bootstrap_resamples": 50,
                "seed": 101,
                "low_tail_threshold": 10,
            }
        },
    )
    assert set(result.tail_uncertainty) == {"0.95", "0.99"}
    assert result.tail_uncertainty["0.99"].bootstrap_resamples == 50
