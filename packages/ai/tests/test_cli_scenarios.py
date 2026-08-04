# Nguyễn Anh Tú - smoke test CLI scenarios: cube đúng shape/khóa, gate fail thì KHÔNG ghi cube.
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from qshield_ai.cli import app
from typer.testing import CliRunner

runner = CliRunner()
TICKERS = ("AAA", "BBB", "CCC", "DDD")

# Ngưỡng mặc định — vô hại (giống configs/scenarios.yaml thật), để test tập trung vào hành vi CLI
# thay vì phải nghĩ lại bộ ngưỡng mỗi lần.
_DEFAULT_THRESHOLDS = {
    "mean_abs_diff_max": 0.0010,
    "std_ratio_min": 0.80,
    "std_ratio_max": 1.25,
    "skew_abs_diff_max": 1.0,
    "kurtosis_abs_diff_max": 5.0,
    "quantile_rel_error_max": 0.25,
    "autocorr_abs_diff_max": 0.10,
    "corr_mean_abs_diff_max": 0.10,
    "tail_coverage_ratio_min": 0.5,
    "tail_coverage_ratio_max": 2.0,
}

# Ngưỡng bất khả thi — mọi cube thật sẽ FAIL ít nhất một metric, dùng để test PR-SCN-013.
_IMPOSSIBLE_THRESHOLDS = {
    "mean_abs_diff_max": 0.0,
    "std_ratio_min": 10.0,
    "std_ratio_max": 20.0,
    "skew_abs_diff_max": 0.0,
    "kurtosis_abs_diff_max": 0.0,
    "quantile_rel_error_max": 0.0,
    "autocorr_abs_diff_max": 0.0,
    "corr_mean_abs_diff_max": 0.0,
    "tail_coverage_ratio_min": 10.0,
    "tail_coverage_ratio_max": 20.0,
}


def _write_config(tmp_path: Path, **overrides) -> Path:
    """Config phẳng, không `includes` — test không đụng vào configs/ thật.

    Interface drift so với brief gốc (Task 10/11 đổi sau khi brief được viết):
    - `gate` cần cả `min_mean_label_agreement` (thiếu thì lệnh `regime` KeyError trước khi kịp
      chạy selection — xem `test_cli_regime.py`).
    - `validation` cần cả `min_reference_windows` (từ khóa bắt buộc của `build_validation_report`,
      không có default) — override toàn bộ khóa `validation` mà quên khóa này sẽ TypeError.
    """
    config = {
        "seed": 20260804,
        "artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")},
        "paths": {"data_root": str(tmp_path / "data")},
        "data": {"data_version": "test-v1"},
        "tickers": [{"ticker": name} for name in TICKERS],
        "n_iter": 50,
        "feature_contract_version": "v0.2",
        "features": {
            "market_columns": [
                "market_log_return",
                "realized_vol_20d",
                "drawdown",
                "liquidity_20d",
            ],
            "corr_window": 60,
        },
        "transforms": {"realized_vol_20d": "log", "mean_pairwise_corr_60d": "fisher_z"},
        "seeds": {"count": 3, "values": [101, 202, 303]},
        "candidates": {"n_states": [3], "covariance_type": ["diag"]},
        "champion": {"n_states": 3, "covariance_type": "diag"},
        "gate": {"min_state_occupancy": 0.02, "min_mean_label_agreement": 0.60},
        "fallback": {"vol_quantile": 0.8, "drawdown_threshold": -0.10},
        "num_scenarios": 60,
        "horizon_days": 20,
        "block_length": 5,
        "scenario_seed": 20260804,
        "evaluation_date": None,
        "validation": {
            "reference": "regime_matched_forward_windows",
            "min_reference_windows": 30,
            "thresholds": _DEFAULT_THRESHOLDS,
        },
    }
    config.update(overrides)
    path = tmp_path / "test.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


