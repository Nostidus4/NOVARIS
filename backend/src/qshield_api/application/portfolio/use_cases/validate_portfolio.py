# Đỗ Ngọc Tân - use case: validate hình dạng danh mục — KHÔNG gọi package tài chính nào.
"""Chỉ kiểm tra: (1) mọi ticker nằm trong universe đã khóa, (2) tổng tỷ trọng (cổ phiếu + tiền
mặt) = 1.0 trong dung sai (CLAUDE.md quy tắc 6), (3) không có trọng số âm. Không tính CVaR/QUBO gì
ở đây — đó là việc của feature `risk`/`optimize`."""

from __future__ import annotations

from collections.abc import Sequence

from qshield_api.application.portfolio.dto import PortfolioInputDTO, ValidationResultDTO


def validate_portfolio(
    portfolio: PortfolioInputDTO,
    *,
    valid_tickers: Sequence[str],
    tolerance: float,
) -> ValidationResultDTO:
    errors: list[str] = []
    valid_set = set(valid_tickers)

    unknown = sorted(set(portfolio.weights) - valid_set)
    if unknown:
        errors.append(f"Ticker không nằm trong universe: {unknown}")

    negative = sorted(t for t, w in portfolio.weights.items() if w < 0)
    if negative:
        errors.append(f"Trọng số âm: {negative}")
    if portfolio.cash_weight < 0:
        errors.append(f"cash_weight âm: {portfolio.cash_weight}")

    total = sum(portfolio.weights.values()) + portfolio.cash_weight
    if abs(total - 1.0) > tolerance:
        errors.append(
            f"Tổng tỷ trọng = {total!r}, kỳ vọng 1.0 (dung sai {tolerance!r})"
        )

    return ValidationResultDTO(valid=not errors, errors=errors)
