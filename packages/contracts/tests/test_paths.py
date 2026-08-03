# Đỗ Ngọc Tân - test ArtifactPaths: dev cố định, runs có run_id, QUBO/SOLVE dùng chung "optimization".
from pathlib import Path

import pytest
from qshield_contracts.enums import Stage
from qshield_contracts.paths import ArtifactPaths


def test_dev_mode_path_is_fixed(tmp_path: Path) -> None:
    config = {"artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")}}
    paths = ArtifactPaths(config)

    assert paths.for_stage(Stage.REGIME, "regime_daily.parquet") == (
        tmp_path / "artifacts" / "dev" / "regime" / "regime_daily.parquet"
    )


def test_runs_mode_path_includes_run_id_and_outputs(tmp_path: Path) -> None:
    config = {"artifacts": {"mode": "runs", "root": str(tmp_path / "artifacts")}}
    paths = ArtifactPaths(config, run_id="run_20260101_0000")

    expected = (
        tmp_path
        / "artifacts"
        / "runs"
        / "run_20260101_0000"
        / "outputs"
        / "regime"
        / "regime_daily.parquet"
    )
    assert paths.for_stage(Stage.REGIME, "regime_daily.parquet") == expected


def test_runs_mode_requires_run_id(tmp_path: Path) -> None:
    config = {"artifacts": {"mode": "runs", "root": str(tmp_path / "artifacts")}}
    with pytest.raises(ValueError):
        ArtifactPaths(config)


def test_qubo_and_solve_share_optimization_dir(tmp_path: Path) -> None:
    config = {"artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")}}
    paths = ArtifactPaths(config)

    assert paths.stage_dir(Stage.QUBO) == paths.stage_dir(Stage.SOLVE)
    assert paths.stage_dir(Stage.QUBO).name == "optimization"


def test_ensure_creates_directory(tmp_path: Path) -> None:
    config = {"artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")}}
    paths = ArtifactPaths(config)

    paths.ensure(Stage.RISK)

    assert paths.stage_dir(Stage.RISK).is_dir()
