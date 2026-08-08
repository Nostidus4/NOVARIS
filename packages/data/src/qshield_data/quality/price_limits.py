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

import re
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

VIOLATION_COLUMNS = [
    "date",
    "ticker",
    "exchange",
    "simple_return",
    "band",
    "tolerance",
    "excess",
]


def _is_periods_shape(periods: Any) -> bool:
    """`True` khi `periods` là sequence các mapping — KHÔNG chấp nhận `str`.

    `str` cũng là `Sequence` trong Python, nên `isinstance(x, Sequence)` một mình sẽ cho qua
    một chuỗi ký tự (đúng dạng sinh ra bởi round-trip YAML → CSV → `pd.read_csv`, xem docstring
    `_periods_by_ticker`). Phải loại `str` tường minh trước khi kiểm tra `Sequence`.
    """
    if isinstance(periods, str):
        return False
    if not isinstance(periods, Sequence):
        return False
    return all(isinstance(item, Mapping) for item in periods)


def _period_exchange(ticker: str, period: Mapping[str, Any]) -> str:
    """`period["exchange"]` với lỗi có ngữ cảnh thay vì `KeyError` trần."""
    exchange = period.get("exchange")
    if exchange is None:
        raise ValueError(
            f"Ticker {ticker!r} có một period trong exchange_periods thiếu khoá 'exchange': "
            f"{dict(period)!r}. Sửa configs/base.yaml."
        )
    return str(exchange)


def _period_in_force(ticker: str, periods: Sequence[Mapping[str, Any]]) -> str:
    """Sàn của period đang có hiệu lực "hiện tại" — period không có `until` (mở), hoặc nếu mọi
    period đều đã đóng thì period có `until` muộn nhất."""
    open_ended = [p for p in periods if p.get("until") is None]
    candidate = (
        open_ended[-1]
        if open_ended
        else max(periods, key=lambda p: pd.Timestamp(p.get("until")))
    )
    return _period_exchange(ticker, candidate)


def _periods_by_ticker(
    universe: pd.DataFrame,
) -> dict[str, Sequence[Mapping[str, Any]]]:
    """`ticker -> exchange_periods`, báo lỗi ngay nếu thiếu, rỗng, sai dạng, hoặc lệch
    `exchange_current`.

    `configs/base.yaml` mang lịch sử sàn của mỗi ticker ba lần: `exchange_current` (máy đọc
    được), `exchange_history` (văn xuôi), `exchange_periods` (máy đọc được, dùng để resolve biên
    độ). Chỉ `exchange_periods` được đọc ở đây — nếu nó lệch với `exchange_current` thì một trong
    hai đã bị sửa mà quên sửa cái kia, và triệu chứng duy nhất là một con số vi phạm không ai có
    baseline để so sánh. Vì vậy khi `universe` có cột `exchange_current`, period đang có hiệu lực
    "hiện tại" của mỗi ticker phải khớp giá trị đó.

    `exchange_periods` cũng có thể tới dưới dạng chuỗi repr Python (`"[{'exchange': 'HOSE'}]"`)
    nếu nó đi qua round-trip `registry.save_universe_and_sources` (ghi CSV) rồi
    `loader.load_data("universe")` (đọc lại bằng `pd.read_csv`, vốn không parse `list[dict]`) —
    trường hợp đó phải bị từ chối tường minh ở đây, không được lặp ký tự của chuỗi rồi chết ở tầng
    dưới với `AttributeError` vô nghĩa.
    """
    if "exchange_periods" not in universe.columns:
        raise ValueError(
            "universe thiếu cột 'exchange_periods' — không resolve được sàn theo ngày. "
            "Thêm trường này vào configs/base.yaml (xem registry._UNIVERSE_COLUMNS)."
        )
    has_current = "exchange_current" in universe.columns
    out: dict[str, Sequence[Mapping[str, Any]]] = {}
    for row in universe.itertuples(index=False):
        ticker = str(row.ticker)
        periods = row.exchange_periods
        if not _is_periods_shape(periods):
            raise ValueError(
                f"Ticker {ticker!r} có exchange_periods sai dạng: kỳ vọng list[dict], nhận "
                f"{type(periods).__name__} = {periods!r}. Nguyên nhân thường gặp: universe đã đi "
                "qua round-trip registry.save_universe_and_sources (ghi CSV) rồi "
                "pd.read_csv (đọc lại) — CSV không giữ được kiểu list[dict], cột đó thành chuỗi "
                "repr. Đọc universe qua configs/base.yaml (registry.load_universe), không qua "
                "CSV đã ghi, nếu cần exchange_periods."
            )
        if len(periods) == 0:
            raise ValueError(
                f"Ticker {ticker!r} có exchange_periods rỗng trong configs/base.yaml — "
                "không suy ra được biên độ. Không có fallback theo thiết kế."
            )
        if has_current:
            declared = str(row.exchange_current)
            in_force = _period_in_force(ticker, periods)
            if in_force != declared:
                raise ValueError(
                    f"Ticker {ticker!r}: exchange_periods cho thấy sàn đang hiệu lực là "
                    f"{in_force!r}, nhưng exchange_current lại ghi {declared!r} trong "
                    "configs/base.yaml — hai trường lệch nhau. Đồng bộ lại cả hai."
                )
        out[ticker] = periods
    return out


