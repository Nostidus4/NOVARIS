# Nguyễn Đỗ Minh Anh - báo cáo bằng chứng adjusted close theo từng mã (TL-002).
"""Sinh `adjusted_close_evidence_report.csv` — không gán im lặng close = adjusted_close.

Decision-package TL-002: baseline không chấp nhận tự gán close=adjusted_close. Report này ghi
rõ method/evidence_flag từng mã để Data Gate và Product Owner review.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd


def build_adjusted_close_evidence_report(
    universe: pd.DataFrame,
    corporate_actions: Sequence[Mapping[str, Any]] | None = None,
) -> pd.DataFrame:
    """Trả 1 dòng / ticker với method, evidence_flag và notes audit được.

    Flags:
    - ``ADJ_REGISTERED`` — có corporate action đã đăng ký thủ công trong configs/data.yaml;
    - ``ADJ_VENDOR`` — nguồn Yahoo (có Adj Close vendor), chưa có cross-check owner;
    - ``ADJ_UNVERIFIED`` — nguồn DNSE (giả định Close≈Adj Close theo repo hiện tại) hoặc mã
      cold-start / cần verify trước UAT.
    """
    actions = list(corporate_actions or [])
    registered = {
        str(item["ticker"]): item
        for item in actions
        if isinstance(item, Mapping) and item.get("ticker")
    }
    rows: list[dict[str, object]] = []
    for row in universe.itertuples(index=False):
        ticker = str(row.ticker)
        source = str(row.data_source)
        notes = str(getattr(row, "notes", "") or "")
        if ticker in registered:
            action = registered[ticker]
            rows.append(
                {
                    "ticker": ticker,
                    "data_source": source,
                    "method": "registered_corporate_action_back_adjust",
                    "evidence_flag": "ADJ_REGISTERED",
                    "event_date": action.get("event_date"),
                    "adjustment_factor": action.get("adjustment_factor"),
                    "evidence": action.get("evidence"),
                    "notes": notes,
                    "baseline_ok": False,
                    "limitation": (
                        "Registered adjustment is documented but Data Gate still requires "
                        "owner sign-off before BASELINE_TARGET."
                    ),
                }
            )
            continue
        if source == "yahoo":
            rows.append(
                {
                    "ticker": ticker,
                    "data_source": source,
                    "method": "vendor_adjusted_close",
                    "evidence_flag": "ADJ_VENDOR",
                    "event_date": None,
                    "adjustment_factor": None,
                    "evidence": "Yahoo Finance Adj Close field via yfinance",
                    "notes": notes,
                    "baseline_ok": False,
                    "limitation": (
                        "Vendor Adj Close present; Decision-package TL-002 still requires "
                        "explicit adjusted-close/corporate-action evidence or approved "
                        "cross-check before baseline."
                    ),
                }
            )
            continue
        rows.append(
            {
                "ticker": ticker,
                "data_source": source,
                "method": "dnse_close_assumed_adjusted",
                "evidence_flag": "ADJ_UNVERIFIED",
                "event_date": None,
                "adjustment_factor": None,
                "evidence": None,
                "notes": notes,
                "baseline_ok": False,
                "limitation": (
                    "DNSE path currently assumes Close approximates Adj Close. "
                    "TL-002 forbids silent close=adjusted_close for baseline."
                ),
            }
        )
    return pd.DataFrame(rows)


def write_adjusted_close_evidence_report(frame: pd.DataFrame, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path
