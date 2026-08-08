# Đỗ Ngọc Tân - bitstring → action → ticker → tỷ trọng mới.
"""Giải mã bitstring 8-bit thắng cuộc thành hành động cụ thể.

Bit thứ `i` (0-indexed, thứ tự = `configs/base.yaml`) = 1 nghĩa là chọn hành động `i` = giảm
`reduction_pct` (khóa 20% — CLAUDE.md) vị thế mã `ticker_order[i]`, phần vốn giải phóng chuyển sang
tiền mặt. Tổng tỷ trọng (kể cả `cash`) luôn phải = 1.0 sau decode (CLAUDE.md quy tắc 6).
"""

from __future__ import annotations


def chosen_action_ids(bitstring: str) -> list[int]:
    """Index (0-based) của các bit = '1' — đúng thứ tự bitstring truyền vào."""
    return [i for i, b in enumerate(bitstring) if b == "1"]


def chosen_tickers(bitstring: str, ticker_order: list[str]) -> list[str]:
    return [ticker_order[i] for i in chosen_action_ids(bitstring)]


def decode(
    bitstring: str,
    ticker_order: list[str],
    current_weights: dict[str, float],
    *,
    reduction_pct: float,
) -> dict[str, float]:
    """Trả tỷ trọng mới (có khóa `"cash"`), tổng luôn = 1.0.

    `current_weights` không cần có sẵn khóa `"cash"` (mặc định 0.0 nếu chưa có — danh mục 100%
    cổ phiếu trước hedge, đúng `configs/base.yaml: sample_portfolio_weights`).
    """
    if len(bitstring) != len(ticker_order):
        raise ValueError(
            f"bitstring dài {len(bitstring)} nhưng ticker_order có {len(ticker_order)} mã."
        )

    new_weights = dict(current_weights)
    cash = float(new_weights.pop("cash", 0.0))
    for idx in chosen_action_ids(bitstring):
        ticker = ticker_order[idx]
        w = float(new_weights.get(ticker, 0.0))
        freed = w * reduction_pct
        new_weights[ticker] = w - freed
        cash += freed
    new_weights["cash"] = cash

    total = sum(new_weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"Tổng tỷ trọng sau decode = {total:.6f}, phải = 1.0 (CLAUDE.md quy tắc 6)."
        )
    return new_weights
