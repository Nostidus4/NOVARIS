# Đỗ Ngọc Tân - QshieldRiskCalculator — implement RiskCalculator, import THẲNG qshield_risk (an toàn, đồng bộ).
"""KHÔNG qua subprocess — `qshield_risk` không đụng qiskit, không ghi parquet, an toàn import
thẳng trong tiến trình backend (khác `qshield_quantum`, xem
docs/architecture/backend_hexagonal_design.md §3).

Tính CVaR cho ĐÚNG danh mục người dùng gửi lên (không phải danh mục mẫu `sample_portfolio_weights`
trong artifact `baseline_risk.json` đã ghi sẵn) — dùng lại scenario cube thật đã có, không tính lại
kịch bản.
"""

from __future__ import annotations

from dataclasses import dataclass

from qshield_contracts.config import Config
from qshield_risk.evaluate import confidence_levels, required_float
from qshield_risk.metrics import alpha_key, risk_metrics_from_wealth
from qshield_risk.paths import portfolio_wealth_paths
from qshield_risk.portfolio import align_portfolio_weights

from qshield_api.domain.risk.entities import BaselineRiskView, RiskPortfolioInput
from qshield_api.infrastructure.persistence.artifact_reader import (
    build_paths,
    read_scenario_cube,
)


class ScenarioCubeMissingError(RuntimeError):
    """Chưa có scenario cube — chạy `qshield-ai scenarios` trước khi gọi `POST /risk/cvar`."""


@dataclass(frozen=True)
class QshieldRiskCalculator:
    cfg: Config

    def compute(self, portfolio: RiskPortfolioInput) -> BaselineRiskView:
        paths = build_paths(self.cfg)
        cube_and_tickers = read_scenario_cube(paths)
        if cube_and_tickers is None:
            raise ScenarioCubeMissingError(
                "Chưa có stress_scenarios.npz — chạy `qshield-ai scenarios` trước."
            )
        cube, ticker_order = cube_and_tickers

        tolerance = required_float(self.cfg, "weight_sum_tolerance")
        aligned = align_portfolio_weights(
            portfolio.weights, ticker_order, portfolio.cash_weight, tolerance=tolerance
        )
        levels = confidence_levels(self.cfg)
        alpha = required_float(self.cfg, "cvar_alpha")

        # Không có hành động phòng vệ nào ở đây (chỉ chấm CVaR "hiện trạng") — stock_amounts trên
        # NAV=1 trước hedge chính là trọng số đã align, cash_amount là cash_weight nguyên trạng.
        wealth = portfolio_wealth_paths(cube, aligned, portfolio.cash_weight)
        metrics = risk_metrics_from_wealth(wealth, levels)

        return BaselineRiskView(
            alpha_primary=alpha_key(alpha),
            var=metrics.var,
            cvar=metrics.cvar,
            expected_horizon_return=metrics.expected_horizon_return,
            worst_scenario_max_drawdown=metrics.worst_scenario_max_drawdown,
            scenario_count=metrics.scenario_count,
        )
