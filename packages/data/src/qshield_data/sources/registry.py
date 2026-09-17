# Nguyễn Đỗ Minh Anh - Data Source Register: nguồn, ngày lấy, quyền dùng, version.
"""Universe Registry 30 mã (workflow_update) và Data Source Register.

Port từ `CLEAN.ipynb` Cell 8-9 (`UNIVERSE_ROWS`, `SOURCE_ROWS`). Khác với notebook: danh sách mã và
`data_source` không còn hard-code trong Python — đọc từ `configs/base.yaml` (đúng
ràng buộc CLAUDE.md quy tắc 8 "Không hard-code ticker").
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

_UNIVERSE_COLUMNS = [
    "ticker",
    "company_name",
    "first_trading_date",
    "exchange_current",
    "exchange_history",
    "exchange_periods",
    "data_source",
    "notes",
]
_ALLOWED_SOURCES = ["fiinpro"]


def load_universe(universe_config: dict[str, Any]) -> pd.DataFrame:
    """Chuyển section `tickers` của `configs/base.yaml` (đã parse) thành DataFrame.

    `universe_config` là dict đã đọc từ yaml (vd qua `Config.load`), PHẢI có key
    `tickers`: list[dict] với đúng các cột trong `_UNIVERSE_COLUMNS`.

    Trả về DataFrame index mặc định, cột đúng thứ tự `_UNIVERSE_COLUMNS`. Raise `ValueError` nếu
    universe rỗng, có ticker trùng, hoặc `data_source` khác `"fiinpro"`.
    """
    rows = universe_config.get("tickers")
    if not rows:
        raise ValueError(
            "universe_config['tickers'] rỗng hoặc null — configs/base.yaml chưa được điền "
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

    bad_source = ~df["data_source"].isin(_ALLOWED_SOURCES)
    if bad_source.any():
        bad = df.loc[bad_source, ["ticker", "data_source"]].to_dict("records")
        raise ValueError(
            f"data_source phải thuộc {_ALLOWED_SOURCES}, gặp giá trị lạ: {bad}"
        )

    df["first_trading_date"] = pd.to_datetime(df["first_trading_date"]).dt.strftime(
        "%Y-%m-%d"
    )
    return df.reset_index(drop=True)


def build_source_register(
    access_date: str,
    vnstock_version: str,
    test_end: str,
    fiinpro_xlsx: str,
    fiinpro_sha256: str,
) -> pd.DataFrame:
    """Sinh Data Source Register — 2 nguồn: FiinPro (giá 30 mã) + vnstock/VCI (VN-Index)."""
    rows = [
        {
            "source_id": "FIINPRO_XLSX",
            "source_name": "FiinPro export — DE Dữ liệu giao dịch (Full_Prices.xlsx)",
            "url_or_path": fiinpro_xlsx,
            "coverage_from": "2016-01-04",
            "coverage_to": test_end,
            "fields": (
                "Open, High, Low, Close (giá gốc), Adj Close, AdjRatio, Volume/Value khớp lệnh, "
                "VolumeTT/ValueTT thoả thuận"
            ),
            "license": "FiinPro — dữ liệu thương mại, chỉ dùng nội bộ, không đưa lên repo công khai",
            "fallback_source": "-",
            "access_date": access_date,
            "version": f"sha256={fiinpro_sha256}",
            "notes": (
                "adjusted_close đã điều chỉnh mọi corporate action và neo theo ngày export "
                "(không phải ngày cuối dữ liệu) — không áp thêm registry, không dùng làm giá hiện "
                "tại. Export lại ⇒ toàn bộ adjusted_close lịch sử đổi ⇒ phải bump data_version."
            ),
        },
        {
            "source_id": "VNSTOCK_INDEX",
            "source_name": "vnstock (nguồn VCI) — VN-Index",
            "url_or_path": "vnstock.api.quote.Quote(symbol='VNINDEX', source='VCI')",
            "coverage_from": "2016-01-01",
            "coverage_to": test_end,
            "fields": "Open, High, Low, Close, Volume",
            "license": "vnstock — free, dữ liệu thật từ HOSE qua Vietcap (VCI)",
            "fallback_source": "custom market composite từ universe",
            "access_date": access_date,
            "version": f"vnstock={vnstock_version}",
            "notes": (
                "Tải theo từng năm (API trả tối đa ~2.000 phiên/lần). Dùng làm lịch giao dịch "
                "chuẩn; fetch dừng nếu thiếu phiên so với FiinPro."
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
    """Ghi `universe_30_asof_{YYYYMMDD}.csv` (tên bắt buộc theo `workflow_update` Data Gate, TL-001)
    và `source_register.csv`."""
    metadata_dir = Path(metadata_dir)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    as_of_tag = pd.to_datetime(universe_as_of).strftime("%Y%m%d")
    universe_30_path = metadata_dir / f"universe_30_asof_{as_of_tag}.csv"
    sources_path = metadata_dir / "source_register.csv"

    universe.to_csv(universe_30_path, index=False, encoding="utf-8-sig")
    sources.to_csv(sources_path, index=False, encoding="utf-8-sig")
    return universe_30_path, sources_path
