# Nguyễn Anh Tú - smoke test CLI regime trên fixture: artifact ra đủ, đúng schema, chạy lại y hệt.
import json
from pathlib import Path

import pandas as pd
import yaml
from qshield_ai.cli import app
from qshield_contracts.schemas.regime import RegimeDailySchema
from qshield_contracts.validate import validate_or_raise
from typer.testing import CliRunner

runner = CliRunner()


def _write_config(tmp_path: Path, **overrides) -> Path:
    """Config phẳng, không `includes` — Config.load xử lý được, và test không đụng configs/ thật."""
    config = {
        "seed": 20260804,
        "artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")},
        "paths": {"data_root": str(tmp_path / "data")},
        "data": {"data_version": "test-v1"},
        "tickers": [{"ticker": name} for name in ("AAA", "BBB", "CCC", "DDD")],
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
        "transforms": {
            "realized_vol_20d": "log",
            "mean_pairwise_corr_60d": "fisher_z",
        },
        "seeds": {"count": 3, "values": [101, 202, 303]},
        "candidates": {"n_states": [3], "covariance_type": ["diag"]},
        "champion": {"n_states": 3, "covariance_type": "diag"},
        "gate": {"min_state_occupancy": 0.02, "min_mean_label_agreement": 0.60},
        "fallback": {"vol_quantile": 0.8, "drawdown_threshold": -0.10},
    }
    config.update(overrides)
    path = tmp_path / "test.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def _run(tmp_path: Path, **overrides):
    config_path = _write_config(tmp_path, **overrides)
    return runner.invoke(app, ["regime", "--config", str(config_path), "--mock"])


