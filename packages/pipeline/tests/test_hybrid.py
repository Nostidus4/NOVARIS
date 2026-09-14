from __future__ import annotations

import copy
import itertools
from typing import Any

import numpy as np
import pandas as pd
import pytest
from qshield_contracts.schemas.hybrid import REFERENCE_TRACK
from qshield_pipeline.hybrid.instances import (
    InstanceInputs,
    portfolio_weights,
    select_dates,
)
from qshield_pipeline.hybrid.runner import run_instance
from qshield_pipeline.hybrid.settings import HybridSettings
from qshield_pipeline.hybrid.stats import holm_adjust, paired_frame, summarize_uplift
from qshield_quantum.solvers.qaoa import QaoaSample, QaoaSeedResult

TICKERS = ("A", "B", "C", "D", "E", "F")


def _risk_config() -> dict[str, Any]:
    return {
        "cvar_alpha": 0.95,
        "robustness_confidence_levels": [0.99],
        "horizon_days": 2,
        "weight_sum_tolerance": 1e-8,
        "maximum_reduction": 0.30,
        "target_cash_increment": 0.10,
        "transaction_cost": {
            "fee": 0.0015,
            "spread": 0.001,
            "liquidity_penalty": 0.0005,
        },
        "financial_objective": {
            "components": {
                "cvar": {"weight": 1.0, "scale": 0.1},
                "return_sacrifice": {"weight": 0.25, "scale": 0.05},
                "transaction_cost": {"weight": 0.25, "scale": 0.01},
                "turnover": {"weight": 0.05, "scale": 0.2},
                "liquidity_penalty": {"weight": 0.25, "scale": 0.01},
                "cash_budget_deviation": {"weight": 0.35, "scale": 0.1},
            }
        },
        "candidate_selection": {
            "score_weights": {
                k: 1.0
                for k in (
                    "marginal_10",
                    "marginal_20",
                    "marginal_30",
                    "baseline_contribution",
                    "transaction_cost",
                    "liquidity_penalty",
                )
            }
        },
        "objective_sampling": {
            "policy_version": "test",
            "train_random_count": 20,
            "validation_count": 10,
            "holdout_count": 10,
            "chunk_size": 16,
            "seeds": {"train": 1, "validation": 2, "holdout": 3},
        },
    }


def _settings(**budget_overrides: Any) -> HybridSettings:
    raw = {
        "experiment_id": "test_hybrid",
        "candidate_count": 3,
        "num_scenarios": 120,
        "universe_lookback_start": "2020-01-01",
        "min_eligible_blocks": 1,
        "budgets": {
            "candidate_budget": 12,
            "polish_top_k": 3,
            "polish_max_evaluations": 20,
            "polish_max_adjustment": 0.05,
            "reference_polish_top_k": 4,
            "compute_budget_max_evaluations": 40,
            "eval_timing_samples": 3,
            **budget_overrides,
        },
        "tracks": {
            "candidate_budget": [
                "classical_true",
                "classical_surrogate",
                "random_uniform",
                "random_stratified",
                "boltzmann",
                "qaoa",
            ],
            "compute_budget": ["classical_true_compute", "random_uniform_compute"],
            "ablation": ["heuristic_baselines"],
        },
        "qaoa": {
            "seeds": [1, 2, 3],
            "shots": 64,
            "reps": 1,
            "maxiter": 5,
            "warm_start": False,
            "seed_timeout_seconds": 10,
            "total_timeout_seconds": None,
        },
        "generator_seeds": {
            "random_uniform": 11,
            "random_stratified": 12,
            "boltzmann": 13,
            "classical_true": 14,
            "classical_surrogate": 15,
            "classical_true_compute": 16,
            "random_uniform_compute": 17,
        },
        "reference": {
            "exact_true_grid_max_bits": 16,
            "grid_workers": 1,
            "grid_chunk_size": 16,
        },
        "metrics": {
            "near_optimal_eps": [0.01],
            "recall_top_k": [5],
            "diversity_sample": 50,
        },
        "statistics": {},
    }
    return HybridSettings.from_config({"hybrid_experiment": raw})


