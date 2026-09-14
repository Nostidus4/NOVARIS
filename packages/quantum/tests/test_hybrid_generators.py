from __future__ import annotations

import json
import subprocess
import sys
import textwrap

import numpy as np
import pandas as pd
import pytest
from qshield_quantum.formulation.neighborhood import (
    candidate_bit_indices,
    condition_qubo,
    embed_bits,
)
from qshield_quantum.formulation.surrogate import QuadraticSurrogate
from qshield_quantum.generators.boltzmann_pool import boltzmann_pool, fit_beta
from qshield_quantum.generators.common import (
    bits_from_indices,
    bitstring_to_index,
    constraint_mask,
    enumerate_state_space,
    index_to_bitstring,
    levels_from_bits,
)
from qshield_quantum.generators.qaoa_pool import (
    QaoaRun,
    distribution_metrics,
    distribution_rows,
    qaoa_proposals,
    run_qaoa_seeds,
)
from qshield_quantum.generators.random_pool import stratified_pool, uniform_pool
from qshield_quantum.generators.surrogate_search import surrogate_local_search_pool
from qshield_quantum.solvers.qaoa import QaoaSample, QaoaSeedResult
from qshield_quantum.verify.hybrid_attribution import attribution_checklist
from qshield_quantum.workflow import make_four_level_feasibility

CONSTRAINTS = {"min_active_candidates": 1, "max_total_action_pct": 50}


def _model(bit_count: int = 6, seed: int = 0) -> QuadraticSurrogate:
    rng = np.random.default_rng(seed)
    Q = rng.normal(0, 0.2, (bit_count, bit_count))
    Q = (Q + Q.T) / 2
    np.fill_diagonal(Q, 0.0)
    return QuadraticSurrogate(
        Q=Q,
        linear=rng.normal(0, 1, bit_count),
        constant=0.5,
        residual_sum_squares=0.0,
        rank=1,
        sample_count=1,
    )


def test_index_codec_and_constraint_mask_match_workflow_predicate() -> None:
    indices = np.arange(64)
    bits = bits_from_indices(indices, 6)
    assert index_to_bitstring(37, 6) == "100101"
    assert bitstring_to_index("100101") == 37
    assert "".join(map(str, bits[37])) == "100101"
    levels = levels_from_bits(bits)
    predicate = make_four_level_feasibility(CONSTRAINTS)
    expected = np.array([predicate(row) for row in bits])
    np.testing.assert_array_equal(constraint_mask(levels, CONSTRAINTS), expected)


def test_state_space_energies_match_model() -> None:
    model = _model()
    space = enumerate_state_space(model, CONSTRAINTS, chunk_size=10)
    for index in (0, 5, 63):
        assert space.energies[index] == pytest.approx(
            model.evaluate(bits_from_indices(np.array([index]), 6)[0])
        )
    assert space.total_states == 64
    assert 0 < space.total_feasible_states < 64


def test_random_pools_are_feasible_unique_and_seeded() -> None:
    space = enumerate_state_space(_model(), CONSTRAINTS)
    first = uniform_pool(space, budget=12, seed=1)
    again = uniform_pool(space, budget=12, seed=1)
    other = uniform_pool(space, budget=12, seed=2)
    assert [p.bitstring for p in first] == [p.bitstring for p in again]
    assert [p.bitstring for p in first] != [p.bitstring for p in other]
    assert len({p.bitstring for p in first}) == 12
    assert all(p.predicate_feasible for p in first)
    assert (
        len(uniform_pool(space, budget=10_000, seed=1)) == space.total_feasible_states
    )
    strat = stratified_pool(space, budget=9, seed=1)
    actives = {
        int(
            np.count_nonzero(
                levels_from_bits(
                    bits_from_indices(np.array([bitstring_to_index(p.bitstring)]), 6)
                )[0]
            )
        )
        for p in strat
    }
    assert len(actives) >= 2
    assert all("exact" not in p.source_method for p in first + strat)


