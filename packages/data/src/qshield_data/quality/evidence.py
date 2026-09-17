# Nguyễn Đỗ Minh Anh - báo cáo bằng chứng adjusted close theo từng mã (TL-002).
"""Sinh `adjusted_close_evidence_report.csv` — không gán im lặng close = adjusted_close.

Decision-package TL-002: baseline không chấp nhận tự gán close=adjusted_close. Report này ghi
rõ method/evidence_flag từng mã để Data Gate và Product Owner review.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_adjusted_close_evidence_report(universe: pd.DataFrame) -> pd.DataFrame:
    """Trả 1 dòng / ticker với method, evidence_flag và notes audit được.

    Flags:
    - ``ADJ_VENDOR`` — nguồn FiinPro: `adjusted_close` là cột "Giá đóng cửa điều chỉnh" của vendor,
      có giá gốc đi kèm để đối chiếu; vẫn cần Data Owner sign-off trước baseline;
    - ``ADJ_UNVERIFIED`` — nguồn khác (không kỳ vọng xuất hiện).
    """
    rows: list[dict[str, object]] = []
    for row in universe.itertuples(index=False):
        source = str(row.data_source)
        is_fiinpro = source == "fiinpro"
        rows.append(
            {
                "ticker": str(row.ticker),
                "data_source": source,
                "method": "vendor_adjusted_close" if is_fiinpro else "unknown",
                "evidence_flag": "ADJ_VENDOR" if is_fiinpro else "ADJ_UNVERIFIED",
                "evidence": (
                    "FiinPro 'Giá đóng cửa điều chỉnh' + giá gốc O/H/L/C cùng file"
                    if is_fiinpro
                    else None
                ),
                "notes": str(getattr(row, "notes", "") or ""),
                "baseline_ok": False,
                "limitation": (
                    "Vendor adjusted close; Decision-package TL-002 still requires Data Owner "
                    "sign-off before BASELINE_TARGET. Không áp thêm corporate action registry."
                ),
            }
        )
    return pd.DataFrame(rows)


def write_adjusted_close_evidence_report(frame: pd.DataFrame, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path
