from __future__ import annotations

from typing import Any

import numpy as np
from qshield_risk.objective import COMPONENT_NAMES
from qshield_risk.sampling import sample_objective_dataset


def _config() -> dict[str, Any]:
    return {
        "cvar_alpha": 0.95,
        "robustness_confidence_levels": [],
        "horizon_days": 1,
        "weight_sum_tolerance": 1e-10,
        "maximum_reduction": 0.30,
        "target_cash_increment": 0.0,
        "transaction_cost": {"fee": 0.0, "spread": 0.0, "liquidity_penalty": 0.0},
        "financial_objective": {
            "components": {
                name: {"weight": 1.0 if name == "cvar" else 0.0, "scale": 1.0}
                for name in COMPONENT_NAMES
            }
        },
        "objective_sampling": {
            "policy_version": "test-v1",
            "train_random_count": 2,
            "validation_count": 1,
            "holdout_count": 2,
            "chunk_size": 2,
            "seeds": {"train": 11, "validation": 22, "holdout": 33},
        },
    }


def test_objective_splits_are_unique_reproducible_and_generic_in_m() -> None:
    cube = np.zeros((40, 1, 2))
    tickers = ("AAA", "BBB")
    weights = {"AAA": 0.5, "BBB": 0.5}
    first = sample_objective_dataset(cube, tickers, weights, 0.0, tickers, _config())
    second = sample_objective_dataset(cube, tickers, weights, 0.0, tickers, _config())
    assert len(first.train) == 1 + 4 + 6 + 2
    assert len(first.validation) == 1
    assert len(first.holdout) == 2
    all_sets = [set(frame["bitstring"]) for frame in (first.train, first.validation, first.holdout)]
    assert not all_sets[0] & all_sets[1]
    assert not all_sets[0] & all_sets[2]
    assert not all_sets[1] & all_sets[2]
    assert first.manifest == second.manifest
    assert first.train["bitstring"].tolist() == second.train["bitstring"].tolist()
    assert set(first.train["cash_bucket"]) <= {"low", "medium", "high"}
    assert first.manifest["overlap_count"] == 0


def test_underfill_with_exhaustive_bitspace_is_disclosed_not_crashed() -> None:
    config = _config()
    config["objective_sampling"] = {
        **config["objective_sampling"],
        "train_random_count": 500,
        "validation_count": 500,
        "holdout_count": 1_000,
    }
    dataset = sample_objective_dataset(
        np.zeros((40, 1, 1)),
        ("AAA",),
        {"AAA": 1.0},
        0.0,
        ("AAA",),
        config,
    )

    assert len(dataset.train) == 4  # The structured design exhausts all two-bit states.
    assert dataset.validation.empty
    assert dataset.holdout.empty
    assert dataset.manifest["sampling_truncated"] is True
    assert dataset.manifest["sampling_warning"] == (
        "INSUFFICIENT_STATE_SPACE_FOR_REQUESTED_SPLITS"
    )