def test_boltzmann_fit_and_pool() -> None:
    space = enumerate_state_space(_model(), CONSTRAINTS)
    energies = space.energies[space.predicate_feasible]
    above = fit_beta(energies, float(energies.mean()) + 1.0)
    assert above.beta == 0.0 and above.status == "TARGET_ABOVE_UNIFORM"
    target = float(np.quantile(energies, 0.2))
    fit = fit_beta(energies, target)
    assert fit.status == "MATCHED"
    assert fit.achieved_mean_energy == pytest.approx(target, abs=1e-6)
    proposals, _ = boltzmann_pool(space, budget=8, seed=4, target_mean_energy=target)
    assert len({p.bitstring for p in proposals}) == 8
    assert all(p.predicate_feasible for p in proposals)


def test_surrogate_local_search_pool() -> None:
    space = enumerate_state_space(_model(), CONSTRAINTS)
    proposals, stats = surrogate_local_search_pool(space, budget=15, seed=9)
    assert len({p.bitstring for p in proposals}) == len(proposals) == 15
    assert all(p.predicate_feasible for p in proposals)
    assert stats["restarts"] >= 1


def _fake_result(
    seed: int, samples: list[tuple[str, float, int]], space, shots: int = 16
):
    distribution = tuple(
        QaoaSample(
            bitstring=bits,
            energy=float(space.energies[bitstring_to_index(bits)]) + energy_offset,
            probability=count / shots,
            feasible=bool(space.predicate_feasible[bitstring_to_index(bits)]),
            measured_count=count,
        )
        for bits, energy_offset, count in samples
    )
    return QaoaSeedResult(
        seed=seed,
        bitstring=samples[0][0],
        energy=0.0,
        feasible=True,
        feasibility_rate=1.0,
        success_prob=0.0,
        runtime_seconds=0.1,
        samples=(),
        transpiled=True,
        distribution=distribution,
    )


def test_qaoa_pool_ranking_metrics_and_dedup_across_seeds() -> None:
    space = enumerate_state_space(_model(), CONSTRAINTS)
    feasible = [
        index_to_bitstring(i, 6) for i in np.flatnonzero(space.predicate_feasible)[:3]
    ]
    infeasible = index_to_bitstring(
        int(np.flatnonzero(~space.predicate_feasible)[0]), 6
    )
    run = QaoaRun(
        results={
            101: _fake_result(
                101,
                [(feasible[0], 0, 8), (feasible[1], 0, 4), (infeasible, 0, 4)],
                space,
            ),
            202: _fake_result(202, [(feasible[1], 0, 10), (feasible[2], 0, 6)], space),
        },
        shots=16,
    )
    rows = distribution_rows(run, space)
    proposals = qaoa_proposals(rows, space, budget=10)
    assert [p.bitstring for p in proposals] == [feasible[1], feasible[0], feasible[2]]
    assert proposals[0].source_seed == 202
    assert all(
        p.predicate_feasible and "exact" not in p.source_method for p in proposals
    )
    metrics = distribution_metrics(rows, space, reference_indices={"best": 0})
    assert metrics["unique_measured"] == 4  # feasible[1] seen twice, counted once
    assert metrics["unique_predicate_feasible"] == 3
    assert metrics["total_shots"] == 32
    assert metrics["coverage_all_fraction"] == "4/64"
    assert metrics["duplicate_rate"] == pytest.approx(1 - 4 / 32)
    # Adding duplicate observations never increases unique coverage.
    doubled = distribution_metrics(rows + rows, space)
    assert doubled["unique_measured"] == metrics["unique_measured"]


def test_distribution_rows_reject_energy_mismatch() -> None:
    space = enumerate_state_space(_model(), CONSTRAINTS)
    bits = index_to_bitstring(int(np.flatnonzero(space.predicate_feasible)[0]), 6)
    run = QaoaRun(results={1: _fake_result(1, [(bits, 0.5, 16)], space)}, shots=16)
    with pytest.raises(ValueError, match="verify/consistency"):
        distribution_rows(run, space)