def _inputs() -> InstanceInputs:
    rng = np.random.default_rng(42)
    market = rng.normal(-0.004, 0.03, size=(120, 2, 1))
    cube = market * np.linspace(0.6, 1.5, 6) + rng.normal(0, 0.02, size=(120, 2, 6))
    weights = {t: 0.9 / 6 for t in TICKERS}
    return InstanceInputs(
        instance={
            "instance_id": "x01_test",
            "set": "exploratory",
            "scenario_seed": 5,
            "target_regime": "volatile",
            "portfolio_id": "diversified",
            "as_of_date": "2024-01-02",
        },
        scenarios=cube,
        tickers=TICKERS,
        weights=weights,
        cash_weight=0.10,
        eligibility={t: True for t in TICKERS},
        ineligible_reasons={},
        config=_risk_config(),
        metadata={"scenario_gate": "PASS"},
    )


def _fake_qaoa(qp, *, seed: int, shots: int, **_kwargs: Any) -> QaoaSeedResult:
    rng = np.random.default_rng(seed)
    n = qp.get_num_vars()
    counts = rng.multinomial(shots, rng.dirichlet(np.ones(2**n) * 0.3))
    samples = []
    for index, count in enumerate(counts):
        if count == 0:
            continue
        bits = format(index, f"0{n}b")
        x = np.fromiter(bits, dtype=int)
        samples.append(
            QaoaSample(
                bits, float(qp.objective.evaluate(x)), count / shots, True, int(count)
            )
        )
    return QaoaSeedResult(
        seed=seed,
        bitstring=samples[0].bitstring,
        energy=0.0,
        feasible=True,
        feasibility_rate=1.0,
        success_prob=0.0,
        runtime_seconds=0.01,
        samples=(),
        transpiled=True,
        distribution=tuple(samples),
        optimal_parameters=(0.1 * seed, 0.2 * seed),
        circuit_evaluations=5,
    )


def test_run_instance_end_to_end_attribution_and_budgets() -> None:
    settings = _settings()
    out = run_instance(
        _inputs(), settings, experiment_id="test_hybrid", qaoa_solver=_fake_qaoa
    )
    assert out.result["attribution_checklist"]["status"] == "PASS"
    pools, tracks, polish = out.pools, out.tracks.set_index("track"), out.polish
    non_reference = pools.loc[pools["track"] != REFERENCE_TRACK]
    assert not non_reference["source_method"].str.contains("exact").any()
    budget_view = tracks.loc[tracks["view"] == "candidate_budget"]
    assert set(budget_view["budget_candidates"]) == {12}
    assert (
        budget_view["true_evaluations_generation"] == budget_view["generated_unique"]
    ).all()
    assert tracks.loc["classical_true", "generated_unique"] == 12
    assert set(tracks.loc[tracks["view"] == "compute_budget"].index) == {
        "classical_true_compute",
        "random_uniform_compute",
    }
    assert (polish["true_objective_evaluations"] <= 20).all()
    assert not polish["active_set_changed"].any()
    refs = out.result["references"]
    j_grid = refs["j_star_grid"]
    assert (budget_view["raw_best_true_objective"] >= j_grid - 1e-12).all()
    finals = tracks["polished_best_true_objective"].dropna()
    assert (finals >= refs["j_best_known"] - 1e-12).all()
    metrics = out.result["qaoa_distribution_metrics"]
    assert metrics["total_shots"] == 3 * 64
    assert metrics["unique_measured"] <= 64
    assert out.distribution.groupby("seed")["probability"].sum().round(9).eq(1.0).all()


def test_run_instance_qaoa_failure_is_recorded_not_hidden() -> None:
    def broken(_qp, **_kwargs: Any):
        raise RuntimeError("simulated crash")

    out = run_instance(
        _inputs(), _settings(), experiment_id="test_hybrid", qaoa_solver=broken
    )
    tracks = out.tracks.set_index("track")
    assert tracks.loc["qaoa", "status"] == "FAILED"
    assert tracks.loc["boltzmann", "status"] == "EMPTY"
    assert tracks.loc["classical_true", "status"] == "OK"
    assert {a["status"] for a in out.result["qaoa_attempts"]} == {"failed"}