def _exchanges_mentioned(text: str, vocabulary: Sequence[str]) -> set[str]:
    """Tập tên sàn trong `vocabulary` xuất hiện dạng từ nguyên vẹn (không phân biệt hoa/thường)
    trong `text`. Dùng biên từ `\\b` để `"HOSE"` không khớp nhầm vào giữa một từ dài hơn."""
    found: set[str] = set()
    for exchange in vocabulary:
        pattern = r"(?i)\b" + re.escape(str(exchange)) + r"\b"
        if re.search(pattern, text):
            found.add(str(exchange))
    return found


def _check_exchange_history_covered_by_periods(
    universe: pd.DataFrame,
    periods_by_ticker: Mapping[str, Sequence[Mapping[str, Any]]],
    bands_by_exchange: Mapping[str, float],
) -> None:
    """`exchange_history` (văn xuôi, vd. `"HNX→HOSE 2020-12"`) là bản ghi lịch sử sàn thứ ba,
    độc lập với `exchange_periods`. Check `exchange_current` (`_periods_by_ticker`) không bắt được
    trường hợp `exchange_periods` bị xóa/thu gọn lịch sử (vd. ACB còn mỗi `[{"exchange": "HOSE"}]`)
    khi sàn đang hiệu lực không đổi — `exchange_current` vẫn khớp `in_force`, check đó pass, và 12
    phiên HNX hợp lệ của ACB bị chấm nhầm bằng biên HOSE ±7%. `exchange_history` vẫn còn nhắc tới
    sàn đã mất nên bắt được đúng lỗi này.

    Từ vựng tên sàn lấy từ khoá của `bands_by_exchange` (configs/base.yaml: price_limits.
    bands_by_exchange) — đây là những sàn DUY NHẤT hệ thống biết tới; không hard-code tên sàn ở
    đây (CLAUDE.md quy tắc 8) và không suy đoán bằng regex tách token viết hoa (sẽ false-positive
    với văn xuôi tiếng Việt viết hoa tùy tiện).
    """
    if (
        "exchange_history" not in universe.columns
        or "exchange_current" not in universe.columns
    ):
        return
    vocabulary = list(bands_by_exchange)
    for row in universe.itertuples(index=False):
        ticker = str(row.ticker)
        history = row.exchange_history
        if history is None:
            continue
        history_text = str(history)
        mentioned = _exchanges_mentioned(history_text, vocabulary)
        if not mentioned:
            continue
        periods = periods_by_ticker.get(ticker, [])
        covered = {_period_exchange(ticker, p) for p in periods}
        missing = sorted(mentioned - covered)
        if missing:
            raise ValueError(
                f"Ticker {ticker!r}: exchange_history {history_text!r} nhắc tới sàn {missing}, "
                "nhưng exchange_periods không có period nào ở (các) sàn đó (hiện có: "
                f"{sorted(covered)}). exchange_periods có thể đã bị thu gọn/xóa lịch sử — đồng bộ "
                "lại với configs/base.yaml."
            )


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
            resolved[in_period] = _period_exchange(ticker, period)

        overlapping = is_ticker & (hits > 1)
        if overlapping.any():
            first = dates[overlapping].min().date()
            raise ValueError(
                f"exchange_periods của {ticker!r} chồng lấn tại {first} — "
                f"một ngày khớp {int(hits[overlapping].max())} period. Sửa configs/base.yaml."
            )
        missing = is_ticker & (hits == 0)
        if missing.any():
            first = dates[missing].min().date()
            raise ValueError(
                f"Ticker {ticker!r}: ngày {first} không rơi vào exchange_periods nào — "
                "lịch sử sàn có khoảng trống. Sửa configs/base.yaml."
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
    missing_cols = [
        c for c in ("date", "ticker", "simple_return") if c not in returns.columns
    ]
    if missing_cols:
        raise ValueError(
            f"returns thiếu cột {missing_cols} — không phải khung `returns.parquet` hợp lệ "
            f"(schemas/returns.py). Cột hiện có: {list(returns.columns)}."
        )
    if tolerance_pct < 0:
        raise ValueError(
            f"tolerance_pct phải >= 0, nhận {tolerance_pct} "
            "(configs/base.yaml: price_limits.tolerance_pct)."
        )
    for exchange, band in bands_by_exchange.items():
        if band <= 0:
            raise ValueError(
                f"Biên độ của sàn {exchange!r} phải > 0, nhận {band} "
                "(configs/base.yaml: price_limits.bands_by_exchange)."
            )

    _check_exchange_history_covered_by_periods(
        universe, _periods_by_ticker(universe), bands_by_exchange
    )

    exchange_col = resolve_exchange_column(returns, universe)
    unknown = sorted(set(exchange_col.dropna()) - set(bands_by_exchange))
    if unknown:
        affected = sorted(
            returns.loc[exchange_col.isin(unknown), "ticker"].astype(str).unique()
        )
        raise ValueError(
            f"Không có biên độ cho sàn {unknown} trong configs/base.yaml "
            f"(price_limits.bands_by_exchange hiện có: {sorted(bands_by_exchange)}). "
            f"Mã bị ảnh hưởng: {affected}."
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

    violations = frame.loc[is_violation, VIOLATION_COLUMNS]
    return violations.sort_values(
        ["excess", "date", "ticker"], ascending=[False, True, True]
    ).reset_index(drop=True)
