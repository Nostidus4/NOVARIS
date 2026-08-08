# Đỗ Ngọc Tân - đọc config cho backend qua qshield_contracts.Config — không hard-code tham số riêng.
"""Nơi DUY NHẤT trong `backend/` gọi `qshield_contracts.config.Config.load_profiled()`.

`transaction_cost` / `weight_sum_tolerance` đã có trong `configs/base.yaml` + profile.
`apply_provisional_overrides` chỉ còn là lưới an toàn nếu giá trị bị null.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from qshield_contracts.config import Config

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("configs/base.yaml")
DEFAULT_PROFILE_PATH = Path("configs/workflow_update.yaml")

PROVISIONAL_TRANSACTION_COST = {
    "fee": 0.0015,
    "spread": 0.0010,
    "liquidity_penalty": 0.0005,
}
PROVISIONAL_WEIGHT_SUM_TOLERANCE = 1e-8


def apply_provisional_overrides(cfg: Config) -> Config:
    resolved = dict(cfg)
    is_provisional = False

    transaction_cost = resolved.get("transaction_cost") or {}
    if any(
        transaction_cost.get(key) is None
        for key in ("fee", "spread", "liquidity_penalty")
    ):
        resolved["transaction_cost"] = PROVISIONAL_TRANSACTION_COST
        is_provisional = True

    if resolved.get("weight_sum_tolerance") is None:
        resolved["weight_sum_tolerance"] = PROVISIONAL_WEIGHT_SUM_TOLERANCE
        is_provisional = True

    if is_provisional:
        logger.warning(
            "transaction_cost/weight_sum_tolerance còn null — đã áp số PROVISIONAL; "
            "kết quả risk/optimize là NON_BASELINE_RUN."
        )
    return Config(resolved)


@lru_cache
def get_config(
    config_path: str = str(DEFAULT_CONFIG_PATH),
    profile_path: str = str(DEFAULT_PROFILE_PATH),
) -> Config:
    """Đọc + resolve config MỘT LẦN, cache lại."""
    cfg = Config.load_profiled(Path(config_path), Path(profile_path))
    return apply_provisional_overrides(cfg)
