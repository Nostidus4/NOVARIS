from __future__ import annotations

from typing import Any

import pytest

TICKERS = ("ACB", "CTG", "VCB", "HPG", "VIC", "MWG", "VNM", "FPT")


@pytest.fixture
def risk_config() -> dict[str, Any]:
    return {
        "cvar_alpha": 0.95,
        "robustness_confidence_levels": [0.975, 0.99],
        "action_reduction_pct": 0.20,
        "transaction_cost": {
            "fee": 0.001,
            "spread": 0.002,
            "liquidity_penalty": 0.0005,
        },
        "weight_sum_tolerance": 1e-10,
        "k_actions": 3,
        "horizon_days": 2,
    }