def test_select_dates_gap_and_count_rule() -> None:
    calendar = list(pd.bdate_range("2024-01-01", periods=100))
    regime = pd.DataFrame(
        {
            "date": calendar,
            "regime": ["stress"] * 100,
            "prob_stress": [0.95] * 90 + [0.5] * 10,
            "split": ["test"] * 100,
        }
    )
    picks = select_dates(
        regime,
        calendar,
        splits=["test"],
        regime="stress",
        count=3,
        min_gap_sessions=20,
        min_probability=0.9,
    )
    assert len(picks) == 3
    positions = [calendar.index(p) for p in picks]
    assert all(b - a >= 20 for a, b in itertools.pairwise(positions))
    assert max(positions) < 90


def test_portfolio_weights_sum_to_one_with_cash() -> None:
    eligible = {t: t != "F" for t in TICKERS}
    spec = {
        "kind": "sector_tilt",
        "cash_weight": 0.05,
        "tilt_share": 0.7,
        "tilt_tickers": ["A", "B"],
    }
    weights, cash = portfolio_weights(
        spec, TICKERS, eligible, pd.DataFrame(), pd.Timestamp("2024-01-01")
    )
    assert sum(weights.values()) + cash == pytest.approx(1.0)
    assert weights["F"] == 0.0
    assert weights["A"] + weights["B"] == pytest.approx(0.95 * 0.7)


def test_paired_stats_failure_counts_as_loss_and_holm() -> None:
    rows = []
    for i in range(6):
        rows.append(
            {
                "instance_id": f"i{i}",
                "track": "qaoa",
                "status": "OK" if i else "FAILED",
                "polished_best_true_objective": 1.0,
                "polished_best_feasible": True,
                "j_no_action": 2.0,
                "improvement_scale": 1.0,
                "target_regime": "normal",
            }
        )
        rows.append(
            {
                "instance_id": f"i{i}",
                "track": "classical_true",
                "status": "OK",
                "polished_best_true_objective": 1.1,
                "polished_best_feasible": True,
                "j_no_action": 2.0,
                "improvement_scale": 1.0,
                "target_regime": "normal",
            }
        )
    joined = paired_frame(pd.DataFrame(rows), target="qaoa", baseline="classical_true")
    summary = summarize_uplift(
        joined, tie_tolerance=1e-9, bootstrap_resamples=200, bootstrap_seed=0
    )
    assert summary["wins"] == 5 and summary["losses"] == 1
    assert joined.set_index("instance_id").loc["i0", "uplift"] == pytest.approx(-0.9)
    adjusted = holm_adjust({"a": 0.01, "b": 0.04, "c": None})
    assert adjusted == {"c": None, "a": pytest.approx(0.02), "b": pytest.approx(0.04)}


def test_settings_reject_unknown_track() -> None:
    raw = copy.deepcopy(_settings().raw)
    raw["tracks"]["candidate_budget"].append("exact")
    with pytest.raises(ValueError, match="unknown tracks"):
        HybridSettings.from_config({"hybrid_experiment": raw})


def test_policy_v2_never_forces_unattainable_cash_and_blocks_do_not_sell_candidates() -> (
    None
):
    from qshield_pipeline.hybrid.instances import instance_policy

    weights = {"A": 0.5, "B": 0.3, "C": 0.15, "D": 0.0}
    template = {
        "policy_version": "t",
        "status": "EXPERIMENT_SYNTHETIC",
        "risk_appetite": "b",
        "cash_max": 1.0,
        "cvar_budget": 1.0,
        "max_turnover": 1.0,
    }
    policy = instance_policy(
        {"policy": {"do_not_sell_top_weight_count": 2}},
        template,
        {"target_cash_increment": 0.10},
        weights,
        0.05,
        {},
    )
    assert policy["cash_min"] == pytest.approx(0.05)
    assert policy["do_not_sell"] == ["A", "B"]


