# Liêu Hoài Phúc - CLI `uv run qshield-risk effects` → artifacts/.../risk/.

import typer

app = typer.Typer(help="Q-SHIELD Risk Engine CLI.")


@app.command()
def effects(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Đường dẫn config"
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Sinh dữ liệu giả từ qshield_contracts.mocks thay vì đọc nguồn thật",
    ),
) -> None:
    """Tính CVaR trước hedge, chi phí và hệ số g/C/c cho từng hành động → action_effects.csv."""
    raise NotImplementedError


if __name__ == "__main__":
    app()