def test_regime_command_writes_all_artifacts(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.exit_code == 0, result.output

    stage = tmp_path / "artifacts" / "dev" / "regime"
    assert (stage / "regime_daily.parquet").exists()
    assert (stage / "regime_summary.json").exists()
    assert (stage / "regime_selection.csv").exists()


def test_written_parquet_passes_the_contract_schema(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.exit_code == 0, result.output
    daily = pd.read_parquet(
        tmp_path / "artifacts" / "dev" / "regime" / "regime_daily.parquet"
    )
    validate_or_raise(daily, RegimeDailySchema, context="test")
    assert not daily.isna().to_numpy().any()
    # Chỉ bắt được trường hợp `smoothed_probabilities` thoái hóa thành filtered (hai cột
    # trùng khít). KHÔNG bắt được việc hoán vị hai đối số `filtered=`/`smoothed=` ở cli.py:
    # hoán vị vẫn cho hai cột khác nhau và artifact vẫn NHẤT QUÁN nội bộ (`state_id` cũng
    # đổi theo, vì nó là argmax của cùng mảng). Việc đó được chặn ở tầng lắp ráp thay vì ở
    # đây: `test_regime_output.py` dùng fixture có filtered=0.7 vs smoothed=0.6 cùng ô nên
    # hoán vị làm test đó đỏ ngay.
    assert not daily["prob_normal"].equals(daily["prob_normal_smoothed"]), (
        "prob_normal trùng khít prob_normal_smoothed — smoothed_probabilities đã thoái hóa."
    )
    diagnostic = {
        "method",
        "inference_status",
        "viterbi_state_id",
        "viterbi_label",
        "prob_normal_smoothed",
        "prob_volatile_smoothed",
        "prob_stress_smoothed",
        "feature_version",
        "split",
        "run_mode",
    }
    # RegimeDailySchema là `strict=False`; cột chẩn đoán phải sống sót qua validate_or_raise
    # (CLI ghi frame ĐÃ validate, nên nếu schema siết lại thì chúng biến mất im lặng).
    assert diagnostic <= set(daily.columns), sorted(diagnostic - set(daily.columns))


def test_summary_records_provenance_and_open_decisions(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.exit_code == 0, result.output
    summary = json.loads(
        (tmp_path / "artifacts" / "dev" / "regime" / "regime_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["run_mode"] == "NON_BASELINE_RUN"
    # `--mock` và run thật ghi vào CÙNG đường dẫn `artifacts/dev/regime/`, nên đây là dấu vết DUY
    # NHẤT phân biệt được hai loại artifact. `run_mode` không thay được vai này: nó nói về trạng
    # thái baseline, không nói đầu vào là thật hay giả.
    assert summary["input_source"] == "mock"
    assert summary["gate_status"] == "OK"
    assert summary["seeds_reported"] == [101, 202, 303]
    assert summary["champion"]["n_states"] == 3
    assert summary["unresolved_decisions"], "run nháp phải liệt kê quyết định chưa chốt"
    assert set(summary["label_map"].values()) == {"normal", "volatile", "stress"}


def test_run_context_metadata_is_written(tmp_path: Path) -> None:
    """Quy tắc 13: 4 file metadata do RunContext ghi, không phải module tính toán."""
    result = _run(tmp_path)
    assert result.exit_code == 0, result.output
    run_root = tmp_path / "artifacts" / "dev"
    for name in ("config.json", "data_version.json", "metrics.json", "logs.txt"):
        assert (run_root / name).exists(), name


def test_selection_report_lists_every_seed(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.exit_code == 0, result.output
    report = pd.read_csv(
        tmp_path / "artifacts" / "dev" / "regime" / "regime_selection.csv"
    )
    assert sorted(report["seed"].unique()) == [101, 202, 303]
    assert report["is_champion"].sum() == 1


def test_rerun_produces_identical_frames(tmp_path: Path) -> None:
    """Cùng config + cùng seed ⇒ cùng nhãn. Khác nhau là dấu hiệu còn nguồn ngẫu nhiên chưa ghim."""
    first_result = _run(tmp_path)
    assert first_result.exit_code == 0, first_result.output
    first = pd.read_parquet(
        tmp_path / "artifacts" / "dev" / "regime" / "regime_daily.parquet"
    )
    second_result = _run(tmp_path)
    assert second_result.exit_code == 0, second_result.output
    second = pd.read_parquet(
        tmp_path / "artifacts" / "dev" / "regime" / "regime_daily.parquet"
    )
    pd.testing.assert_frame_equal(first, second)


def test_failed_gate_writes_fallback_and_exits_nonzero(tmp_path: Path) -> None:
    """AD-07: cổng fail ⇒ không có regime_daily.parquet, có artifact fallback, exit != 0.

    `config.update(overrides)` thay THẾ cả khóa "gate" (không merge nông), nên override phải mang
    theo `min_mean_label_agreement` — thiếu nó thì `cli.py` (đọc trực tiếp qua subscript, không
    `.get()`, để KeyError sớm nếu config thật thiếu khóa) sẽ KeyError trước khi kịp chạy selection.
    """
    result = _run(
        tmp_path, gate={"min_state_occupancy": 0.99, "min_mean_label_agreement": 0.60}
    )
    assert result.exit_code != 0

    stage = tmp_path / "artifacts" / "dev" / "regime"
    assert not (stage / "regime_daily.parquet").exists()
    assert (stage / "regime_daily_rule_based.parquet").exists()

    fallback = pd.read_parquet(stage / "regime_daily_rule_based.parquet")
    assert not any(column.startswith("prob") for column in fallback.columns)

    summary = json.loads((stage / "regime_summary.json").read_text(encoding="utf-8"))
    assert summary["gate_status"] == "HMM_FAILED"
    assert summary["gate_reasons"]


def test_gate_failure_removes_stale_champion_from_prior_run(tmp_path: Path) -> None:
    """Ngày 1 cổng OK ghi champion; ngày 2 (cùng thư mục dev) cổng FAIL không được để champion
    ngày 1 sống sót — `qshield_risk`/backend đọc thẳng `regime_daily.parquet`, không đọc
    `regime_summary.json`, nên file cũ còn nằm đó là champion "ma" của một run đã fail cổng.
    """
    stage = tmp_path / "artifacts" / "dev" / "regime"

    ok_result = _run(tmp_path)
    assert ok_result.exit_code == 0, ok_result.output
    assert (stage / "regime_daily.parquet").exists()
    assert not (stage / "regime_daily_rule_based.parquet").exists()

    fail_result = _run(
        tmp_path, gate={"min_state_occupancy": 0.99, "min_mean_label_agreement": 0.60}
    )
    assert fail_result.exit_code != 0

    assert not (stage / "regime_daily.parquet").exists(), (
        "champion của run OK trước đó phải bị xóa khi run sau FAIL cổng"
    )
    assert (stage / "regime_daily_rule_based.parquet").exists()


def test_gate_success_removes_stale_fallback_from_prior_run(tmp_path: Path) -> None:
    """Chiều ngược lại: ngày 1 cổng FAIL để lại fallback; ngày 2 cổng OK phải dọn fallback cũ,
    không để một artifact rule-based lạc hậu nằm cạnh champion mới.
    """
    stage = tmp_path / "artifacts" / "dev" / "regime"

    fail_result = _run(
        tmp_path, gate={"min_state_occupancy": 0.99, "min_mean_label_agreement": 0.60}
    )
    assert fail_result.exit_code != 0
    assert (stage / "regime_daily_rule_based.parquet").exists()

    ok_result = _run(tmp_path)
    assert ok_result.exit_code == 0, ok_result.output

    assert (stage / "regime_daily.parquet").exists()
    assert not (stage / "regime_daily_rule_based.parquet").exists(), (
        "fallback của run FAIL trước đó phải bị xóa khi run sau OK cổng"
    )