@pytest.fixture
def prepared(tmp_path: Path) -> Path:
    """Chạy chặng regime trước — scenarios đọc regime_daily.parquet của nó."""
    config_path = _write_config(tmp_path)
    result = runner.invoke(app, ["regime", "--config", str(config_path), "--mock"])
    assert result.exit_code == 0, result.output
    return config_path


def _scenario_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts" / "dev" / "scenarios"


def _regime_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts" / "dev" / "regime"


def test_scenarios_command_writes_all_artifacts(tmp_path: Path, prepared: Path) -> None:
    result = runner.invoke(app, ["scenarios", "--config", str(prepared), "--mock"])
    assert result.exit_code == 0, result.output

    stage = _scenario_dir(tmp_path)
    for name in (
        "stress_scenarios.npz",
        "scenarios_by_regime.npz",
        "scenario_validation.csv",
        "scenario_manifest.json",
    ):
        assert (stage / name).exists(), name


def test_cube_has_the_contracted_keys_and_shape(tmp_path: Path, prepared: Path) -> None:
    runner.invoke(app, ["scenarios", "--config", str(prepared), "--mock"])
    with np.load(
        _scenario_dir(tmp_path) / "stress_scenarios.npz", allow_pickle=False
    ) as data:
        assert set(data.files) == {"scenarios", "scenarios_log", "ticker_order"}
        assert data["scenarios"].shape == (60, 20, len(TICKERS))
        assert list(data["ticker_order"]) == list(TICKERS)
        np.testing.assert_allclose(
            data["scenarios"], np.expm1(data["scenarios_log"]), atol=1e-15
        )
        assert np.isfinite(data["scenarios"]).all()


