# Nguyễn Đỗ Minh Anh - Data Source Register: nguồn, ngày lấy, quyền dùng, version.
"""Universe Registry (30→8 mã đã khóa) và Data Source Register.

Port từ `CLEAN.ipynb` Cell 8-9 (`UNIVERSE_ROWS`, `SOURCE_ROWS`). Khác với notebook: danh sách mã và
`data_source` (yahoo/dnse) không còn hard-code trong Python — đọc từ `configs/universe.yaml` (đúng
ràng buộc CLAUDE.md quy tắc 8 "Không hard-code ticker").
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

_UNIVERSE_COLUMNS = [
    "ticker",
    "yahoo_symbol",
    "company_name",
    "first_trading_date",
    "exchange_current",
    "exchange_history",
    "exchange_periods",
    "data_source",
    "notes",
]


def load_universe(universe_config: dict[str, Any]) -> pd.DataFrame:
    """Chuyển section `tickers` của `configs/universe.yaml` (đã parse) thành DataFrame.

    `universe_config` là dict đã đọc từ yaml (vd qua `_config_stub.load_config`), PHẢI có key
    `tickers`: list[dict] với đúng các cột trong `_UNIVERSE_COLUMNS`.

    Trả về DataFrame index mặc định, cột đúng thứ tự `_UNIVERSE_COLUMNS`. Raise `ValueError` nếu
    universe rỗng, có ticker trùng, hoặc `data_source` không thuộc {"yahoo", "dnse"}.
    """
    rows = universe_config.get("tickers")
    if not rows:
        raise ValueError(
            "universe_config['tickers'] rỗng hoặc null — configs/universe.yaml chưa được điền "
            "(xem TODO/PROVISIONAL trong file đó)."
        )
    df = pd.DataFrame(rows)
    missing_cols = set(_UNIVERSE_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"universe.yaml thiếu cột bắt buộc: {sorted(missing_cols)}")
    df = df[_UNIVERSE_COLUMNS].copy()

    if df["ticker"].duplicated().any():
        dups = df.loc[df["ticker"].duplicated(), "ticker"].tolist()
        raise ValueError(f"Universe có ticker trùng: {dups}")

    bad_source = ~df["data_source"].isin(["yahoo", "dnse"])
    if bad_source.any():
        bad = df.loc[bad_source, ["ticker", "data_source"]].to_dict("records")
        raise ValueError(
            f"data_source phải là 'yahoo' hoặc 'dnse', gặp giá trị lạ: {bad}"
        )

    df["first_trading_date"] = pd.to_datetime(df["first_trading_date"]).dt.strftime(
        "%Y-%m-%d"
    )
    return df.reset_index(drop=True)


def build_source_register(
    access_date: str,
    yfinance_version: str,
    vnstock_version: str,
    test_end: str,
) -> pd.DataFrame:
    """Sinh Data Source Register — 4 nguồn dùng trong pipeline tải giá.

    Port từ `CLEAN.ipynb` Cell 9 (`SOURCE_ROWS`), bổ sung dòng `DNSE_PRICES` (notebook có code tải
    DNSE nhưng thiếu dòng tương ứng trong Source Register — bổ sung cho đủ, tránh nguồn dữ liệu
    không được ghi lại theo PR-DAT-009).
    """
    rows = [
        {
            "source_id": "YF_PRICES",
            "source_name": "Yahoo Finance (via yfinance)",
            "url_or_path": "https://finance.yahoo.com",
            "coverage_from": "2016-01-01",
            "coverage_to": test_end,
            "fields": "Open, High, Low, Close, Adj Close, Volume",
            "license": "Free tier — for research/prototype only",
            "fallback_source": "DNSE/Entrade cho 6 mã multi-exchange; vnstock (VCI) nếu cả hai fail",
            "access_date": access_date,
            "yfinance_version": yfinance_version,
            "notes": (
                "Yahoo Adj Close đã điều chỉnh cổ tức và chia tách. LƯU Ý: Yahoo .VN chỉ có data "
                "từ ngày mã lên HOSE — mất history HNX/UPCOM của các mã đã chuyển sàn. Các mã đó "
                "được lấy từ DNSE/Entrade thay thế (xem DNSE_PRICES)."
            ),
        },
        {
            "source_id": "DNSE_PRICES",
            "source_name": "DNSE/Entrade OHLC API",
            "url_or_path": "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock",
            "coverage_from": "ngày niêm yết đầu tiên của từng mã (kể cả HNX/UPCOM)",
            "coverage_to": test_end,
            "fields": "Open, High, Low, Close, Adj Close (=Close), Volume",
            "license": "Public API, không auth — nguồn công ty chứng khoán DNSE (nền tảng Entrade)",
            "fallback_source": "Yahoo Finance nếu DNSE fail (nhưng sẽ mất pre-HOSE history)",
            "access_date": access_date,
            "yfinance_version": "-",
            "notes": (
                "Nguồn CHÍNH cho các mã multi-exchange (từng niêm yết HNX/UPCOM trước khi chuyển "
                "HOSE). Giá trả về theo nghìn VNĐ, nhân 1000 để nhất quán với Yahoo. Giá đã điều "
                "chỉnh cổ tức/chia tách, dùng làm cả Close và Adj Close."
            ),
        },
        {
            "source_id": "VNSTOCK_PRICES",
            "source_name": "vnstock (nguồn VCI) — Giá cổ phiếu",
            "url_or_path": "vnstock.stock(source='VCI').quote.history()",
            "coverage_from": "ngày niêm yết đầu tiên của từng mã (any exchange)",
            "coverage_to": test_end,
            "fields": "Open, High, Low, Close, Volume (Close đã điều chỉnh split/cổ tức)",
            "license": "vnstock — free, dữ liệu thật qua Vietcap (VCI)",
            "fallback_source": "Yahoo Finance nếu vnstock fail (nhưng sẽ mất pre-HOSE history)",
            "access_date": access_date,
            "vnstock_version": vnstock_version,
            "notes": (
                "Alternative cho DNSE khi cần lấy đầy đủ history từ HNX/UPCOM. vnstock VCI trả "
                "`close` đã điều chỉnh → gán Close = Adj Close cho consistent với schema Yahoo."
            ),
        },
        {
            "source_id": "VNSTOCK_INDEX",
            "source_name": "vnstock (nguồn VCI) — VN-Index",
            "url_or_path": "VNINDEX (source=VCI)",
            "coverage_from": "2016-01-01",
            "coverage_to": test_end,
            "fields": "Open, High, Low, Close, Volume",
            "license": "vnstock — free, dữ liệu thật từ HOSE qua Vietcap (VCI)",
            "fallback_source": "Yahoo Finance (^VNINDEX/^VNI) → nếu cũng fail, custom market composite từ universe",
            "access_date": access_date,
            "vnstock_version": vnstock_version,
            "notes": (
                "VN-Index lấy trực tiếp từ vnstock (VCI) — dữ liệu thật, thay cho Yahoo Finance "
                "vốn không có index VN. Cũng dùng làm trading calendar chuẩn để loại phantom days "
                "của Yahoo (xem clean/validate_prices.remove_yahoo_phantom_days)."
            ),
        },
    ]
    return pd.DataFrame(rows)


def save_universe_and_sources(
    universe: pd.DataFrame,
    sources: pd.DataFrame,
    metadata_dir: Path,
    universe_as_of: str,
) -> tuple[Path, Path]:
    """Ghi `universe_asof_{YYYYMMDD}.csv` và `source_register.csv` vào `metadata_dir`.

    `universe_as_of` phải là chuỗi `YYYY-MM-DD`; dùng để đặt tên file universe snapshot.
    """
    metadata_dir = Path(metadata_dir)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    as_of_tag = pd.to_datetime(universe_as_of).strftime("%Y%m%d")
    universe_path = metadata_dir / f"universe_asof_{as_of_tag}.csv"
    sources_path = metadata_dir / "source_register.csv"

    universe.to_csv(universe_path, index=False, encoding="utf-8-sig")
    sources.to_csv(sources_path, index=False, encoding="utf-8-sig")
    return universe_path, sources_path
