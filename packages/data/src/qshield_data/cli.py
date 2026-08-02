# Nguyễn Đỗ Minh Anh - CLI `uv run qshield-data build` → data/processed/*.parquet.

import typer

app = typer.Typer(help="Q-SHIELD Data Pipeline CLI.")


@app.command()
def build(
    config: str = typer.Option("configs/base.yaml", "--config", help="Đường dẫn config"),
    mock: bool = typer.Option(False, "--mock", help="Sinh dữ liệu giả từ qshield_contracts.mocks thay vì đọc nguồn thật"),
) -> None:
    """Thu thập, làm sạch dữ liệu, tạo feature và ghi returns.parquet / features.parquet."""
    raise NotImplementedError


if __name__ == "__main__":
    app()