def test_manifest_records_provenance(tmp_path: Path, prepared: Path) -> None:
    runner.invoke(app, ["scenarios", "--config", str(prepared), "--mock"])
    manifest = json.loads(
        (_scenario_dir(tmp_path) / "scenario_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["run_mode"] == "NON_BASELINE_RUN"
    assert manifest["return_type"] == "simple"
    assert manifest["ticker_order"] == list(TICKERS)
    assert manifest["target_regime"] in {"normal", "volatile", "stress"}
    assert manifest["evaluation_date"]
    assert manifest["block_length"] == 5
    assert manifest["primary"]["eligible_block_count"] > 0
    assert 0.0 <= manifest["primary"]["reuse_rate"] <= 1.0
    assert manifest["unresolved_decisions"]


def test_validation_csv_covers_every_generated_regime(
    tmp_path: Path, prepared: Path
) -> None:
    runner.invoke(app, ["scenarios", "--config", str(prepared), "--mock"])
    report = pd.read_csv(_scenario_dir(tmp_path) / "scenario_validation.csv")
    assert {"target_regime", "metric", "verdict"} <= set(report.columns)
    assert report["target_regime"].nunique() >= 1
    assert set(report["verdict"]) <= {"PASS", "WARN", "FAIL"}


def test_by_regime_cubes_are_written_for_evidence(
    tmp_path: Path, prepared: Path
) -> None:
    """AD-12: cần >= 2 regime để so sánh stress với normal (AC-SCN-009)."""
    runner.invoke(app, ["scenarios", "--config", str(prepared), "--mock"])
    with np.load(
        _scenario_dir(tmp_path) / "scenarios_by_regime.npz", allow_pickle=False
    ) as data:
        regimes = {name for name in data.files if not name.endswith("_log")}
        regimes.discard("ticker_order")
        assert regimes, "phải có ít nhất một cube theo regime"
        for regime in regimes:
            assert data[regime].shape == (60, 20, len(TICKERS))


def test_rerun_reproduces_the_cube(tmp_path: Path, prepared: Path) -> None:
    runner.invoke(app, ["scenarios", "--config", str(prepared), "--mock"])
    with np.load(_scenario_dir(tmp_path) / "stress_scenarios.npz") as data:
        first = data["scenarios"].copy()
    runner.invoke(app, ["scenarios", "--config", str(prepared), "--mock"])
    with np.load(_scenario_dir(tmp_path) / "stress_scenarios.npz") as data:
        second = data["scenarios"].copy()
    np.testing.assert_array_equal(first, second)


def test_impossible_thresholds_block_the_cube(tmp_path: Path) -> None:
    """PR-SCN-013: gate fail ⇒ cube KHÔNG được ghi, exit != 0, nhưng báo cáo vẫn còn."""
    config_path = _write_config(
        tmp_path,
        validation={
            "reference": "regime_matched_forward_windows",
            "min_reference_windows": 30,
            "thresholds": _IMPOSSIBLE_THRESHOLDS,
        },
    )
    assert (
        runner.invoke(app, ["regime", "--config", str(config_path), "--mock"]).exit_code
        == 0
    )
    result = runner.invoke(app, ["scenarios", "--config", str(config_path), "--mock"])

    assert result.exit_code != 0
    stage = _scenario_dir(tmp_path)
    assert not (stage / "stress_scenarios.npz").exists()
    assert (stage / "scenario_validation.csv").exists()
    manifest = json.loads(
        (stage / "scenario_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["gate_status"] == "FAIL"


def test_force_writes_the_cube_despite_a_failed_gate(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        validation={
            "reference": "regime_matched_forward_windows",
            "min_reference_windows": 30,
            "thresholds": _IMPOSSIBLE_THRESHOLDS,
        },
    )
    runner.invoke(app, ["regime", "--config", str(config_path), "--mock"])
    result = runner.invoke(
        app, ["scenarios", "--config", str(config_path), "--mock", "--force"]
    )

    assert result.exit_code == 0, result.output
    assert (_scenario_dir(tmp_path) / "stress_scenarios.npz").exists()
    manifest = json.loads(
        (_scenario_dir(tmp_path) / "scenario_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["gate_status"] == "FAIL"
    assert manifest["forced"] is True


def test_scenarios_without_a_regime_artifact_fails_clearly(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    result = runner.invoke(app, ["scenarios", "--config", str(config_path), "--mock"])
    assert result.exit_code != 0
    assert "regime_daily.parquet" in str(result.output) + str(result.exception)


def test_scenarios_refuses_rule_based_fallback_without_force(tmp_path: Path) -> None:
    """Cổng HMM FAIL ⇒ chỉ có regime_daily_rule_based.parquet (không posterior). scenarios phải
    từ chối chạy trên đó trừ khi `--force` — nhãn rule-based không có gì để điều kiện hóa hợp lệ.
    """
    config_path = _write_config(
        tmp_path, gate={"min_state_occupancy": 0.99, "min_mean_label_agreement": 0.60}
    )
    gate_result = runner.invoke(app, ["regime", "--config", str(config_path), "--mock"])
    assert gate_result.exit_code != 0
    assert (_regime_dir(tmp_path) / "regime_daily_rule_based.parquet").exists()
    assert not (_regime_dir(tmp_path) / "regime_daily.parquet").exists()

    result = runner.invoke(app, ["scenarios", "--config", str(config_path), "--mock"])
    assert result.exit_code != 0
    assert not (_scenario_dir(tmp_path) / "stress_scenarios.npz").exists()


def test_force_allows_rule_based_fallback_regime(tmp_path: Path) -> None:
    """Chiều ngược lại của test trên: `--force` cho phép chạy scenarios trên fallback rule-based."""
    config_path = _write_config(
        tmp_path, gate={"min_state_occupancy": 0.99, "min_mean_label_agreement": 0.60}
    )
    runner.invoke(app, ["regime", "--config", str(config_path), "--mock"])
    assert (_regime_dir(tmp_path) / "regime_daily_rule_based.parquet").exists()

    result = runner.invoke(
        app, ["scenarios", "--config", str(config_path), "--mock", "--force"]
    )
    assert result.exit_code == 0, result.output
    assert (_scenario_dir(tmp_path) / "stress_scenarios.npz").exists()
    manifest = json.loads(
        (_scenario_dir(tmp_path) / "scenario_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["forced"] is True
    assert manifest["regime_source"] == "rule_based_fallback"
