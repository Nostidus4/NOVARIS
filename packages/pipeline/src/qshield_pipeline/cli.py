# Đỗ Ngọc Tân - CLI `uv run qshield-pipeline all` — một lệnh chạy toàn bộ pipeline.
"""CLI `qshield-pipeline all` — orchestrator end-to-end, xem `run.py` cho logic từng chặng (mỗi
chặng chạy trong một subprocess riêng — bắt buộc để tránh xung đột native library qiskit/pyarrow,
xem docstring `run.py`).

`@app.callback()` bắt buộc phải có: Typer gộp app chỉ-một-lệnh thành root command nếu thiếu, khiến
`qshield-pipeline all --config ...` thất bại với "no such option" — bug đã đo ở
`docs/perf/2026-08-04-pipeline-timing.md` §5 (cùng loại lỗi từng gặp ở `qshield-quantum solve`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from qshield_pipeline.run import (
    StageError,
    run_all,
    run_downstream,
    run_workflow_update,
)

app = typer.Typer(help="Q-SHIELD end-to-end pipeline CLI.")


def _tolerate_legacy_console_encoding() -> None:
    """Console cp1252 (Windows Git Bash/cmd.exe cũ) không mã hóa được tiếng Việt có dấu — copy từ
    `qshield_ai/cli.py`/`qshield_quantum/cli.py`, xem
    `docs/perf/2026-08-04-pipeline-timing.md` §8."""
    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", None)
        if encoding and encoding.lower() != "utf-8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


@app.callback()
def _main() -> None:
    """Giữ `all` là subcommand thật (bug đã đo ở §5, xem docstring module)."""
    _tolerate_legacy_console_encoding()


@app.command(name="all")
def run_all_command(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Đường dẫn config"
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Chạy trên dữ liệu giả từ qshield_contracts.mocks/fixtures — cho phép 5 người phát "
        "triển song song từ ngày 1",
    ),
) -> None:
    """Chạy tuần tự 5 bước: data → regime → scenarios → risk → optimize (qubo+solve gộp).

    Fail fast: dừng ngay tại chặng lỗi đầu tiên, in rõ tên chặng (xem `run.py`, `stages.py`).
    """
    try:
        run_id = run_all(Path(config), mock=mock)
    except StageError as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"[pipeline] OK — toàn bộ 5 chặng PASS (run_id={run_id or 'dev'}).")


@app.command(name="downstream")
def run_downstream_command(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Base config path"
    ),
    profile: str = typer.Option(
        "configs/profiles/workflow_update.yaml",
        "--profile",
        help="Product profile path",
    ),
    override: str = typer.Option(
        "configs/provisional/workflow_update_downstream.yaml",
        "--override",
        help="Explicit NON_BASELINE override path",
    ),
    mock: bool = typer.Option(
        False, "--mock", help="Use deterministic current eight-ticker scenario fixture"
    ),
) -> None:
    """Run Risk selection/sampling → generic Quantum → true rerank/local polishing."""
    try:
        run_id = run_downstream(Path(config), Path(profile), Path(override), mock=mock)
    except (StageError, ValueError) as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        "[pipeline/downstream] OK — NON_BASELINE_RUN 3 chặng PASS "
        f"(run_id={run_id or 'dev'})."
    )


@app.command(name="workflow-update")
def run_workflow_update_command(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Base config path"
    ),
    profile: str = typer.Option(
        "configs/profiles/workflow_update.yaml",
        "--profile",
        help="Product profile path",
    ),
    override: str = typer.Option(
        "configs/provisional/workflow_update_downstream.yaml",
        "--override",
        help="Explicit NON_BASELINE override path",
    ),
    run_data: bool = typer.Option(
        False,
        "--run-data",
        help="Also fetch/rebuild Data; default reuses the current 30-ticker Data artifacts",
    ),
    quantum_mode: str = typer.Option(
        "exact",
        "--quantum-mode",
        help="exact = safe fallback; qaoa = explicitly monitored NON_FINAL QAOA run",
    ),
) -> None:
    """Run Regime → Scenarios → Risk top-10 → Quantum → rerank/polish → true-benchmark."""
    try:
        run_id = run_workflow_update(
            Path(config),
            Path(profile),
            Path(override),
            run_data=run_data,
            quantum_mode=quantum_mode,
        )
    except (StageError, ValueError) as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        "[pipeline/workflow-update] OK — NON_BASELINE_RUN "
        f"(run_id={run_id or 'dev'}, quantum_mode={quantum_mode})."
    )


if __name__ == "__main__":
    app()
