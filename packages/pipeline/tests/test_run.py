# Đỗ Ngọc Tân - run_all: fail-fast đúng chặng, không chạy chặng sau khi chặng trước lỗi.
"""Mock ở tầng `_run_stage_subprocess` (KHÔNG import trực tiếp qshield_data/ai/risk/quantum.cli
vào tiến trình pytest) — khớp thiết kế thật của `run.py`: mỗi chặng chạy trong một tiến trình con
riêng để tránh xung đột native library qiskit/pyarrow (segfault đã verify bằng `faulthandler`, xem
docstring `run.py`). Import các package đó thẳng vào cùng tiến trình test sẽ tái tạo đúng rủi ro mà
thiết kế subprocess được tạo ra để tránh."""

import subprocess
from pathlib import Path

import pytest
import qshield_pipeline.run as run_mod
import yaml
from qshield_pipeline.run import (
    StageError,
    run_all,
    run_downstream,
    run_workflow_update,
)


def _write_config(tmp_path: Path) -> Path:
    config = {"artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")}}
    path = tmp_path / "test.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def _completed(returncode: int) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode)


def _write_downstream_configs(tmp_path: Path) -> tuple[Path, Path, Path]:
    base = _write_config(tmp_path)
    profile = tmp_path / "profile.yaml"
    profile.write_text(
        yaml.safe_dump(
            {
                "profile": {"id": "workflow_update", "status": "BASELINE_TARGET"},
                "runtime": {
                    "candidate_count": 10,
                    "bits_per_candidate": 2,
                    "total_decision_bits": 20,
                    "structured_sample_count": 211,
                    "action_levels_pct": [0, 10, 20, 30],
                },
            }
        ),
        encoding="utf-8",
    )
    override = tmp_path / "override.yaml"
    override.write_text(
        yaml.safe_dump(
            {
                "profile": {
                    "id": "workflow_update",
                    "status": "NON_BASELINE_RUN",
                },
                "runtime": {
                    "candidate_count": 8,
                    "bits_per_candidate": 2,
                    "total_decision_bits": 16,
                    "structured_sample_count": 137,
                    "action_levels_pct": [0, 10, 20, 30],
                },
            }
        ),
        encoding="utf-8",
    )
    return base, profile, override


def test_run_all_stops_at_first_failing_stage(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []

    def _fake_run(
        module: str, subcommand: str, config_path: Path, extra_args: list[str]
    ):
        calls.append(subcommand)
        if subcommand == "build":
            return _completed(1)
        raise AssertionError("chặng sau không được chạy khi chặng data đã lỗi")

    monkeypatch.setattr(run_mod, "_run_stage_subprocess", _fake_run)

    with pytest.raises(StageError) as exc_info:
        run_all(_write_config(tmp_path))

    assert exc_info.value.stage == "data"
    assert calls == ["build"]


def test_run_all_reaches_risk_stage_and_stops_there(
    tmp_path: Path, monkeypatch
) -> None:
    """Khớp acceptance test của plan.md: chạy tới đúng chặng risk (`qshield-risk effects` chưa
    implement, trả exit code khác 0) rồi dừng rõ ràng — không chạy tiếp `optimize`."""
    calls: list[str] = []

    def _fake_run(
        module: str, subcommand: str, config_path: Path, extra_args: list[str]
    ):
        calls.append(subcommand)
        if subcommand == "effects":
            return _completed(1)
        if subcommand == "solve":
            raise AssertionError("optimize không được chạy khi risk lỗi")
        return _completed(0)

    monkeypatch.setattr(run_mod, "_run_stage_subprocess", _fake_run)

    with pytest.raises(StageError) as exc_info:
        run_all(_write_config(tmp_path))

    assert exc_info.value.stage == "risk"
    assert calls == ["build", "regime", "scenarios", "effects"]


def test_run_all_returns_run_id_when_every_stage_succeeds(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[str] = []

    def _fake_run(
        module: str, subcommand: str, config_path: Path, extra_args: list[str]
    ):
        calls.append(subcommand)
        return _completed(0)

    monkeypatch.setattr(run_mod, "_run_stage_subprocess", _fake_run)

    run_id = run_all(_write_config(tmp_path))

    assert run_id is None  # dev mode: ArtifactPaths không cần run_id
    assert calls == ["build", "regime", "scenarios", "effects", "solve"]


def test_run_stage_subprocess_builds_expected_command(monkeypatch) -> None:
    """`_run_stage_subprocess` phải gọi đúng `python -c "from <module> import app; app()"
    <subcommand> --config <path> [--mock]`."""
    captured: dict = {}

    def _fake_subprocess_run(args, check):
        captured["args"] = args
        captured["check"] = check
        return _completed(0)

    monkeypatch.setattr(run_mod.subprocess, "run", _fake_subprocess_run)

    run_mod._run_stage_subprocess(
        "qshield_quantum.cli", "solve", Path("cfg.yaml"), ["--mock"]
    )

    assert captured["check"] is False
    assert "from qshield_quantum.cli import app; app()" in captured["args"]
    assert captured["args"][-4:] == ["solve", "--config", "cfg.yaml", "--mock"]


def test_run_downstream_uses_three_isolated_profiled_stages(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[tuple[str, str, list[str]]] = []

    def _fake_run(
        module: str, subcommand: str, config_path: Path, extra_args: list[str]
    ):
        calls.append((module, subcommand, extra_args))
        return _completed(0)

    monkeypatch.setattr(run_mod, "_run_stage_subprocess", _fake_run)
    base, profile, override = _write_downstream_configs(tmp_path)

    run_downstream(base, profile, override, mock=True)

    assert [subcommand for _, subcommand, _ in calls] == [
        "prepare-workflow",
        "workflow",
        "rerank-polish",
    ]
    assert calls[0][2][0] == "--mock"
    assert "--mock" not in calls[1][2]
    assert calls[2][2][0] == "--mock"
    assert all("--profile" in extra_args for _, _, extra_args in calls)
    assert all("--override" in extra_args for _, _, extra_args in calls)


def test_workflow_update_exact_fallback_runs_profiled_stages(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _fake_run(
        module: str, subcommand: str, config_path: Path, extra_args: list[str]
    ):
        calls.append((subcommand, extra_args))
        return _completed(0)

    monkeypatch.setattr(run_mod, "_run_stage_subprocess", _fake_run)
    base, profile, override = _write_downstream_configs(tmp_path)

    run_workflow_update(
        base,
        profile,
        override,
        run_data=False,
        quantum_mode="exact",
    )

    assert [command for command, _ in calls] == [
        "regime",
        "scenarios",
        "prepare-workflow",
        "workflow",
        "rerank-polish",
        "benchmark-true",
    ]
    quantum_args = calls[3][1]
    assert "--exact-only" in quantum_args
    assert "--no-warm-start" in quantum_args
    assert all("--profile" in args and "--override" in args for _, args in calls)
