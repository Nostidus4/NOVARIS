# Đỗ Ngọc Tân - PortfolioInput — validate hình dạng, KHÔNG phải công thức tài chính.
"""Riêng cho feature `portfolio` (POST /portfolio/validate) — KHÔNG dùng chung với
`domain/risk/entities.py::RiskPortfolioInput` hay `domain/optimize/entities.py::OptimizeJobRequest`
dù cùng hình dạng field. Quyết định đã chốt: mỗi feature khai entity portfolio riêng để tránh một
feature đổi hình dạng làm hỏng 2 feature còn lại (xem
docs/architecture/backend_hexagonal_design.md §6.2).
"""

from __future__ import annotations

from dataclasses import dataclass


class PortfolioShapeError(ValueError):
    """Hình dạng danh mục sai (tổng khác 1, ticker lạ, trọng số âm...) — lỗi 422, không phải 500."""


@dataclass(frozen=True)
class PortfolioInput:
    weights: dict[str, float]  # ticker -> tỷ trọng
    cash_weight: float

    def total_weight(self) -> float:
        return sum(self.weights.values()) + self.cash_weight
