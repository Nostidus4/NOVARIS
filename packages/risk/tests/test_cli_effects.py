from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from qshield_risk.cli import app
from typer.testing import CliRunner

from .conftest import TICKERS

runner = CliRunner()


def _config(tmp_path: Path, *, null_cost: bool = False) -> dict[str, Any]:
    return {
        "seed": 20260804,
        "artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")},
        "data": {"data_version": "test-v1"},
        "tickers": [{"ticker": ticker} for ticker in TICKERS],
        "sample_portfolio_weights": {ticker: 0.125 for ticker in TICKERS},
        "num_scenarios": 40,
        "horizon_days": 20,
        "cvar_alpha": 0.95,
        "robustness_confidence_levels": [0.975, 0.99],
        "action_reduction_pct": 0.20,
        "transaction_cost": {
            "fee": None if null_cost else 0.001,
            "spread": 0.002,
            "liquidity_penalty": 0.0005,
        },
        "weight_sum_tolerance": 1e-10,
        "k_actions": 3,
    }


def _write_config(tmp_path: Path, *, null_cost: bool = False) -> Path:
    path = tmp_path / "risk-test.yaml"
    path.write_text(yaml.safe_dump(_config(tmp_path, null_cost=null_cost)), encoding="utf-8")
    return path


def _risk_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts" / "dev" / "risk"


def test_mock_cli_writes_canonical_artifacts_and_provenance(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    result = runner.invoke(app, ["effects", "--config", str(config_path), "--mock"])
    assert result.exit_code == 0, result.output
    stage = _risk_dir(tmp_path)
    baseline = json.loads((stage / "baseline_risk.json").read_text(encoding="utf-8"))
    actions = pd.read_csv(stage / "action_effects.csv")
    pairs = pd.read_csv(stage / "pairwise_effects.csv")
    assert baseline["input_source"] == "mock"
    assert baseline["scenario_run_id"] == "risk_mock_fixture"
    assert baseline["ticker_order"] == list(TICKERS)
    assert set(baseline["risk_metrics"]["cvar"]) == {"0.95", "0.975", "0.99"}
    assert actions["action_id"].tolist() == list(range(8))
    assert actions["ticker"].tolist() == list(TICKERS)
    assert len(pairs) == 28
    assert (pairs["action_i"] < pairs["action_j"]).all()


def test_null_cost_fails_and_removes_stale_canonical_outputs(tmp_path: Path) -> None:
    good_config = _write_config(tmp_path)
    first = runner.invoke(app, ["effects", "--config", str(good_config), "--mock"])
    assert first.exit_code == 0, first.output
    assert (_risk_dir(tmp_path) / "baseline_risk.json").exists()

    bad_config = _write_config(tmp_path, null_cost=True)
    failed = runner.invoke(app, ["effects", "--config", str(bad_config), "--mock"])
    assert failed.exit_code != 0
    assert "fee=null" in failed.output
    for filename in ("baseline_risk.json", "action_effects.csv", "pairwise_effects.csv"):
        assert not (_risk_dir(tmp_path) / filename).exists()


def test_real_run_rejects_failed_scenario_gate_without_writing_outputs(
    tmp_path: Path,
) -> None:
    config_path = _write_config(tmp_path)
    scenario_dir = tmp_path / "artifacts" / "dev" / "scenarios"
    scenario_dir.mkdir(parents=True)
    manifest = {
        "gate_status": "FAIL",
        "input_source": "real",
        "return_type": "simple",
        "ticker_order": list(TICKERS),
        "num_scenarios": 40,
        "horizon_days": 20,
    }
    (scenario_dir / "scenario_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    result = runner.invoke(app, ["effects", "--config", str(config_path)])
    assert result.exit_code != 0
    assert "gate_status='FAIL'" in result.output
    assert not (_risk_dir(tmp_path) / "baseline_risk.json").exists()
