# Đỗ Ngọc Tân - test RunContext: run_id, logger ghi logs.txt, ghi config/data_version/metrics json.
import json
from pathlib import Path

from qshield_contracts.paths import ArtifactPaths
from qshield_contracts.runs import RunContext


def _paths(tmp_path: Path) -> ArtifactPaths:
    return ArtifactPaths(
        {"artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")}}
    )


def test_run_id_generated_even_in_dev_mode(tmp_path: Path) -> None:
    ctx = RunContext({"seed": 1}, _paths(tmp_path))
    assert ctx.run_id.startswith("run_")


def test_write_config_snapshot(tmp_path: Path) -> None:
    ctx = RunContext({"seed": 1, "data": {"data_version": "v1.0.0"}}, _paths(tmp_path))

    out_path = ctx.write_config_snapshot()

    assert out_path.exists()
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["seed"] == 1


def test_write_data_version_and_metrics(tmp_path: Path) -> None:
    ctx = RunContext({}, _paths(tmp_path))

    dv_path = ctx.write_data_version("v1.0.0")
    metrics_path = ctx.write_metrics({"cvar_before": 0.1, "cvar_after": 0.05})

    dv = json.loads(dv_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert dv["data_version"] == "v1.0.0"
    assert dv["run_id"] == ctx.run_id
    assert metrics["cvar_after"] == 0.05


def test_logger_writes_to_logs_txt(tmp_path: Path) -> None:
    ctx = RunContext({}, _paths(tmp_path))
    logger = ctx.logger("test")

    logger.info("hello from test")

    log_path = ctx.artifact_paths.run_root / "logs.txt"
    assert log_path.exists()
    assert "hello from test" in log_path.read_text(encoding="utf-8")