def test_run_instance_skips_when_no_true_feasible_state() -> None:
    from qshield_pipeline.hybrid.instances import InstanceSkipped

    inputs = _inputs()
    config = copy.deepcopy(inputs.config)
    config["risk_policy"] = {
        "policy_version": "t",
        "status": "S",
        "risk_appetite": "b",
        "cash_min": 0.99,
        "cash_max": 1.0,
        "cvar_budget": 1.0,
        "max_turnover": 1.0,
    }
    blocked = InstanceInputs(**{**inputs.__dict__, "config": config})
    with pytest.raises(InstanceSkipped, match="NO_TRUE_FEASIBLE_STATE"):
        run_instance(blocked, _settings(), experiment_id="t", qaoa_solver=_fake_qaoa)


def test_qaoa_transfer_track_uses_registered_parameters_and_normalization() -> None:
    settings = _settings()
    raw = copy.deepcopy(settings.raw)
    raw["tracks"]["candidate_budget"].append("qaoa_transfer")
    raw["tracks"]["compute_budget"] += [
        "classical_true_compute_transfer",
        "random_uniform_compute_transfer",
    ]
    raw["qaoa"]["transfer"] = {"maxiter": 2, "source_set": "exploratory"}
    raw["qaoa"]["energy_normalization"] = {"target_range": 4.0}
    raw["generator_seeds"] |= {
        "classical_true_compute_transfer": 18,
        "random_uniform_compute_transfer": 19,
    }
    transfer_settings = HybridSettings.from_config({"hybrid_experiment": raw})
    seen: list[Any] = []

    def recording(qp, **kwargs: Any):
        seen.append(kwargs.get("initial_point"))
        return _fake_qaoa(qp, **kwargs)

    out = run_instance(
        _inputs(),
        transfer_settings,
        experiment_id="t",
        qaoa_solver=recording,
        transfer_parameters={"x01_test": [0.5, 0.25]},
    )
    tracks = out.tracks.set_index("track")
    assert tracks.loc["qaoa_transfer", "status"] == "OK"
    assert [0.5, 0.25] in seen and None in seen
    assert out.result["qaoa_energy_normalization"]["target_range"] == 4.0
    assert set(out.distribution["track"]) == {"qaoa", "qaoa_transfer"}
    missing = run_instance(
        _inputs(),
        transfer_settings,
        experiment_id="t",
        qaoa_solver=_fake_qaoa,
        transfer_parameters={},
    )
    assert missing.tracks.set_index("track").loc["qaoa_transfer", "status"] == "FAILED"


def test_transfer_parameters_canonicalize_and_leave_one_out(tmp_path) -> None:
    import json
    import math

    from qshield_pipeline.hybrid.transfer import (
        build_transfer_parameters,
        canonicalize,
        parameters_for_manifest,
    )

    assert canonicalize([0.4, -0.3], 1).tolist() == pytest.approx([-0.4, 0.3])
    assert canonicalize([math.pi - 0.1, 0.3], 1).tolist() == pytest.approx([-0.1, 0.3])
    for iid, (beta, gamma) in {
        "a": (0.1, 1.0),
        "b": (0.2, 2.0),
        "c": (0.3, 3.0),
    }.items():
        d = tmp_path / "instances" / iid
        d.mkdir(parents=True)
        attempts = [{"status": "completed", "optimal_parameters": [beta, gamma]}]
        (d / "instance_result.json").write_text(
            json.dumps({"qaoa_attempts_by_track": {"qaoa": attempts}})
        )
    payload = build_transfer_parameters(
        tmp_path, ["a", "b", "c"], source_set="exploratory", reps=1
    )
    assert payload["pooled"] == pytest.approx([0.2, 2.0])
    assert payload["leave_one_out"]["a"] == pytest.approx([0.25, 2.5])
    exploratory = parameters_for_manifest(
        payload, {"set": "exploratory", "instances": [{"instance_id": "a"}]}
    )
    confirmation = parameters_for_manifest(
        payload, {"set": "confirmation", "instances": [{"instance_id": "z"}]}
    )
    assert exploratory["a"] == pytest.approx([0.25, 2.5])
    assert confirmation["z"] == pytest.approx([0.2, 2.0])
