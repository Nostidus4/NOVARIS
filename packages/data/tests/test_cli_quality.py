# Nguyễn Anh Tú - CLI `quality`: guard cấu hình thiếu `price_limits` (finding 2, review round 1).
from pathlib import Path

import pandas as pd
import yaml
from qshield_data.cli import app
from typer.testing import CliRunner

runner = CliRunner()

_TICKER = {
    "ticker": "AAA",
    "yahoo_symbol": "AAA.VN",
    "company_name": "Test Co",
    "first_trading_date": "2020-01-01",
    "exchange_current": "HOSE",
    "exchange_history": "-",
    "exchange_periods": [{"exchange": "HOSE"}],
    "data_source": "yahoo",
    "notes": "",
}


def _write_config(tmp_path: Path, *, with_price_limits: bool) -> Path:
    """Config phẳng, không `includes` (giống test_cli_regime.py) — chỉ đủ để `quality` chạy tới
    đoạn đọc `cfg["price_limits"]`. Prices/returns không cần dữ liệu thật: KeyError phải nổ ra
    TRƯỚC khi `find_price_limit_violations`/`run_all_checks` chạm vào nội dung của chúng.
    """
    data_root = tmp_path / "data"
    processed = data_root / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2022-01-01"]),
            "ticker": ["AAA"],
            "adjusted_close": [10.0],
            "volume": [100],
        }
    ).to_parquet(processed / "prices_adjusted.parquet", index=False)
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2022-01-01"]),
            "ticker": ["AAA"],
            "simple_return": [0.01],
            "split": ["train"],
        }
    ).to_parquet(processed / "returns.parquet", index=False)

    config: dict = {
        "paths": {
            "data_root": str(data_root),
            "reports_root": str(tmp_path / "reports"),
        },
        "tickers": [dict(_TICKER)],
        "expected_ticker_count": 1,
    }
    if with_price_limits:
        config["price_limits"] = {
            "tolerance_pct": 0.005,
            "bands_by_exchange": {"HOSE": 0.07},
        }
    path = tmp_path / "test.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def _run(tmp_path: Path, *, with_price_limits: bool):
    config_path = _write_config(tmp_path, with_price_limits=with_price_limits)
    return runner.invoke(app, ["quality", "--config", str(config_path)])


def test_quality_missing_price_limits_section_exits_nonzero_naming_key(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, with_price_limits=False)
    assert result.exit_code == 1, result.output
    assert "price_limits" in result.output


def test_quality_missing_bands_by_exchange_key_exits_nonzero_naming_key(
    tmp_path: Path,
) -> None:
    config_path = _write_config(tmp_path, with_price_limits=True)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    del config["price_limits"]["bands_by_exchange"]
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    result = runner.invoke(app, ["quality", "--config", str(config_path)])
    assert result.exit_code == 1, result.output
    assert "bands_by_exchange" in result.output


def test_quality_with_full_config_does_not_hit_the_guard(tmp_path: Path) -> None:
    """Kiểm soát: config đầy đủ phải đi qua đoạn `try`/`except` (không exit 1 vì thiếu key)."""
    result = _run(tmp_path, with_price_limits=True)
    assert result.exit_code == 0, result.output
    assert (tmp_path / "reports" / "price_limit_violations.csv").exists()
