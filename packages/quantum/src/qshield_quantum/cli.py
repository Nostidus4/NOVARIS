# Đỗ Ngọc Tân - CLI `uv run qshield-quantum solve` → artifacts/.../optimization/.

import typer

app = typer.Typer(help="Q-SHIELD Quantum solver CLI.")


@app.command()
def solve(
    config: str = typer.Option("configs/base.yaml", "--config", help="Đường dẫn config"),
    mock: bool = typer.Option(False, "--mock", help="Sinh dữ liệu giả từ qshield_contracts.mocks thay vì đọc nguồn thật"),
) -> None:
    """Dựng QUBO từ action_effects.csv, chạy verify/consistency + exact + QAOA → qaoa_result.json."""
    raise NotImplementedError


if __name__ == "__main__":
    app()
