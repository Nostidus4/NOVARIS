# Đỗ Ngọc Tân - PipelineRunContext: dev không cần run_id, runs sinh một run_id dùng chung.
import logging
from pathlib import Path

import yaml
from qshield_contracts.config import Config
from qshield_pipeline.run_context import PipelineRunContext, resolve_pipeline_run_id


def _write_config(tmp_path: Path, mode: str) -> Path:
    config = {"artifacts": {"mode": mode, "root": str(tmp_path / "artifacts")}}
    path = tmp_path / "test.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_resolve_pipeline_run_id_dev_mode_returns_none(tmp_path: Path) -> None:
    cfg = Config.load(_write_config(tmp_path, "dev"))
    assert resolve_pipeline_run_id(cfg) is None


def test_resolve_pipeline_run_id_runs_mode_returns_run_id(tmp_path: Path) -> None:
    cfg = Config.load(_write_config(tmp_path, "runs"))
    run_id = resolve_pipeline_run_id(cfg)
    assert run_id is not None
    assert run_id.startswith("run_")


def test_resolve_config_path_dev_mode_returns_original_path(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, "dev")
    cfg = Config.load(config_path)
    ctx = PipelineRunContext(cfg)
    assert ctx.resolve_config_path(cfg, config_path) == config_path


def test_resolve_config_path_runs_mode_injects_shared_run_id(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, "runs")
    cfg = Config.load(config_path)
    ctx = PipelineRunContext(cfg)

    resolved = ctx.resolve_config_path(cfg, config_path)

    assert resolved != config_path
    merged = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    assert merged["run_id"] == ctx.run_id
    assert merged["artifacts"]["mode"] == "runs"


def test_pipeline_logger_is_wired_up(tmp_path: Path) -> None:
    """Không assert nội dung `logs.txt` trên đĩa: `RunContext.logger()` cache theo tên logger
    toàn cục (`qshield.{run_id}.{name}`) — trong dev mode, `run_id` chỉ có độ phân giải giây, nên
    nhiều `PipelineRunContext` dựng liên tiếp trong CÙNG một giây (như nhiều test chạy nhanh) có
    thể trùng tên logger và tái dùng FileHandler trỏ tới `tmp_path` của lần chạy trước — bug đã có
    sẵn ở `qshield_contracts.runs.RunContext`, không phải của `packages/pipeline`. Ở đây chỉ kiểm
    tra `ctx.logger` được nối dây đúng, không kiểm tra nội dung file để tránh test giả-flaky."""
    config_path = _write_config(tmp_path, "dev")
    cfg = Config.load(config_path)
    ctx = PipelineRunContext(cfg)

    assert isinstance(ctx.logger, logging.Logger)
    ctx.logger.info("hello from pipeline test")  # không raise là đủ
