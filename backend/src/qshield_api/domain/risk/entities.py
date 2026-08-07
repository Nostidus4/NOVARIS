# Đỗ Ngọc Tân - RiskPortfolioInput + BaselineRiskView — riêng cho feature risk, không dùng chung domain/portfolio/.
"""Không chứa công thức CVaR (đó là `qshield_risk.metrics`) — chỉ mô tả hình dạng input/output của
feature `risk` qua API."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskPortfolioInput:
    """Riêng cho `risk` — xem ghi chú trong `domain/portfolio/entities.py::PortfolioInput`."""

    weights: dict[str, float]
    cash_weight: float


@dataclass(frozen=True)
class BaselineRiskView:
    """Kết quả `qshield_risk.metrics.risk_metrics_from_wealth` cho MỘT danh mục do người dùng nhập
    — khác `baseline_risk.json` (artifact ghi sẵn cho danh mục mẫu `sample_portfolio_weights`).
    `var`/`cvar` khoá theo chuỗi alpha (`"0.95"`, `"0.975"`, `"0.99"`) — giữ nguyên quy ước
    `qshield_risk.metrics.alpha_key`, không đổi kiểu khoá ở tầng backend."""

    alpha_primary: str
    var: dict[str, float]
    cvar: dict[str, float]
    expected_horizon_return: float
    worst_scenario_max_drawdown: float
    scenario_count: int