def test_run_qaoa_seeds_records_failures_and_timeouts() -> None:
    space = enumerate_state_space(_model(), CONSTRAINTS)
    bits = index_to_bitstring(int(np.flatnonzero(space.predicate_feasible)[0]), 6)

    def solver(_qp, *, seed, **_kwargs):
        if seed == 2:
            raise RuntimeError("simulated crash")
        return _fake_result(seed, [(bits, 0, 16)], space)

    run = run_qaoa_seeds(
        None,
        seeds=[1, 2, 3],
        shots=16,
        maxiter=1,
        reps=1,
        warm_start=False,
        feasibility_constraints=None,
        seed_timeout_seconds=1.0,
        total_timeout_seconds=None,
        solver=solver,
    )
    assert sorted(run.results) == [1, 3]
    statuses = {item["seed"]: item["status"] for item in run.attempts}
    assert statuses == {1: "completed", 2: "failed", 3: "completed"}
    timed_out = run_qaoa_seeds(
        None,
        seeds=[1, 2],
        shots=16,
        maxiter=1,
        reps=1,
        warm_start=False,
        feasibility_constraints=None,
        seed_timeout_seconds=1.0,
        total_timeout_seconds=0.0,
        solver=solver,
    )
    assert not timed_out.results
    assert {item["status"] for item in timed_out.attempts} == {"timeout"}


def test_neighborhood_conditioning_is_exact() -> None:
    model = _model(8, seed=3)
    base = np.array([1, 0, 1, 1, 0, 0, 1, 0])
    free = candidate_bit_indices([1, 3])
    assert free == [2, 3, 6, 7]
    sub = condition_qubo(model, base, free)
    for index in range(16):
        sub_bits = bits_from_indices(np.array([index]), 4)[0]
        full = embed_bits(base, free, sub_bits)
        assert sub.evaluate(sub_bits) == pytest.approx(model.evaluate(full), abs=1e-12)


def test_attribution_checklist_flags_contamination() -> None:
    common = {
        "experiment_id": "e",
        "instance_id": "i",
        "candidate_order_hash": "o",
        "qubo_hash": "q",
        "qubo_energy": 0.0,
        "predicate_feasible": True,
        "true_objective": 1.0,
        "true_feasible": True,
        "raw_probability": None,
        "source_seed": None,
        "source_rank": 1,
    }
    pools = pd.DataFrame(
        [
            {
                **common,
                "track": "qaoa",
                "view": "candidate_budget",
                "source_method": "qaoa_sample",
                "bitstring": "10",
                "effective_action_hash": "h1",
            },
            {
                **common,
                "track": "exact_reference",
                "view": "reference",
                "source_method": "exact",
                "bitstring": "10",
                "effective_action_hash": "h1",
            },
        ]
    )
    tracks = pd.DataFrame(
        [
            {
                "experiment_id": "e",
                "instance_id": "i",
                "track": "qaoa",
                "view": "candidate_budget",
                "status": "OK",
                "budget_candidates": 1,
                "generated_unique": 1,
                "shortfall": 0,
                "true_evaluations_generation": 1,
                "true_evaluations_polish": 1,
                "raw_best_true_objective": 1.0,
                "polished_best_true_objective": 1.0,
                "generation_seconds": 0.0,
                "polish_seconds": 0.0,
            }
        ]
    )
    polish = pd.DataFrame(
        columns=[
            "experiment_id",
            "instance_id",
            "track",
            "view",
            "start_rank",
            "start_bitstring",
            "start_true_objective",
            "final_true_objective",
            "objective_improvement",
            "true_objective_evaluations",
            "iterations",
            "wall_seconds",
            "active_set_changed",
            "zero_action_lock_respected",
            "max_adjustment_respected",
            "stop_reason",
            "final_feasible",
        ]
    )
    clean = attribution_checklist(
        pools, polish, tracks, bit_count=2, polish_top_k=5, polish_max_evaluations=10
    )
    assert clean["status"] == "PASS"
    assert clean["checks"]["reference_overlap_reported"]["detail"] == {
        "overlap_with_reference_top_k": {"qaoa": 1}
    }
    dirty = pools.copy()
    dirty.loc[0, "source_method"] = "exact_top20"
    report = attribution_checklist(
        dirty, polish, tracks, bit_count=2, polish_top_k=5, polish_max_evaluations=10
    )
    assert report["status"] == "FAIL"


