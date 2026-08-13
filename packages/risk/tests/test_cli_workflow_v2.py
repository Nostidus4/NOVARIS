from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from qshield_risk.cli import _eligibility_snapshot, _solver_candidate_pool, app
from qshield_risk.objective import COMPONENT_NAMES
from typer.testing import CliRunner

from .conftest import TICKERS

runner = CliRunner()


def _base(tmp_path: Path) -> dict[str, Any]:
    return {
        "seed": 20260813,
        "artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")},
        "paths": {"data_root": str(tmp_path / "data")},
        "data": {"data_version": "test-v2"},
        "tickers": [{"ticker": ticker} for ticker in TICKERS],
        "sample_portfolio_weights": {ticker: 0.125 for ticker in TICKERS},
        "sample_portfolio_cash_weight": 0.0,
        "num_scenarios": 40,
        "horizon_days": 20,
        "cvar_alpha": 0.95,
        "robustness_confidence_levels": [0.975, 0.99],
        "weight_sum_tolerance": 1e-10,
        "maximum_reduction": 0.30,
        "target_cash_increment": 0.10,
        "transaction_cost": {"fee": 0.001, "spread": 0.001, "liquidity_penalty": 0.0005},
        "financial_objective": {
            "components": {
                name: {"weight": 1.0 if name == "cvar" else 0.0, "scale": 1.0}
                for name in COMPONENT_NAMES
            }
        },
        "candidate_selection": {
            "output_candidates": 10,
            "score_weights": {
                "marginal_10": 1.0,
                "marginal_20": 1.0,
                "marginal_30": 1.0,
                "baseline_contribution": 1.0,
                "transaction_cost": 1.0,
                "liquidity_penalty": 1.0,
            },
        },
        "candidate_gate": {
            "coverage_at_n_min": 0.70,
            "median_overlap_at_n_min": 0.70,
            "worst_overlap_at_n_min": 0.50,
            "sensitivity_counts": [12, 15],
        },
        "objective_sampling": {
            "policy_version": "test-v2",
            "train_random_count": 2,
            "validation_count": 1,
            "holdout_count": 2,
            "chunk_size": 2,
            "seeds": {"train": 11, "validation": 22, "holdout": 33},
        },
        "quantum_constraints": {},
    }


def _write_configs(tmp_path: Path) -> tuple[Path, Path]:
    base = tmp_path / "base.yaml"
    profile = tmp_path / "profile.yaml"
    base.write_text(yaml.safe_dump(_base(tmp_path)), encoding="utf-8")
    profile.write_text(
        yaml.safe_dump(
            {
                "profile": {"id": "workflow_update", "status": "NON_BASELINE_RUN"},
                "provenance": {"config_version": "test-v2"},
            }
        ),
        encoding="utf-8",
    )
    return base, profile


