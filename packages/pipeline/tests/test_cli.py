# Đỗ Ngọc Tân - CLI `qshield-pipeline all`: là subcommand thật, dừng rõ ràng đúng chặng lỗi.
from pathlib import Path

import qshield_pipeline.run as run_mod
import yaml
from qshield_pipeline.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def _write_config(tmp_path: Path) -> Path:
    config = {"artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")}}
    path = tmp_path / "test.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_all_is_a_real_subcommand_not_collapsed_into_root() -> None:
    """Bug đã đo ở docs/perf/2026-08-04-pipeline-timing.md §5: Typer gộp app chỉ-một-lệnh thành
    root command nếu thiếu `@app.callback()`. `--help` phải liệt kê `all` như subcommand thật."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "all" in result.output


def test_all_command_stops_at_risk_stage_with_clear_message(
    tmp_path: Path, monkeypatch
) -> None:
    """Mock ở tầng `_run_stage_subprocess` — xem ghi chú trong test_run.py về lý do không import
    trực tiếp qshield_ai/qshield_quantum.cli vào tiến trình pytest (rủi ro segfault qiskit/pyarrow,
    đã verify)."""

    def _fake_run(module: str, subcommand: str, config_path, extra_args: list[str]):
        import subprocess

        if subcommand == "effects":
            return subprocess.CompletedProcess(args=[], returncode=1)
        if subcommand == "solve":
            raise AssertionError("optimize không được chạy khi risk lỗi")
        return subprocess.CompletedProcess(args=[], returncode=0)

    monkeypatch.setattr(run_mod, "_run_stage_subprocess", _fake_run)

    result = runner.invoke(app, ["all", "--config", str(_write_config(tmp_path))])

    assert result.exit_code == 1
    assert "Risk" in result.output
