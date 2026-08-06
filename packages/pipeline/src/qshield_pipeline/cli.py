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

from qshield_pipeline.run import StageError, run_all

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


if __name__ == "__main__":
    app()
