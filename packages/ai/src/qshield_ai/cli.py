# Nguyễn Anh Tú - CLI `uv run qshield-ai regime` / `uv run qshield-ai scenarios`.

import typer

app = typer.Typer(
    help="Q-SHIELD AI CLI: market regime detection & scenario generation."
)


@app.command()
def regime(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Đường dẫn config"
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Sinh dữ liệu giả từ qshield_contracts.mocks thay vì đọc nguồn thật",
    ),
) -> None:
    """Huấn luyện/suy luận Gaussian HMM → regime_daily.parquet (3 xác suất trạng thái/ngày)."""
    raise NotImplementedError


@app.command()
def scenarios(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Đường dẫn config"
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Sinh dữ liệu giả từ qshield_contracts.mocks thay vì đọc nguồn thật",
    ),
) -> None:
    """Sinh kịch bản stress bằng regime-conditioned moving-block bootstrap → stress_scenarios.npz."""
    raise NotImplementedError


if __name__ == "__main__":
    app()
