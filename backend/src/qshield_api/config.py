# Đỗ Ngọc Tân - đọc config cho backend qua qshield_contracts.Config — không hard-code tham số riêng.
"""Nơi DUY NHẤT trong `backend/` gọi `qshield_contracts.config.Config.load()`. Tất cả
`*_repository_impl.py`/`*_calculator.py`/`*_runner.py` nhận `Config` đã load qua đây (qua
`deps.py`), không tự đọc `configs/*.yaml`.

Áp PROVISIONAL cho `transaction_cost`/`weight_sum_tolerance` nếu còn `null` trong
`configs/risk.yaml` (TBD-002, `docs/product/mvp_scope.md` §23 — Phúc đề xuất, Ngọc duyệt, chưa có
số nào được duyệt tại thời điểm viết file này). Không có giá trị này thì `qshield_risk.evaluate`/
`qshield_risk.costs.CostRates.from_config` raise ngay — backend không chạy được các endpoint
`risk`/`optimize`. Ghi log CẢNH BÁO rõ ràng mỗi lần dùng số tạm — không âm thầm hợp thức hoá,
đúng tinh thần đã áp dụng xuyên suốt ở các notebook `notebooks/exploration/{risk_effects,
quantum_solve,pipeline_full_run}.ipynb`.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from qshield_contracts.config import Config

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("configs/base.yaml")

# PROVISIONAL — KHÔNG phải số đã duyệt. Mức phí môi giới VN điển hình, chỉ để backend chạy được;
# mọi baseline_risk/optimize sinh ra khi dùng số này phải hiểu là NON_BASELINE_RUN.
PROVISIONAL_TRANSACTION_COST = {
    "fee": 0.0015,
    "spread": 0.0010,
    "liquidity_penalty": 0.0005,
}
PROVISIONAL_WEIGHT_SUM_TOLERANCE = 1e-6


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
            "transaction_cost/weight_sum_tolerance PROVISIONAL (TBD-002, chưa Phúc/Ngọc duyệt) — "
            "mọi kết quả risk/optimize từ backend này là NON_BASELINE_RUN."
        )
    return Config(resolved)


@lru_cache
def get_config(config_path: str = str(DEFAULT_CONFIG_PATH)) -> Config:
    """Đọc + resolve config MỘT LẦN, cache lại — mọi request dùng chung, không đọc lại file mỗi
    request. Artifact trên đĩa (regime/scenarios/risk/optimize) vẫn đọc tươi mỗi request ở tầng
    `*_repository_impl.py`, chỉ CONFIG (tham số) mới cache."""
    cfg = Config.load(Path(config_path))
    return apply_provisional_overrides(cfg)