def test_prepare_workflow_writes_v2_gate_and_split_handoffs(tmp_path: Path) -> None:
    base, profile = _write_configs(tmp_path)
    result = runner.invoke(
        app,
        [
            "prepare-workflow",
            "--config",
            str(base),
            "--profile",
            str(profile),
            "--mock",
        ],
    )
    assert result.exit_code == 0, result.output
    risk_dir = tmp_path / "artifacts" / "dev" / "risk"
    gate = json.loads((risk_dir / "candidate_gate.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (risk_dir / "objective_sample_manifest.json").read_text(encoding="utf-8")
    )
    summary = json.loads((risk_dir / "risk_summary.json").read_text(encoding="utf-8"))
    baseline = json.loads((risk_dir / "baseline_risk.json").read_text(encoding="utf-8"))
    samples = pd.read_parquet(risk_dir / "true_objective_samples.parquet")
    assert gate["status"] == "FAIL"
    assert "UNDERFILLED_CANDIDATES_8_OF_10" in gate["reasons"]
    assert gate["analysis_handoff_allowed"] is True
    assert gate["baseline_handoff_allowed"] is False
    assert manifest["structured_count"] == 137
    assert manifest["overlap_count"] == 0
    assert set(samples["split"]) == {"train", "validation", "holdout"}
    assert len(samples) == 137 + 2 + 1 + 2
    assert summary["candidate_count"] == 8
    assert summary["total_decision_bits"] == 16
    assert baseline["schema_version"] == "risk-workflow-v2"
    assert baseline["producer"] == "qshield_risk"
    assert baseline["policy_version"] == "UNAPPROVED_POLICY"
    assert "risk_metrics" in baseline
    assert (risk_dir / "candidate_topn.csv").exists()
    assert (risk_dir / "qubo_objective_samples.parquet").exists()


def test_solver_pool_combines_exact_qaoa_and_classical_provenance() -> None:
    pool = _solver_candidate_pool(
        {
            "candidate_pool": [
                {"bitstring": "0000", "energy": 0.0, "sources": ["qaoa_seed_11"]}
            ]
        },
        {
            "top_feasible_candidates": [
                {"bitstring": "1000", "energy": -0.2, "feasible": True}
            ]
        },
        {"classical_bitstring": "0100", "classical_energy": -0.1},
    )

    assert {item["source_solver"] for item in pool} == {
        "qaoa_seed_11",
        "exact",
        "classical",
    }


def test_prepare_failure_removes_stale_and_partial_canonical_outputs(
    tmp_path: Path,
) -> None:
    base, profile = _write_configs(tmp_path)
    payload = yaml.safe_load(base.read_text(encoding="utf-8"))
    payload["objective_sampling"]["seeds"] = {
        "train": 11,
        "validation": 11,
        "holdout": 33,
    }
    base.write_text(yaml.safe_dump(payload), encoding="utf-8")
    risk_dir = tmp_path / "artifacts" / "dev" / "risk"
    risk_dir.mkdir(parents=True)
    (risk_dir / "final_recommendation.json").write_text("stale", encoding="utf-8")

    result = runner.invoke(
        app,
        ["prepare-workflow", "--config", str(base), "--profile", str(profile), "--mock"],
    )

    assert result.exit_code != 0
    assert not (risk_dir / "candidate_top10.csv").exists()
    assert not (risk_dir / "candidate_order.json").exists()
    assert not (risk_dir / "final_recommendation.json").exists()
    assert not list(risk_dir.glob("*.pending"))


def test_eligibility_snapshot_is_point_in_time_and_keeps_restricted_reason(
    tmp_path: Path,
) -> None:
    path = tmp_path / "eligibility.parquet"
    pd.DataFrame(
        [
            {
                "date": "2026-08-01",
                "ticker": "AAA",
                "eligible_flag": True,
                "trade_eligible_flag": False,
                "model_eligible_flag": True,
                "reason_code": "TRADE_RESTRICTED",
            },
            {
                "date": "2026-08-01",
                "ticker": "BBB",
                "eligible_flag": True,
                "trade_eligible_flag": True,
                "model_eligible_flag": True,
                "reason_code": "ELIGIBLE",
            },
            {
                "date": "2026-08-04",
                "ticker": "AAA",
                "eligible_flag": True,
                "trade_eligible_flag": True,
                "model_eligible_flag": True,
                "reason_code": "FUTURE_ROW_MUST_NOT_LEAK",
            },
            {
                "date": "2026-08-04",
                "ticker": "BBB",
                "eligible_flag": True,
                "trade_eligible_flag": True,
                "model_eligible_flag": True,
                "reason_code": "FUTURE_ROW_MUST_NOT_LEAK",
            },
        ]
    ).to_parquet(path, index=False)

    eligibility, reasons, _ = _eligibility_snapshot(
        {"eligibility_artifact": str(path)},  # type: ignore[arg-type]
        ("AAA", "BBB"),
        {"evaluation_date": "2026-08-03"},
        {"AAA": 0.5, "BBB": 0.5},
        mock=False,
        tolerance=1e-10,
    )

    assert eligibility == {"AAA": False, "BBB": True}
    assert reasons["AAA"] == "TRADE_RESTRICTED"
