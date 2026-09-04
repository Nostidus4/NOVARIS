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


def test_second_run_context_with_same_run_id_still_writes_its_own_logs(
    tmp_path: Path,
) -> None:
    """`logging.getLogger` là registry toàn cục theo tiến trình, còn tên logger chỉ gồm
    `run_id` + `name`. Hai run KHÁC `run_root` nhưng TRÙNG `run_id` (dev mode, hai tmp_path)
    vì thế nhận cùng một đối tượng logger. Nếu chỉ kiểm `if not logger.handlers`, run thứ hai
    tái dùng `FileHandler` cũ trỏ vào `run_root` CŨ và `logs.txt` của nó không bao giờ tồn tại —
    mất lặng lẽ một trong 4 file metadata bắt buộc (CLAUDE.md quy tắc 13). Bug này từng làm
    `test_run_context_metadata_is_written` (packages/ai) fail tuỳ thứ tự chạy test.
    """
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    fixed_run_id = "shared_run_id"

    def _context(root: Path) -> RunContext:
        paths = ArtifactPaths(
            {"artifacts": {"mode": "runs", "root": str(root / "artifacts")}},
            run_id=fixed_run_id,
        )
        return RunContext({}, paths)

    first = _context(first_root)
    first.logger("stage").info("from first run")

    second = _context(second_root)
    second.logger("stage").info("from second run")

    assert first.run_id == second.run_id, "tiền đề của test: hai run trùng run_id"
    first_log = first.artifact_paths.run_root / "logs.txt"
    second_log = second.artifact_paths.run_root / "logs.txt"
    assert first_log.exists()
    assert second_log.exists(), "run thứ hai phải có logs.txt của riêng nó"
    assert "from second run" in second_log.read_text(encoding="utf-8")
    # Handler cũ phải bị đóng, không được tiếp tục ghi vào run_root cũ.
    assert "from second run" not in first_log.read_text(encoding="utf-8")
