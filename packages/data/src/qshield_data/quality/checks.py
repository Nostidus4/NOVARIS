# Nguyễn Đỗ Minh Anh - duplicate, missing, outlier, leakage, overlap.
"""Data Quality Gate — port từ `CLEAN.ipynb` (6 check DQ-001..DQ-006, `PR-DAT-*`/`AC-DAT-*`).

Mỗi check trả về `dict` (`check_id, check_name, type, status, count, trace`) — `run_all_checks`
gộp thành DataFrame và cờ `all_pass` (chỉ tính trên check `type == "MUST_PASS"`, theo đúng gate
`GATE-02 Data` ở `docs/product/rtm.md`).
"""

from __future__ import annotations

import pandas as pd


def check_no_duplicates(prices: pd.DataFrame) -> dict:
    """DQ-001 — `(date, ticker)` phải unique (AC-DAT-004, PR-DAT-006)."""
    n_dup = int(prices.duplicated(subset=["date", "ticker"]).sum())
    return {
        "check_id": "DQ-001",
        "check_name": "No duplicate (date, ticker)",
        "type": "MUST_PASS",
        "status": "PASS" if n_dup == 0 else "FAIL",
        "count": n_dup,
        "trace": "AC-DAT-004, PR-DAT-006",
    }


def check_positive_prices(prices: pd.DataFrame) -> dict:
    """DQ-002 — `adjusted_close` phải dương và không NaN (AC-DAT-005, PR-DAT-007)."""
    n_neg = int((prices["adjusted_close"] <= 0).sum() + prices["adjusted_close"].isna().sum())
    return {
        "check_id": "DQ-002",
        "check_name": "adjusted_close > 0 và không NaN",
        "type": "MUST_PASS",
        "status": "PASS" if n_neg == 0 else "WARN",
        "count": n_neg,
        "trace": "AC-DAT-005, PR-DAT-007",
    }


def check_no_negative_volume(prices: pd.DataFrame) -> dict:
    """DQ-003 — không có volume âm."""
    n_negvol = int((prices["volume"] < 0).sum())
    return {
        "check_id": "DQ-003",
        "check_name": "Không có volume âm",
        "type": "MUST_PASS",
        "status": "PASS" if n_negvol == 0 else "FAIL",
        "count": n_negvol,
        "trace": "AC-DAT-005",
    }


def check_no_pre_listing(prices: pd.DataFrame, universe: pd.DataFrame) -> dict:
    """DQ-004 — không có giá trước `first_trading_date` (AC-DAT-011, PR-DAT-017)."""
    merged = prices.merge(universe[["ticker", "first_trading_date"]], on="ticker")
    merged["first_trading_date"] = pd.to_datetime(merged["first_trading_date"])
    n_pre = int((merged["date"] < merged["first_trading_date"]).sum())
    return {
        "check_id": "DQ-004",
        "check_name": "Không có giá trước first_trading_date",
        "type": "MUST_PASS",
        "status": "PASS" if n_pre == 0 else "FAIL",
        "count": n_pre,
        "trace": "AC-DAT-011, PR-DAT-017",
    }


def check_universe_count(universe: pd.DataFrame, expected: int) -> dict:
    """DQ-005 — universe khớp số mã đã khóa (AC-DAT-001, PR-DAT-001).

    `expected` PHẢI truyền từ `configs/universe.yaml["expected_ticker_count"]` — không hard-code
    (universe hiện tại đang khóa 8 mã theo CLAUDE.md, không phải 30 như thiết kế PSS/PRS gốc).
    """
    n_uni = len(universe)
    return {
        "check_id": "DQ-005",
        "check_name": f"Universe = {expected} tickers",
        "type": "MUST_PASS",
        "status": "PASS" if n_uni == expected else "FAIL",
        "count": n_uni,
        "trace": "AC-DAT-001, PR-DAT-001",
    }


def check_split_no_overlap(returns: pd.DataFrame) -> dict:
    """DQ-006 — train/validation/test không giao nhau (AC-DAT-009, PR-DAT-013).

    `returns` phải có cột `split`.
    """
    splits_ok = True
    splits_present = [s for s in ("train", "validation", "test") if (returns["split"] == s).any()]
    date_sets = {s: set(returns.loc[returns["split"] == s, "date"]) for s in splits_present}
    for i, a in enumerate(splits_present):
        for b in splits_present[i + 1 :]:
            if date_sets[a] & date_sets[b]:
                splits_ok = False
    return {
        "check_id": "DQ-006",
        "check_name": "Train/Val/Test không giao nhau",
        "type": "MUST_PASS",
        "status": "PASS" if splits_ok else "FAIL",
        "count": 0,
        "trace": "AC-DAT-009, PR-DAT-013",
    }


def run_all_checks(
    prices: pd.DataFrame,
    universe: pd.DataFrame,
    returns: pd.DataFrame,
    expected_universe_count: int,
) -> tuple[pd.DataFrame, bool]:
    """Chạy toàn bộ 6 check, trả `(report_df, all_pass)`.

    `all_pass` chỉ tính trên các check `type == "MUST_PASS"` — đúng theo `GATE-02 Data`
    (`docs/product/rtm.md` §3).
    """
    checks = [
        check_no_duplicates(prices),
        check_positive_prices(prices),
        check_no_negative_volume(prices),
        check_no_pre_listing(prices, universe),
        check_universe_count(universe, expected_universe_count),
        check_split_no_overlap(returns),
    ]
    report_df = pd.DataFrame(checks)
    must_pass = report_df[report_df["type"] == "MUST_PASS"]
    all_pass = bool((must_pass["status"] == "PASS").all())
    return report_df, all_pass
