# Nguyễn Đỗ Minh Anh - duplicate, missing, outlier, leakage, overlap.
"""Data Quality Gate — port từ `CLEAN.ipynb` (7 check DQ-001..DQ-007, `PR-DAT-*`/`AC-DAT-*`).

Mỗi check trả về `dict` (`check_id, check_name, type, status, count, trace`) — `run_all_checks`
gộp thành DataFrame và cờ `all_pass` (chỉ tính trên check `type == "MUST_PASS"`, theo đúng gate
`GATE-02 Data` ở `docs/product/rtm.md`).
"""

from __future__ import annotations

import pandas as pd

from qshield_data.quality.price_limits import _VIOLATION_COLUMNS


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
    n_neg = int(
        (prices["adjusted_close"] <= 0).sum() + prices["adjusted_close"].isna().sum()
    )
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
    splits_present = [
        s for s in ("train", "validation", "test") if (returns["split"] == s).any()
    ]
    date_sets = {
        s: set(returns.loc[returns["split"] == s, "date"]) for s in splits_present
    }
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


def check_price_limit(violations: pd.DataFrame) -> dict:
    """DQ-007 — return ngày vượt biên độ dao động của sàn.

    Nhận sẵn khung vi phạm đã tính (`quality.price_limits.find_price_limit_violations`) thay vì tự
    tính, để công việc chỉ chạy đúng một lần và module này giữ nguyên vai trò đăng ký check.

    `type="WARN"`: check này KHÔNG chặn gate. Trên dữ liệu hiện tại nó bắn 24 dòng mà mới chỉ một
    dòng (VCB 2025-03-03) là bất khả thi thật sự; để MUST_PASS sẽ chặn mọi lần chạy data trong khi
    23 dòng còn lại chưa ai phân loại. Nâng lên MUST_PASS khi việc sửa dữ liệu hoàn tất.

    `trace` trỏ tới doc điều tra vì chưa có requirement id nào phủ kiểm tra biên độ giá — việc
    đăng ký id trong `docs/product/rtm.md` thuộc Minh Anh và Ngọc.

    Raise `ValueError` nếu `violations` thiếu cột — tránh nhận nhầm khung khác (vd. `returns`
    thô) rồi vẫn báo một `WARN` có vẻ hợp lý bằng `len()` của nó (CLAUDE.md quy tắc 12).
    """
    missing = [c for c in _VIOLATION_COLUMNS if c not in violations.columns]
    if missing:
        raise ValueError(
            f"violations thiếu cột {missing} — không phải khung từ "
            "quality.price_limits.find_price_limit_violations. Cột hiện có: "
            f"{list(violations.columns)}."
        )
    n_violations = len(violations)
    return {
        "check_id": "DQ-007",
        "check_name": "Return ngày trong biên độ sàn",
        "type": "WARN",
        "status": "PASS" if n_violations == 0 else "WARN",
        "count": n_violations,
        "trace": "docs/perf/2026-08-05-kurtosis-fail-vcb.md",
    }


def run_all_checks(
    prices: pd.DataFrame,
    universe: pd.DataFrame,
    returns: pd.DataFrame,
    expected_universe_count: int,
    price_limit_violations: pd.DataFrame,
) -> tuple[pd.DataFrame, bool]:
    """Chạy toàn bộ 7 check, trả `(report_df, all_pass)`.

    `all_pass` chỉ tính trên các check `type == "MUST_PASS"` — đúng theo `GATE-02 Data`
    (`docs/product/rtm.md` §3). DQ-007 là `WARN` nên không ảnh hưởng `all_pass`.

    `price_limit_violations` là tham số BẮT BUỘC, không có mặc định: một mặc định "rỗng" sẽ khiến
    DQ-007 báo PASS mỗi khi caller quên nối dây — âm tính giả im lặng ở đúng cái check sinh ra để
    bắt lỗi im lặng.
    """
    checks = [
        check_no_duplicates(prices),
        check_positive_prices(prices),
        check_no_negative_volume(prices),
        check_no_pre_listing(prices, universe),
        check_universe_count(universe, expected_universe_count),
        check_split_no_overlap(returns),
        check_price_limit(price_limit_violations),
    ]
    report_df = pd.DataFrame(checks)
    must_pass = report_df[report_df["type"] == "MUST_PASS"]
    all_pass = bool((must_pass["status"] == "PASS").all())
    return report_df, all_pass
