"""Focused tests for the generic four-level workflow branch."""

import itertools

import numpy as np
import pandas as pd
import pytest
from qshield_quantum.formulation.four_level import (
    decode_action_levels,
    encode_action_levels,
    four_level_bitstring,
    four_level_variable_names,
)
from qshield_quantum.formulation.surrogate import (
    QuadraticSurrogate,
    fit_quadratic_surrogate,
    quadratic_feature_count,
    structured_samples_to_arrays,
)
from qshield_quantum.solvers.exact import solve_quadratic_exact
from qshield_quantum.verify.consistency import verify_quadratic_consistency
from qshield_quantum.workflow import (
    FOUR_LEVEL_MODE,
    candidate_order_from_handoff,
    make_four_level_feasibility,
    validate_four_level_profile,
)


def _linear_model(dimension: int) -> QuadraticSurrogate:
    return QuadraticSurrogate(
        Q=np.zeros((dimension, dimension)),
        linear=-np.arange(1, dimension + 1, dtype=float),
        constant=3.0,
        residual_sum_squares=0.0,
        rank=quadratic_feature_count(dimension),
        sample_count=quadratic_feature_count(dimension),
    )


def test_four_level_codec_uses_profile_mapping() -> None:
    levels = [0, 10, 20, 30]
    assert four_level_bitstring(levels) == "00100111"
    assert encode_action_levels(levels).tolist() == [0, 0, 1, 0, 0, 1, 1, 1]
    assert decode_action_levels("00100111").tolist() == levels


def test_four_level_codec_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="Action levels"):
        encode_action_levels([5])
    with pytest.raises(ValueError, match="even bit count"):
        decode_action_levels("101")


def test_surrogate_recovers_quadratic_samples_from_bitstrings() -> None:
    dimension = 4
    Z = np.array(list(itertools.product([0, 1], repeat=dimension)), dtype=int)
    truth = QuadraticSurrogate(
        Q=np.array(
            [
                [0.0, 0.5, 0.0, -0.25],
                [0.5, 0.0, 0.75, 0.0],
                [0.0, 0.75, 0.0, 0.125],
                [-0.25, 0.0, 0.125, 0.0],
            ]
        ),
        linear=np.array([1.0, -2.0, 0.5, 3.0]),
        constant=-4.0,
        residual_sum_squares=0.0,
        rank=11,
        sample_count=16,
    )
    frame = pd.DataFrame(
        {
            "bitstring": ["".join(map(str, row)) for row in Z],
            "objective": truth.evaluate_batch(Z),
        }
    )
    bits, targets, target = structured_samples_to_arrays(frame, ["AAA", "BBB"])
    fitted = fit_quadratic_surrogate(bits, targets)
    assert target == "objective"
    np.testing.assert_allclose(
        fitted.evaluate_batch(Z), truth.evaluate_batch(Z), atol=1e-10
    )
    assert fitted.rank == quadratic_feature_count(dimension)


def test_surrogate_requires_full_rank_structured_samples() -> None:
    Z = np.zeros((11, 4), dtype=int)
    with pytest.raises(ValueError, match="rank deficient"):
        fit_quadratic_surrogate(Z, np.zeros(11))


def test_generic_consistency_matches_all_three_paths() -> None:
    model = _linear_model(6)
    verify_quadratic_consistency(
        model, variable_names=four_level_variable_names(["A", "B", "C"]), chunk_size=17
    )


def test_chunked_exact_evaluates_all_16_bit_states_without_energy_dict() -> None:
    model = _linear_model(16)
    result = solve_quadratic_exact(model, chunk_size=4096, top_n=7)
    assert result.evaluated_states == 65_536
    assert result.feasible_states == 65_536
    assert result.best_feasible_bitstring == "1" * 16
    assert len(result.top_feasible_candidates) == 7
    assert not hasattr(result, "all_energies")


@pytest.mark.slow
def test_chunked_exact_evaluates_optional_20_bit_reference() -> None:
    model = _linear_model(20)
    result = solve_quadratic_exact(model, chunk_size=65_536, top_n=3)
    assert result.evaluated_states == 1_048_576
    assert result.best_feasible_bitstring == "1" * 20


def test_generic_feasibility_and_profile_boundary() -> None:
    profile = {
        "quantum": {
            "mode": FOUR_LEVEL_MODE,
            "input_candidates": 2,
            "action_levels_pct": [0, 10, 20, 30],
            "bit_encoding": {"bits_per_asset": 2},
        }
    }
    assert validate_four_level_profile(profile)["input_candidates"] == 2
    predicate = make_four_level_feasibility(
        {"max_active_candidates": 1, "max_total_action_pct": 20}
    )
    assert predicate(encode_action_levels([20, 0]))
    assert not predicate(encode_action_levels([20, 10]))
    assert not predicate(encode_action_levels([30, 0]))

    candidates = pd.DataFrame(
        {
            "ticker": ["B", "A", "X"],
            "rank": [2, 1, 3],
            "selected_top10": [True, True, False],
        }
    )
    assert candidate_order_from_handoff(candidates, expected_candidates=2) == ["A", "B"]
