# Đỗ Ngọc Tân - chạy tuần tự 6 chặng, validate schema giữa mỗi chặng, fail fast.
"""Orchestrator: chạy MỖI chặng trong MỘT TIẾN TRÌNH CON riêng (subprocess), không import trực
tiếp module CLI của từng package.

⚠️ Đây KHÔNG phải lựa chọn tối ưu tốc độ (plan.md câu hỏi 6 ban đầu định chọn import trực tiếp cho
nhanh) — mà là bắt buộc, đã verify bằng `faulthandler` (không suy đoán): nếu `qshield_quantum`
(qiskit + Rust `_accelerate.abi3.so`) và `qshield_ai`/`qshield_data` (ghi `.parquet` qua pyarrow)
cùng sống trong MỘT tiến trình Python, lệnh ghi parquet SAU ĐÓ sẽ segfault bên trong bộ cấp phát
mimalloc của pyarrow (`libarrow.dylib`), bất kể thứ tự import trước hay sau — tái hiện được 100%
bằng:

    uv run python -X faulthandler -c "
    import qshield_quantum.cli
    import qshield_ai.cli as ai_cli
    ai_cli.regime(config='...', mock=True)"

→ segfault ngay tại `pandas.DataFrame.to_parquet` → `pyarrow.parquet.write_table`. Cô lập từng
chặng bằng subprocess (mỗi tiến trình con chỉ import ĐÚNG MỘT package nặng) là cách duy nhất verify
được để tránh crash này hoàn toàn.

Vì chạy qua subprocess, mỗi package con tự parse `--config` của riêng nó — pipeline chia sẻ
`run_id` bằng cách tiêm qua config (xem `run_context.py`) thay vì qua tham số hàm (plan.md câu
hỏi 6).

Fail-fast: một chặng lỗi (subprocess trả exit code khác 0) thì dừng ngay, KHÔNG chạy chặng sau
(CLAUDE.md: một module critical fail giữa pipeline không được tạo final recommendation).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from qshield_contracts.config import Config

from qshield_pipeline.run_context import PipelineRunContext
from qshield_pipeline.stages import STAGE_LABELS, STAGE_ORDER


class StageError(RuntimeError):
    """Một chặng trong pipeline thất bại — kèm tên chặng để dễ tra `logs.txt`."""

    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(f"Chặng '{STAGE_LABELS.get(stage, stage)}' thất bại: {detail}")
        self.stage = stage
        self.detail = detail


def _run_stage_subprocess(
    module: str, subcommand: str, config_path: Path, extra_args: list[str]
) -> subprocess.CompletedProcess:
    """Chạy `python -c "from {module} import app; app()" {subcommand} --config <path> ...` trong
    tiến trình con — tương đương `uv run qshield-xxx {subcommand}` nhưng bỏ qua chi phí `uv run`
    tự resolve lại mỗi lần gọi (cùng kỹ thuật đã dùng để cô lập test QAOA, xem
    `packages/quantum/tests/test_cli.py`)."""
    args = [
        sys.executable,
        "-c",
        f"from {module} import app; app()",
        subcommand,
        "--config",
        str(config_path),
        *extra_args,
    ]
    return subprocess.run(args, check=False)


def run_all(config_path: Path, *, mock: bool = False) -> str | None:
    """Chạy tuần tự data → regime → scenarios → risk → optimize. Trả về `run_id` (None ở
    `artifacts.mode: dev`, khớp `ArtifactPaths`)."""
    cfg = Config.load(config_path)
    ctx = PipelineRunContext(cfg)
    logger = ctx.logger
    resolved_config_path = ctx.resolve_config_path(cfg, config_path)
    mock_flag = ["--mock"] if mock else []

    logger.info(
        "Bắt đầu pipeline — run_id=%s, mock=%s, %d chặng: %s",
        ctx.run_id,
        mock,
        len(STAGE_ORDER),
        ", ".join(STAGE_ORDER),
    )

    stage = "data"
    logger.info("[1/%d] %s", len(STAGE_ORDER), STAGE_LABELS[stage])
    # `qshield-data build` không có `--mock` (cần universe.yaml thật + network thật).
    result = _run_stage_subprocess(
        "qshield_data.cli", "build", resolved_config_path, []
    )
    if result.returncode != 0:
        raise StageError(
            stage, f"tiến trình con thoát với exit code {result.returncode}"
        )

    stage = "regime"
    logger.info("[2/%d] %s", len(STAGE_ORDER), STAGE_LABELS[stage])
    result = _run_stage_subprocess(
        "qshield_ai.cli", "regime", resolved_config_path, mock_flag
    )
    if result.returncode != 0:
        raise StageError(
            stage, f"tiến trình con thoát với exit code {result.returncode}"
        )

    stage = "scenarios"
    logger.info("[3/%d] %s", len(STAGE_ORDER), STAGE_LABELS[stage])
    result = _run_stage_subprocess(
        "qshield_ai.cli", "scenarios", resolved_config_path, mock_flag
    )
    if result.returncode != 0:
        raise StageError(
            stage, f"tiến trình con thoát với exit code {result.returncode}"
        )

    stage = "risk"
    logger.info("[4/%d] %s", len(STAGE_ORDER), STAGE_LABELS[stage])
    result = _run_stage_subprocess(
        "qshield_risk.cli", "effects", resolved_config_path, mock_flag
    )
    if result.returncode != 0:
        raise StageError(
            stage, f"tiến trình con thoát với exit code {result.returncode}"
        )

    stage = "optimize"
    logger.info("[5/%d] %s", len(STAGE_ORDER), STAGE_LABELS[stage])
    result = _run_stage_subprocess(
        "qshield_quantum.cli", "solve", resolved_config_path, mock_flag
    )
    if result.returncode != 0:
        raise StageError(
            stage, f"tiến trình con thoát với exit code {result.returncode}"
        )

    logger.info("Pipeline hoàn tất — toàn bộ %d chặng PASS.", len(STAGE_ORDER))
    return ctx.run_id


def run_downstream(
    config_path: Path,
    profile_path: Path,
    override_path: Path | None = None,
    *,
    mock: bool = False,
) -> str | None:
    """Run the four-level branch from Risk handoff through final accounting.

    This intentionally does not run Data/Regime/Scenarios. It consumes the current scenario
    artifact, or deterministic mock scenarios when requested, and scales dimensions from
    ``M=min(N_eligible, 10)``: 16 bits today and 20 bits once ten candidates are available.
    """
    cfg = Config.load_profiled(config_path, profile_path, override_path)
    runtime = cfg.workflow_runtime()
    if runtime.profile_status != "NON_BASELINE_RUN":
        raise ValueError(
            "The underfilled downstream development command requires NON_BASELINE_RUN."
        )
    ctx = PipelineRunContext(cfg)
    logger = ctx.logger
    resolved_config_path = ctx.resolve_config_path(cfg, config_path)
    mock_flag = ["--mock"] if mock else []
    profile_args = ["--profile", str(profile_path)]
    if override_path is not None:
        profile_args.extend(["--override", str(override_path)])
    stages = (
        (
            "risk_workflow",
            "qshield_risk.cli",
            "prepare-workflow",
            [*mock_flag, *profile_args],
        ),
        (
            "quantum_workflow",
            "qshield_quantum.cli",
            "workflow",
            profile_args,
        ),
        (
            "rerank_polish",
            "qshield_risk.cli",
            "rerank-polish",
            [*mock_flag, *profile_args],
        ),
    )
    logger.info(
        "Bắt đầu downstream NON_BASELINE_RUN — run_id=%s, candidates=%d, bits=%d.",
        ctx.run_id,
        runtime.candidate_count,
        runtime.total_decision_bits,
    )
    for index, (stage, module, command, extra_args) in enumerate(stages, start=1):
        logger.info("[%d/%d] %s", index, len(stages), STAGE_LABELS[stage])
        result = _run_stage_subprocess(
            module, command, resolved_config_path, list(extra_args)
        )
        if result.returncode != 0:
            raise StageError(
                stage, f"tiến trình con thoát với exit code {result.returncode}"
            )
    logger.info("Downstream NON_BASELINE_RUN hoàn tất — 3/3 chặng PASS.")
    return ctx.run_id


def run_workflow_update(
    config_path: Path,
    profile_path: Path,
    override_path: Path | None = None,
    *,
    run_data: bool = False,
    quantum_mode: str = "exact",
) -> str | None:
    """Run the profiled 30→top-10→20-bit workflow in isolated subprocesses.

    ``quantum_mode='exact'`` is the safe NON_FINAL fallback while 20-qubit QAOA runtime is being
    fixed. It still performs surrogate fit, consistency verification, exhaustive exact solve,
    classical comparison, true-risk rerank and polishing. ``quantum_mode='qaoa'`` is available
    only for an explicitly monitored run.
    """
    if quantum_mode not in {"exact", "qaoa"}:
        raise ValueError("quantum_mode must be 'exact' or 'qaoa'.")
    cfg = Config.load_profiled(config_path, profile_path, override_path)
    runtime = cfg.workflow_runtime()
    if runtime.profile_status != "NON_BASELINE_RUN":
        raise ValueError(
            "workflow-update requires NON_BASELINE_RUN until all approval gates are signed."
        )

    ctx = PipelineRunContext(cfg)
    logger = ctx.logger
    resolved_config_path = ctx.resolve_config_path(cfg, config_path)
    profile_args = ["--profile", str(profile_path)]
    if override_path is not None:
        profile_args.extend(["--override", str(override_path)])
    stages: list[tuple[str, str, str, list[str]]] = []
    if run_data:
        stages.append(("data", "qshield_data.cli", "build", profile_args))
    stages.extend(
        [
            ("regime", "qshield_ai.cli", "regime", profile_args),
            ("scenarios", "qshield_ai.cli", "scenarios", profile_args),
            (
                "risk_workflow",
                "qshield_risk.cli",
                "prepare-workflow",
                profile_args,
            ),
            (
                "quantum_workflow",
                "qshield_quantum.cli",
                "workflow",
                [
                    *profile_args,
                    *(
                        ["--exact-only", "--no-warm-start"]
                        if quantum_mode == "exact"
                        else []
                    ),
                ],
            ),
            (
                "rerank_polish",
                "qshield_risk.cli",
                "rerank-polish",
                profile_args,
            ),
            (
                "benchmark_true",
                "qshield_risk.cli",
                "benchmark-true",
                profile_args,
            ),
        ]
    )

    logger.info(
        "Bắt đầu workflow-update NON_BASELINE_RUN — run_id=%s, candidates=%d, bits=%d, "
        "quantum_mode=%s, run_data=%s.",
        ctx.run_id,
        runtime.candidate_count,
        runtime.total_decision_bits,
        quantum_mode,
        run_data,
    )
    for index, (stage, module, command, extra_args) in enumerate(stages, start=1):
        logger.info("[%d/%d] %s", index, len(stages), STAGE_LABELS[stage])
        result = _run_stage_subprocess(
            module, command, resolved_config_path, list(extra_args)
        )
        if result.returncode != 0:
            raise StageError(
                stage, f"tiến trình con thoát với exit code {result.returncode}"
            )
    logger.info(
        "workflow-update NON_BASELINE_RUN hoàn tất — %d/%d chặng PASS.",
        len(stages),
        len(stages),
    )
    return ctx.run_id
