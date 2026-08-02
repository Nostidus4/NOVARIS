# Đỗ Ngọc Tân - CLI `uv run qshield-pipeline all` — một lệnh chạy toàn bộ pipeline.

import typer

app = typer.Typer(help="Q-SHIELD end-to-end pipeline CLI.")


@app.command(name="all")
def run_all(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Đường dẫn config"
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Chạy trên dữ liệu giả từ qshield_contracts.mocks — cho phép 5 người phát triển song song từ ngày 1",
    ),
) -> None:
    """Chạy tuần tự 6 chặng: data → regime → scenarios → risk → qubo → solve.

    Validate schema giữa mỗi chặng, fail fast nếu một chặng lỗi (xem stages.py, run.py).
    """
    raise NotImplementedError


if __name__ == "__main__":
    app()
