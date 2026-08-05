# Nguyễn Anh Tú - phát hiện biến động vượt biên độ sàn (DQ-007), phát hiện thôi, không sửa.
"""Phát hiện return ngày vượt biên độ dao động của sàn.

Động cơ: `docs/perf/2026-08-05-kurtosis-fail-vcb.md` — VCB 2025-03-03 có return −33,11% trong khi
HOSE giới hạn ±7%. Đó là sự kiện doanh nghiệp chưa điều chỉnh, không phải biến động giá, và nó đi
lọt toàn bộ cổng chất lượng dữ liệu.

Module thuần: không đọc config, không chạm đĩa, ngưỡng truyền vào tường minh. CLAUDE.md quy tắc 5 —
ở đây chỉ GẮN CỜ, không bao giờ xoá hay sửa giá trị return.

Biên độ phụ thuộc SÀN và SÀN phụ thuộc NGÀY: ACB niêm yết HNX (±10%) tới 2020-11, sau đó chuyển
HOSE (±7%). Dùng `exchange_current` cho toàn bộ lịch sử sẽ báo nhầm 12 phiên ACB hợp lệ.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

_VIOLATION_COLUMNS = [
    "date",
    "ticker",
    "exchange",
    "simple_return",
    "band",
    "tolerance",
    "excess",
]


def _periods_by_ticker(
    universe: pd.DataFrame,
) -> dict[str, Sequence[Mapping[str, Any]]]:
    """`ticker -> exchange_periods`, báo lỗi ngay nếu thiếu hoặc rỗng."""
    if "exchange_periods" not in universe.columns:
        raise ValueError(
            "universe thiếu cột 'exchange_periods' — không resolve được sàn theo ngày. "
            "Thêm trường này vào configs/universe.yaml (xem registry._UNIVERSE_COLUMNS)."
        )
    out: dict[str, Sequence[Mapping[str, Any]]] = {}
    for row in universe.itertuples(index=False):
        periods = row.exchange_periods
        if periods is None or len(periods) == 0:
            raise ValueError(
                f"Ticker {row.ticker!r} có exchange_periods rỗng trong configs/universe.yaml — "
                "không suy ra được biên độ. Không có fallback theo thiết kế."
            )
        out[str(row.ticker)] = periods
    return out


def resolve_exchange_column(returns: pd.DataFrame, universe: pd.DataFrame) -> pd.Series:
    """Sàn đang áp dụng cho mỗi dòng của `returns`, theo `(ticker, date)`.

    `from`/`until` trong mỗi period đều là biên ĐÓNG. Thiếu `from` = từ lúc niêm yết, thiếu
    `until` = tới hiện tại.

    Raise `ValueError` khi ticker lạ, period rỗng, ngày rơi vào khoảng trống, hoặc period chồng
    lấn — không bao giờ đoán một sàn mặc định (CLAUDE.md quy tắc 12).
    """
    periods_by_ticker = _periods_by_ticker(universe)
    dates = pd.to_datetime(returns["date"])
    resolved = pd.Series(pd.NA, index=returns.index, dtype="object")

    for ticker in returns["ticker"].astype(str).unique():
        if ticker not in periods_by_ticker:
            raise ValueError(
                f"Ticker {ticker!r} có trong returns nhưng không có trong universe — "
                f"không resolve được sàn. Universe hiện có: {sorted(periods_by_ticker)}."
            )
        is_ticker = returns["ticker"].astype(str) == ticker
        hits = pd.Series(0, index=returns.index, dtype=int)

        for period in periods_by_ticker[ticker]:
            in_period = is_ticker.copy()
            start = period.get("from")
            end = period.get("until")
            if start is not None:
                in_period &= dates >= pd.Timestamp(start)
            if end is not None:
                in_period &= dates <= pd.Timestamp(end)
            hits += in_period.astype(int)
            resolved[in_period] = str(period["exchange"])

        overlapping = is_ticker & (hits > 1)
        if overlapping.any():
            first = dates[overlapping].min().date()
            raise ValueError(
                f"exchange_periods của {ticker!r} chồng lấn tại {first} — "
                f"một ngày khớp {int(hits[overlapping].max())} period. Sửa configs/universe.yaml."
            )
        missing = is_ticker & (hits == 0)
        if missing.any():
            first = dates[missing].min().date()
            raise ValueError(
                f"Ticker {ticker!r}: ngày {first} không rơi vào exchange_periods nào — "
                "lịch sử sàn có khoảng trống. Sửa configs/universe.yaml."
            )

    return resolved


def find_price_limit_violations(
    returns: pd.DataFrame,
    universe: pd.DataFrame,
    *,
    bands_by_exchange: Mapping[str, float],
    tolerance_pct: float,
) -> pd.DataFrame:
    """Các dòng có `|simple_return|` vượt biên độ sàn cộng dung sai.

    Vi phạm khi `abs(simple_return) > band + tolerance_pct` — bất đẳng thức NGẶT, giá trị đúng
    bằng biên không tính là vi phạm.

    Cột `excess` đo so với `band` (biên độ danh nghĩa) mà thôi, KHÔNG so với ngưỡng phát hiện
    `band + tolerance_pct` — mọi dòng bị gắn cờ vẫn có `excess > tolerance_pct`, nhưng đừng đọc
    `excess` là "vượt ngưỡng phát hiện bao nhiêu".

    Kết quả sắp theo `excess` giảm dần, khóa phụ `(date, ticker)` tăng dần để các dòng bằng
    `excess` có thứ tự xác định, lặp lại được giữa các lần chạy — không dựa vào tính ổn định của
    thuật toán sắp xếp mặc định.

    `simple_return` NaN được BỎ QUA: không phải vi phạm, cũng không phải lỗi. Phiên đầu tiên của
    mỗi mã không có giá trước đó nên luôn NaN (8 dòng trong returns.parquet hiện tại). Lọc tường
    minh, không dựa vào việc `NaN > x` cho `False` — đúng kết quả nhưng sai lý do, và sẽ hỏng âm
    thầm nếu phép so sánh được viết lại.

    Trả DataFrame RỖNG đúng cột khi sạch, không bao giờ `None` — caller không phải rẽ nhánh.
    """
    if tolerance_pct < 0:
        raise ValueError(
            f"tolerance_pct phải >= 0, nhận {tolerance_pct} "
            "(configs/data.yaml: price_limits.tolerance_pct)."
        )
    for exchange, band in bands_by_exchange.items():
        if band <= 0:
            raise ValueError(
                f"Biên độ của sàn {exchange!r} phải > 0, nhận {band} "
                "(configs/data.yaml: price_limits.bands_by_exchange)."
            )

    exchange_col = resolve_exchange_column(returns, universe)
    unknown = sorted(set(exchange_col.dropna()) - set(bands_by_exchange))
    if unknown:
        raise ValueError(
            f"Không có biên độ cho sàn {unknown} trong configs/data.yaml "
            f"(price_limits.bands_by_exchange hiện có: {sorted(bands_by_exchange)})."
        )

    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(returns["date"]),
            "ticker": returns["ticker"].astype(str),
            "exchange": exchange_col,
            "simple_return": returns["simple_return"].astype(float),
        }
    )
    frame["band"] = frame["exchange"].map(bands_by_exchange).astype(float)
    frame["tolerance"] = float(tolerance_pct)
    frame["excess"] = frame["simple_return"].abs() - frame["band"]

    has_return = frame["simple_return"].notna()
    is_violation = has_return & (
        frame["simple_return"].abs() > frame["band"] + tolerance_pct
    )

    violations = frame.loc[is_violation, _VIOLATION_COLUMNS]
    return violations.sort_values(
        ["excess", "date", "ticker"], ascending=[False, True, True]
    ).reset_index(drop=True)