_DISTRIBUTION_SCRIPT = textwrap.dedent(
    """
    import json, os, sys
    import numpy as np
    from qshield_quantum.formulation.qiskit_program import build_quadratic_program
    from qshield_quantum.solvers.qaoa import solve_qaoa_one_seed

    Q = np.array([[0, 0.3, 0, 0], [0.3, 0, -0.2, 0], [0, -0.2, 0, 0.1], [0, 0, 0.1, 0]])
    qp = build_quadratic_program(Q, np.array([-1.0, 0.5, -0.3, 0.2]), 0.0,
                                 ticker_order=["a", "b", "c", "d"])
    r = solve_qaoa_one_seed(qp, seed=7, shots=64, maxiter=5, feasibility=lambda b: True,
                            candidate_pool_size=2, export_full_distribution=True,
                            initial_point=[0.3, 0.4])
    payload = {
        "prob_sum": sum(s.probability for s in r.distribution),
        "count_sum": sum(s.measured_count for s in r.distribution),
        "unique": len({s.bitstring for s in r.distribution}),
        "rows": len(r.distribution),
        "top_samples": len(r.samples),
        "params": list(r.optimal_parameters),
        "evals": r.circuit_evaluations,
    }
    sys.stdout.write(json.dumps(payload)); sys.stdout.flush(); os._exit(0)
    """
)


def test_qaoa_full_distribution_is_lossless() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _DISTRIBUTION_SCRIPT],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    payload = json.loads(result.stdout)
    assert payload["prob_sum"] == pytest.approx(1.0)
    assert payload["count_sum"] == 64
    assert payload["unique"] == payload["rows"]
    assert payload["top_samples"] == 2
    assert len(payload["params"]) == 2 and 1 <= payload["evals"] <= 5


def test_energy_normalization_preserves_order_and_argmin() -> None:
    from qshield_quantum.formulation.normalization import normalize_for_qaoa

    model = _model(8, seed=5)
    scaled, norm = normalize_for_qaoa(model, 4.0)
    bits = bits_from_indices(np.arange(256), 8)
    original = model.evaluate_batch(bits)
    new = scaled.evaluate_batch(bits)
    np.testing.assert_allclose(new, norm.scale * (original - norm.offset), atol=1e-12)
    assert int(np.argmin(new)) == int(np.argmin(original))
    assert new.max() - new.min() <= 4.0 + 1e-9
    with pytest.raises(ValueError, match="target_range"):
        normalize_for_qaoa(model, 0.0)


def test_distribution_rows_accept_normalized_energies() -> None:
    space = enumerate_state_space(_model(), CONSTRAINTS)
    bits = index_to_bitstring(int(np.flatnonzero(space.predicate_feasible)[0]), 6)
    raw = float(space.energies[bitstring_to_index(bits)])
    scale, offset = 7.5, 0.5
    result = _fake_result(1, [(bits, 0, 16)], space)
    sample = result.distribution[0]
    from dataclasses import replace

    scaled = replace(
        result, distribution=(replace(sample, energy=scale * (raw - offset)),)
    )
    rows = distribution_rows(
        QaoaRun(results={1: scaled}, shots=16),
        space,
        energy_scale=scale,
        energy_offset=offset,
    )
    assert rows[0]["qubo_energy"] == pytest.approx(raw)
