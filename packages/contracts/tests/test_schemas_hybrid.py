import pandas as pd
import pytest
from qshield_contracts.enums import Stage
from qshield_contracts.hashing import effective_action_hash, stable_hash
from qshield_contracts.paths import ArtifactPaths
from qshield_contracts.schemas.hybrid import (
    manifest_instances_hash,
    validate_candidate_pool,
    validate_hybrid_manifest,
    validate_polish_trace,
    validate_qaoa_distribution,
    validate_track_results,
)


def _pool_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "experiment_id": "exp",
        "instance_id": "i1",
        "track": "qaoa",
        "view": "candidate_budget",
        "source_method": "qaoa_seed",
        "source_seed": 101,
        "source_rank": 1,
        "raw_probability": 0.5,
        "qubo_energy": -1.0,
        "bitstring": "1001",
        "effective_action_hash": effective_action_hash([10, 20]),
        "predicate_feasible": True,
        "true_objective": 0.3,
        "true_feasible": True,
        "candidate_order_hash": "order",
        "qubo_hash": "qubo",
    }
    row.update(overrides)
    return row


def _distribution_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "experiment_id": "exp",
        "instance_id": "i1",
        "track": "qaoa",
        "seed": 101,
        "bitstring": "1001",
        "qubo_energy": -1.0,
        "probability": 0.25,
        "measured_count": 8,
        "predicate_feasible": True,
        "shots": 32,
        "reps": 1,
        "optimizer": "COBYLA",
        "maxiter": 10,
        "backend": "StatevectorSampler",
        "warm_start": False,
        "transpiled": True,
        "candidate_order_hash": "order",
        "qubo_hash": "qubo",
    }
    row.update(overrides)
    return row


def _polish_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "experiment_id": "exp",
        "instance_id": "i1",
        "track": "qaoa",
        "view": "candidate_budget",
        "start_rank": 1,
        "start_bitstring": "1001",
        "start_true_objective": 0.5,
        "final_true_objective": 0.4,
        "objective_improvement": 0.1,
        "true_objective_evaluations": 12,
        "iterations": 2,
        "wall_seconds": 0.01,
        "active_set_changed": False,
        "zero_action_lock_respected": True,
        "max_adjustment_respected": True,
        "stop_reason": "converged",
        "final_feasible": True,
    }
    row.update(overrides)
    return row


def test_stage_hybrid_has_own_directory() -> None:
    paths = ArtifactPaths({"artifacts": {"mode": "dev", "root": "artifacts"}})
    assert paths.stage_dir(Stage.HYBRID).name == "hybrid"


def test_effective_action_hash_rounds_codec_noise() -> None:
    assert effective_action_hash([30.000000000004, 0.0]) == effective_action_hash(
        [30, 0]
    )
    assert effective_action_hash([10, 20]) != effective_action_hash([20, 10])
    assert stable_hash({"b": 1, "a": 2}) == stable_hash({"a": 2, "b": 1})


def test_candidate_pool_rejects_exact_contamination() -> None:
    frame = pd.DataFrame([_pool_row(source_method="exact_top_k")])
    with pytest.raises(ValueError, match="exact contamination"):
        validate_candidate_pool(frame, bit_count=4)
    reference = pd.DataFrame(
        [_pool_row(track="exact_reference", view="reference", source_method="exact")]
    )
    assert len(validate_candidate_pool(reference, bit_count=4)) == 1


def test_candidate_pool_rejects_duplicate_effective_action_in_track() -> None:
    frame = pd.DataFrame([_pool_row(), _pool_row(source_rank=2)])
    with pytest.raises(ValueError, match="duplicate effective actions"):
        validate_candidate_pool(frame, bit_count=4)
    other_track = pd.DataFrame([_pool_row(), _pool_row(track="random_uniform")])
    assert len(validate_candidate_pool(other_track, bit_count=4)) == 2


def test_candidate_pool_rejects_mixed_hash_and_bad_length() -> None:
    with pytest.raises(ValueError, match="mixed qubo_hash"):
        validate_candidate_pool(
            pd.DataFrame(
                [
                    _pool_row(),
                    _pool_row(
                        bitstring="0110", effective_action_hash="x", qubo_hash="other"
                    ),
                ]
            ),
            bit_count=4,
        )
    with pytest.raises(ValueError, match="length"):
        validate_candidate_pool(pd.DataFrame([_pool_row(bitstring="10")]), bit_count=4)


def test_qaoa_distribution_requires_lossless_probability_mass() -> None:
    rows = [
        _distribution_row(bitstring="1001", probability=0.75, measured_count=24),
        _distribution_row(bitstring="0000", probability=0.25, measured_count=8),
    ]
    assert len(validate_qaoa_distribution(pd.DataFrame(rows), bit_count=4)) == 2
    with pytest.raises(ValueError, match="not lossless"):
        validate_qaoa_distribution(pd.DataFrame(rows[:1]), bit_count=4)


def test_polish_trace_rejects_active_set_change_and_bad_improvement() -> None:
    assert len(validate_polish_trace(pd.DataFrame([_polish_row()]))) == 1
    with pytest.raises(ValueError, match="active_set_changed"):
        validate_polish_trace(pd.DataFrame([_polish_row(active_set_changed=True)]))
    with pytest.raises(ValueError, match="objective_improvement"):
        validate_polish_trace(pd.DataFrame([_polish_row(objective_improvement=0.2)]))
    with pytest.raises(ValueError, match="zero_action_lock"):
        validate_polish_trace(
            pd.DataFrame([_polish_row(zero_action_lock_respected=False)])
        )


def test_track_results_budget_consistency() -> None:
    row = {
        "experiment_id": "exp",
        "instance_id": "i1",
        "track": "qaoa",
        "view": "candidate_budget",
        "status": "SHORTFALL",
        "budget_candidates": 10,
        "generated_unique": 7,
        "shortfall": 3,
        "true_evaluations_generation": 7,
        "true_evaluations_polish": 20,
        "raw_best_true_objective": 0.4,
        "polished_best_true_objective": 0.3,
        "generation_seconds": 1.0,
        "polish_seconds": 0.1,
    }
    assert len(validate_track_results(pd.DataFrame([row]))) == 1
    with pytest.raises(ValueError, match="generated_unique"):
        validate_track_results(pd.DataFrame([{**row, "shortfall": 0}]))


def test_manifest_hash_locks_instances() -> None:
    instances = [
        {
            "instance_id": "c01",
            "as_of_date": "2024-03-01",
            "target_regime": "volatile",
            "portfolio_id": "diversified",
            "scenario_seed": 1,
            "set": "confirmation",
        }
    ]
    manifest = {
        "experiment_id": "hybrid_v1",
        "status": "CONFIRMATION_NON_BASELINE",
        "selection_rule": {"min_gap_sessions": 20},
        "instances": instances,
        "instances_hash": manifest_instances_hash(instances),
    }
    validate_hybrid_manifest(manifest)
    tampered = {**manifest, "instances": [{**instances[0], "as_of_date": "2024-03-04"}]}
    with pytest.raises(ValueError, match="edited after it was locked"):
        validate_hybrid_manifest(tampered)
    with pytest.raises(ValueError, match="status"):
        validate_hybrid_manifest({**manifest, "status": "BASELINE"})
