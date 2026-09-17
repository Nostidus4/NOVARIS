# Nguyễn Đỗ Minh Anh / Mạnh - loader giá 30 mã từ file export FiinPro (Full_Prices.xlsx).
"""FiinPro loader — port từ `CLEAN.ipynb` bản 2026-09-17 (PR-DAT-020, PR-DAT-021).

Nguồn giá DUY NHẤT cho cổ phiếu (thay Yahoo + DNSE). File export FiinPro "DE - Dữ liệu giao dịch"
có đủ thứ hai nguồn API cũ thiếu:

- `Open/High/Low/Close` là giá GỐC khớp trên sàn; `Adj Close` là giá đóng cửa ĐÃ điều chỉnh;
- `Value` là giá trị khớp lệnh thật (không phải ước lượng close × volume);
- `VolumeTT/ValueTT` là giao dịch thoả thuận.

Lưu ý (xem `docs/data/2026-09-17-chuyen-nguon-gia-fiinpro.md` §2):

- `adjusted_close` đã điều chỉnh sẵn mọi corporate action ⇒ KHÔNG áp thêm registry nào (sẽ điều
  chỉnh hai lần).
- `adjusted_close` neo theo ngày export, không phải ngày cuối dữ liệu ⇒ không dùng làm "giá hiện
  tại"; dùng `close`.
- Chỉ giá đóng cửa có bản điều chỉnh; `open/high/low` là giá gốc.
- Cột `AdjRatio` chỉ giữ ở CSV raw để tra cứu (FiinPro bỏ sót sự kiện, vd FPT 2018-05-25).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

SOURCE_ID = "FIINPRO_XLSX"

# Prefix tiếng Việt → tên nội bộ. Prefix match để không vỡ khi FiinPro đổi phần "Đơn vị: ..." phía
# sau. Thứ tự quan trọng: "Giá đóng cửa điều chỉnh" phải đứng TRƯỚC "Giá đóng cửa".
_COLMAP = {
    "Mã": "ticker",
    "Tên công ty": "company",
    "Ngày": "date",
    "Giá mở cửa": "Open",
    "Giá cao nhất": "High",
    "Giá thấp nhất": "Low",
    "Giá đóng cửa điều chỉnh": "Adj Close",
    "Giá đóng cửa": "Close",
    "Tỷ lệ điều chỉnh": "AdjRatio",
    "Khối lượng khớp lệnh": "Volume",
    "Giá trị khớp lệnh": "Value",
    "Khối lượng thỏa thuận": "VolumeTT",
    "Giá trị thỏa thuận": "ValueTT",
}
_NUMERIC_COLS = [
    "Open",
    "High",
    "Low",
    "Close",
    "Adj Close",
    "AdjRatio",
    "Volume",
    "Value",
    "VolumeTT",
    "ValueTT",
]
RAW_CSV_COLUMNS = [
    "Open",
    "High",
    "Low",
    "Close",
    "Adj Close",
    "Volume",
    "Value",
    "VolumeTT",
    "ValueTT",
    "AdjRatio",
]


def read_full_prices(xlsx_path: Path) -> pd.DataFrame:
    """Đọc `Full_Prices.xlsx` → DataFrame long (1 dòng / ticker × ngày), cột theo `_COLMAP`.

    Tự dò dòng header (file export có vài dòng metadata ở đầu) và bỏ footer rác (thông tin liên hệ
    FiinGroup — các dòng không có mã). Raise `ValueError` nếu không dò được header hoặc thiếu cột.
    """
    xlsx_path = Path(xlsx_path)
    if not xlsx_path.exists():
        raise FileNotFoundError(
            f"Không thấy file FiinPro {xlsx_path} — đặt Full_Prices.xlsx vào đúng đường dẫn "
            "`data.fiinpro_xlsx` trong configs/base.yaml."
        )
    raw = pd.read_excel(xlsx_path, sheet_name=0, header=None)
    hdr_rows = raw.index[raw[1].astype(str).str.strip() == "Mã"]
    if len(hdr_rows) != 1:
        raise ValueError(
            f"{xlsx_path}: không dò được dòng header (thấy {len(hdr_rows)} dòng có cột 'Mã')."
        )
    hdr = hdr_rows[0]

    df = raw.iloc[hdr + 1 :].copy()
    df.columns = [str(x).replace("\n", " ").strip() for x in raw.iloc[hdr]]
    df = df.reset_index(drop=True)

    rename: dict[str, str] = {}
    seen: set[str] = set()
    for col in df.columns:
        for prefix, name in _COLMAP.items():
            if col.startswith(prefix) and name not in seen:
                rename[col] = name
                seen.add(name)
                break
    df = df.rename(columns=rename)
    missing = set(_COLMAP.values()) - set(df.columns)
    if missing:
        raise ValueError(
            f"{xlsx_path}: thiếu cột sau khi map tên FiinPro: {sorted(missing)}"
        )

    n_before = len(df)
    df = df[df["ticker"].notna()].copy()
    logger.info(
        "FiinPro: bỏ %d dòng footer/rác → %d dòng dữ liệu", n_before - len(df), len(df)
    )

    df["date"] = pd.to_datetime(df["date"])
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    for col in _NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def apply_raw_price_patches(
    full_df: pd.DataFrame, patches: Sequence[Mapping[str, Any]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Vá lỗi nằm ngay trong file Excel (PR-DAT-021), áp lúc TÁCH file để CSV raw ghi ra đã đúng.

    Mỗi patch: `{ticker, date, <cột raw>: giá trị, reason, verified_against, verified_on}` — khai
    báo trong `configs/base.yaml → data.raw_price_patches`. Chỉ ghi các cột có trong
    `RAW_CSV_COLUMNS`. Patch không khớp đúng 1 dòng ⇒ raise (không bỏ qua im lặng).

    Trả về `(df_patched, patch_log)`.
    """
    out = full_df.copy()
    log: list[dict[str, Any]] = []
    for patch in patches:
        ticker, date = str(patch["ticker"]), pd.Timestamp(patch["date"])
        mask = (out["ticker"] == ticker) & (out["date"] == date)
        if int(mask.sum()) != 1:
            raise ValueError(
                f"raw_price_patches {ticker} {date.date()}: khớp {int(mask.sum())} dòng "
                "(kỳ vọng 1) — sửa configs/base.yaml (data.raw_price_patches)."
            )
        for col, value in patch.items():
            if col not in RAW_CSV_COLUMNS:
                continue
            old = out.loc[mask, col].iloc[0]
            out.loc[mask, col] = value
            logger.warning(
                "FiinPro patch %s %s %s: %s → %s (%s)",
                ticker,
                date.date(),
                col,
                old,
                value,
                patch.get("reason"),
            )
            log.append(
                {
                    "ticker": ticker,
                    "date": date.strftime("%Y-%m-%d"),
                    "column": col,
                    "old_value": old,
                    "new_value": value,
                    "reason": patch.get("reason"),
                    "verified_against": patch.get("verified_against"),
                    "verified_on": patch.get("verified_on"),
                }
            )
    return out, pd.DataFrame(log)
