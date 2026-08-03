# Nguyễn Đỗ Minh Anh - orchestration tải giá đa nguồn (Yahoo/DNSE/vnstock) — file mới, xem plan.md §3.2.
"""Orchestration tải giá cho toàn bộ universe + VN-Index.

Port từ `CLEAN.ipynb` (cell tải giá 30 mã có retry pass, và cell tải VN-Index ưu tiên
vnstock/fallback Yahoo). Không thuộc `registry.py` (đó là schema/metadata, không phải I/O) và
không thuộc một loader riêng (đây là logic *route* giữa các loader) — theo plan.md §3.2/§6 câu 3.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from qshield_data.manifest import _sha256_of_file
from qshield_data.sources.loaders import dnse as dnse_loader
from qshield_data.sources.loaders import vnstock as vnstock_loader
from qshield_data.sources.loaders import yahoo as yahoo_loader

logger = logging.getLogger(__name__)

_VNINDEX_YAHOO_CANDIDATES = ["^VNINDEX", "^VNI", "VNINDEX.VN"]


def _download_one(row: pd.Series, start: str, end: str, raw_dir: Path, today_tag: str) -> dict:
    """Tải giá 1 mã theo routing `row['data_source']` (dnse/yahoo), trả về manifest dict.

    Nếu `data_source == "dnse"`: thử DNSE/Entrade trước (nguồn chính, có full HNX/UPCOM history);
    fail thì fallback Yahoo (chỉ có HOSE, mất history trước ngày chuyển sàn — log rõ để không âm
    thầm mất dữ liệu).
    """
    ticker = row["ticker"]
    preferred_source = row["data_source"]
    first = pd.to_datetime(row["first_trading_date"])
    effective_start = max(pd.to_datetime(start), first).strftime("%Y-%m-%d")

    df = None
    actual_source = None
    symbol_used = None
    file_tag = None
    fallback_used = False

    if preferred_source == "dnse":
        df, _ = dnse_loader.download_ticker(ticker, start=effective_start, end=end)
        time.sleep(0.5)  # throttle nhẹ
        if df is not None:
            actual_source = "DNSE_PRICES"
            symbol_used = f"dnse:{ticker}"
            file_tag = "dnse"
        else:
            logger.warning("DNSE failed for %s — fallback về Yahoo (HOSE-only)", ticker)
            df = yahoo_loader.download_ticker(row["yahoo_symbol"], start=effective_start, end=end)
            actual_source = "YF_PRICES_FALLBACK"
            symbol_used = row["yahoo_symbol"]
            file_tag = "yfinance"
            fallback_used = True
    else:
        df = yahoo_loader.download_ticker(row["yahoo_symbol"], start=effective_start, end=end)
        actual_source = "YF_PRICES"
        symbol_used = row["yahoo_symbol"]
        file_tag = "yfinance"

    if df is None:
        return {
            "ticker": ticker,
            "symbol": symbol_used or "-",
            "source": actual_source or "UNKNOWN",
            "preferred": preferred_source,
            "fallback_used": fallback_used,
            "file": None,
            "rows": 0,
            "start": None,
            "end": None,
            "sha256": None,
            "status": "FAILED",
        }

    fname = f"{today_tag}_{file_tag}_{ticker.lower()}.csv"
    fpath = Path(raw_dir) / "prices" / fname
    fpath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(fpath)
    return {
        "ticker": ticker,
        "symbol": symbol_used,
        "source": actual_source,
        "preferred": preferred_source,
        "fallback_used": fallback_used,
        "file": str(fpath),
        "rows": len(df),
        "start": df.index.min().strftime("%Y-%m-%d"),
        "end": df.index.max().strftime("%Y-%m-%d"),
        "sha256": _sha256_of_file(fpath),
        "status": "OK",
    }


def fetch_all_prices(universe: pd.DataFrame, start: str, end: str, raw_dir: Path) -> pd.DataFrame:
    """Tải giá toàn bộ universe, route theo `universe['data_source']`.

    24 mã (giá trị `"yahoo"`) → Yahoo Finance. Mã `"dnse"` (multi-exchange) → DNSE/Entrade, fallback
    Yahoo nếu DNSE fail. Ghi CSV vào `raw_dir/prices/`. Có retry pass: mã nào FAILED ở lượt đầu
    (thường do timeout tạm thời khi tải dồn dập) được nghỉ 5 giây rồi thử lại thêm một lượt.

    Trả về `raw_manifest` DataFrame — cột: ticker, symbol, source, preferred, fallback_used, file,
    rows, start, end, sha256, status.
    """
    raw_dir = Path(raw_dir)
    today_tag = datetime.now().strftime("%Y%m%d")

    logger.info(
        "Downloading %d tickers from %s to %s (route: yahoo/dnse theo universe['data_source'])",
        len(universe),
        start,
        end,
    )

    raw_manifest = [
        _download_one(row, start, end, raw_dir, today_tag) for _, row in universe.iterrows()
    ]

    failed_tickers = [m["ticker"] for m in raw_manifest if m["status"] == "FAILED"]
    if failed_tickers:
        logger.warning("Retry pass cho %d mã fail: %s", len(failed_tickers), failed_tickers)
        time.sleep(5)
        for i, m in enumerate(raw_manifest):
            if m["status"] != "FAILED":
                continue
            row = universe.loc[universe["ticker"] == m["ticker"]].iloc[0]
            raw_manifest[i] = _download_one(row, start, end, raw_dir, today_tag)

    return pd.DataFrame(raw_manifest)


def fetch_vn_index(
    start: str, end: str, raw_dir: Path
) -> tuple[pd.DataFrame | None, str | None, str | None]:
    """Tải VN-Index — ưu tiên vnstock (VCI, dữ liệu thật từ HOSE), fallback Yahoo.

    Yahoo Finance không có VN-Index thật (`^VNINDEX`/`^VNI` không tồn tại trên Yahoo) nên chỉ giữ
    làm fallback. Ghi CSV vào `raw_dir/vn_index/`.

    Trả về `(df, symbol_used, source_used)`; `(None, None, None)` nếu cả hai nguồn đều fail — chặng
    sau (`features.build_market_features`) phải tự fallback sang custom composite trong trường hợp
    này.
    """
    raw_dir = Path(raw_dir)
    today_tag = datetime.now().strftime("%Y%m%d")

    logger.info("Trying VN-Index from vnstock (source=VCI)...")
    df = vnstock_loader.download_vnindex(start=start, end=end)
    if df is not None and len(df) > 100:
        symbol_used, source_used = "VNINDEX", "vnstock_VCI"
        logger.info("Got %d rows from vnstock (VNINDEX, source=VCI)", len(df))
    else:
        logger.warning("vnstock VNINDEX unavailable or too few rows")
        df, symbol_used, source_used = None, None, None
        for cand in _VNINDEX_YAHOO_CANDIDATES:
            logger.info("Trying VN-Index symbol: %s", cand)
            candidate_df = yahoo_loader.download_ticker(cand, start=start, end=end)
            if candidate_df is not None and len(candidate_df) > 100:
                df, symbol_used, source_used = candidate_df, cand, "yahoo"
                logger.info("Got %d rows from %s", len(candidate_df), cand)
                break
            logger.warning("%s unavailable or too few rows", cand)

    if df is None:
        logger.warning(
            "VN-Index unavailable từ vnstock lẫn Yahoo. "
            "Chặng features phải tự tính custom market composite từ universe."
        )
        return None, None, None

    idx_fname = f"{today_tag}_{source_used}_vnindex.csv"
    idx_fpath = raw_dir / "vn_index" / idx_fname
    idx_fpath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(idx_fpath)
    logger.info("Saved VN-Index: %s", idx_fpath)
    return df, symbol_used, source_used
