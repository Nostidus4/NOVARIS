# Nguyễn Đỗ Minh Anh - consumer API cho Tú/Phúc (file mới, xem plan.md §3.6/§6 câu 4).
"""Consumer API — thay cho `sample_loader.py` đứng riêng cạnh `data/` như trong `CLEAN.ipynb` Cell
56.

Đặt trong package (`from qshield_data.loader import load_data`) thay vì một script standalone, vì
đây là một phần giao diện chính thức của `qshield_data` cho Tú/Phúc dùng, không phải code demo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import pandas as pd

Table = Literal["universe", "prices", "returns", "market_features", "eligibility"]

_TABLE_FILENAME: dict[str, str] = {
    "prices": "prices_adjusted.parquet",
    "returns": "returns.parquet",
    "market_features": "market_features.parquet",
    "eligibility": "eligibility_daily.parquet",
}


def load_data(
    table: Table,
    split: str | None = None,
    date: str | None = None,
    tickers: list[str] | None = None,
    data_root: Path | None = None,
) -> pd.DataFrame:
    """Đọc một bảng đã processed, lọc theo `split`/`date`/`tickers` nếu có.

    `table == "universe"`: ưu tiên snapshot Data Gate `universe_30_asof_*.csv`, rồi mới fallback
    alias legacy `universe_asof_*.csv`. Các bảng khác đọc từ `data/processed/<table>.parquet`.

    Raise `FileNotFoundError` nếu bảng chưa được sinh ra (chưa chạy `qshield-data` đến bước đó).
    """
    data_root = Path(data_root) if data_root is not None else Path("data")

    if table == "universe":
        metadata = data_root / "metadata"
        candidates = sorted(metadata.glob("universe_30_asof_*.csv"))
        if not candidates:
            candidates = sorted(metadata.glob("universe_asof_*.csv"))
        if not candidates:
            raise FileNotFoundError(
                "Không tìm thấy universe_30_asof_*.csv hoặc universe_asof_*.csv trong "
                f"{metadata} "
                "— đã chạy `qshield-data fetch` chưa?"
            )
        df = pd.read_csv(candidates[-1])
    else:
        try:
            fname = _TABLE_FILENAME[table]
        except KeyError:
            raise ValueError(
                f"table='{table}' không hợp lệ — phải thuộc {{'universe', 'prices', 'returns', "
                "'market_features', 'eligibility'}}"
            ) from None
        path = data_root / "processed" / fname
        if not path.exists():
            raise FileNotFoundError(
                f"{path} chưa tồn tại — đã chạy đủ bước qshield-data chưa?"
            )
        df = pd.read_parquet(path)

    if split is not None and "split" in df.columns:
        df = df[df["split"] == split]
    if date is not None and "date" in df.columns:
        df = df[pd.to_datetime(df["date"]) == pd.to_datetime(date)]
    if tickers is not None and "ticker" in df.columns:
        df = df[df["ticker"].isin(tickers)]

    return df.reset_index(drop=True)


def get_manifest(data_root: Path | None = None) -> dict[str, Any]:
    """Đọc `data/metadata/data_manifest.json`. Raise `FileNotFoundError` nếu chưa có (chưa chạy
    `qshield-data manifest`)."""
    data_root = Path(data_root) if data_root is not None else Path("data")
    path = data_root / "metadata" / "data_manifest.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} chưa tồn tại — đã chạy `qshield-data manifest` chưa?"
        )
    return json.loads(path.read_text(encoding="utf-8"))
