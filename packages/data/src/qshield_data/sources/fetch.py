# Nguyễn Đỗ Minh Anh - nạp giá 30 mã từ FiinPro + tải VN-Index.
"""Orchestration nạp giá cho toàn bộ universe + VN-Index.

Port từ `CLEAN.ipynb` bản 2026-09-17: giá cổ phiếu KHÔNG còn tải qua API (Yahoo/DNSE) mà tách từ
file export FiinPro `Full_Prices.xlsx`; VN-Index vẫn tải qua vnstock (VCI). Xem
`docs/data/2026-09-17-chuyen-nguon-gia-fiinpro.md`.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from qshield_data.manifest import _sha256_of_file
from qshield_data.sources.loaders import fiinpro as fiinpro_loader
from qshield_data.sources.loaders import vnstock as vnstock_loader

logger = logging.getLogger(__name__)


def split_fiinpro_prices(
    universe: pd.DataFrame,
    xlsx_path: Path,
    raw_dir: Path,
    raw_price_patches: Sequence[Mapping[str, Any]] = (),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Đọc `Full_Prices.xlsx`, áp patch, tách mỗi mã universe thành `{ngày}_fiinpro_{mã}.csv`.

    Mã có trong universe nhưng không có trong file ⇒ dòng manifest `status=FAILED` (không raise, để
    DQ gate báo đủ số mã). Mã có trong file nhưng ngoài universe ⇒ bỏ qua, log warning.

    Trả về `(raw_manifest, full_df)` — `full_df` (đã patch) dùng để kiểm tra lịch VN-Index.
    Cột manifest: ticker, symbol, source, file, rows, start, end, sha256, status.
    """
    raw_dir = Path(raw_dir)
    today_tag = datetime.now().astimezone().strftime("%Y%m%d")

    full_df = fiinpro_loader.read_full_prices(xlsx_path)
    full_df, _ = fiinpro_loader.apply_raw_price_patches(full_df, raw_price_patches)

    uni, in_file = set(universe["ticker"]), set(full_df["ticker"])
    if uni - in_file:
        logger.warning(
            "Có trong universe nhưng KHÔNG có trong FiinPro: %s", sorted(uni - in_file)
        )
    if in_file - uni:
        logger.warning(
            "Có trong FiinPro nhưng ngoài universe (bỏ qua): %s", sorted(in_file - uni)
        )

    out_dir = raw_dir / "prices"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for ticker in universe["ticker"]:
        sub = full_df[full_df["ticker"] == ticker]
        if sub.empty:
            manifest.append(
                {
                    "ticker": ticker,
                    "symbol": ticker,
                    "source": fiinpro_loader.SOURCE_ID,
                    "file": None,
                    "rows": 0,
                    "start": None,
                    "end": None,
                    "sha256": None,
                    "status": "FAILED",
                }
            )
            continue
        sub = (
            sub.sort_values(["date", "Volume"], na_position="first")
            .drop_duplicates("date", keep="last")
            .set_index("date")[fiinpro_loader.RAW_CSV_COLUMNS]
        )
        fpath = out_dir / f"{today_tag}_fiinpro_{ticker.lower()}.csv"
        sub.to_csv(fpath)
        manifest.append(
            {
                "ticker": ticker,
                "symbol": ticker,
                "source": fiinpro_loader.SOURCE_ID,
                "file": str(fpath),
                "rows": len(sub),
                "start": sub.index.min().strftime("%Y-%m-%d"),
                "end": sub.index.max().strftime("%Y-%m-%d"),
                "sha256": _sha256_of_file(fpath),
                "status": "OK",
            }
        )
    return pd.DataFrame(manifest), full_df


def fetch_vn_index(start: str, end: str, raw_dir: Path) -> pd.DataFrame | None:
    """Tải VN-Index từ vnstock (VCI) và ghi `raw_dir/vn_index/{ngày}_vnstock_VCI_vnindex.csv`.

    Trả về `None` nếu không tải được — chặng clean bỏ qua lọc lịch giao dịch, chặng features tự
    dựng custom composite.
    """
    df = vnstock_loader.download_vnindex(start=start, end=end)
    if df is None or len(df) <= 100:
        logger.warning("VN-Index không tải được từ vnstock (VCI).")
        return None
    today_tag = datetime.now().astimezone().strftime("%Y%m%d")
    fpath = Path(raw_dir) / "vn_index" / f"{today_tag}_vnstock_VCI_vnindex.csv"
    fpath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(fpath)
    logger.info("Saved VN-Index: %s (%d phiên)", fpath, len(df))
    return df


def missing_index_sessions(
    price_dates: pd.Series, index_df: pd.DataFrame, start: str, end: str
) -> pd.DatetimeIndex:
    """Các phiên có giá cổ phiếu (trong [start, end]) nhưng VN-Index không có.

    Lịch VN-Index được dùng ở bước clean để loại ngày không giao dịch thật — nếu API trả thiếu
    ngày, bước đó sẽ XOÁ NHẦM giá thật. Caller phải dừng khi kết quả khác rỗng.
    """
    days = pd.DatetimeIndex(pd.to_datetime(price_dates).unique())
    days = days[(days >= pd.Timestamp(start)) & (days <= pd.Timestamp(end))]
    return days.difference(pd.DatetimeIndex(index_df.index)).sort_values()
