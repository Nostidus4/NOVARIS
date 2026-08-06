# Đỗ Ngọc Tân - fixtures TẠM THỜI cho packages/quantum; xóa khi packages/risk có thật.
"""Sinh `g`/`C`/`c`/`baseline_risk` giả — đúng `schemas/risk.py` (đã có thật trong
`packages/contracts`) — CHỈ dùng qua `--mock`.

TẠM THỜI (theo đúng tiền lệ `qshield_ai/src/qshield_ai/fixtures.py`): `packages/risk/` hiện vẫn
scaffold (34 dòng, chưa có `action_effects.csv`/`pairwise_effects.csv`/`baseline_risk.json` thật —
xem `plan.md` §1). File này XÓA khi `packages/risk` implement xong, đổi `cli.py` sang đọc artifact
thật qua `io.py` — không giữ hai nguồn dữ liệu song song.

Không phải dữ liệu tài chính thật — chỉ đủ hình dạng đúng schema để build/test/chạy
`packages/quantum` độc lập trong lúc chờ.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from qshield_contracts.schemas.risk import BaselineRisk


def generate_arrays(
    tickers: list[str], *, seed: int, alpha: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, BaselineRisk]:
    """Trả `(g, C, c, baseline)` — `g`/`c`: (n,), `C`: (n,n) đối xứng, đường chéo = 0."""
    rng = np.random.default_rng(seed)
    n = len(tickers)

    cvar_0 = float(abs(rng.normal(loc=0.08, scale=0.02)))
    var_0 = cvar_0 * 0.8  # VaR luôn <= CVaR cùng alpha (Rockafellar-Uryasev)

    g = np.abs(rng.normal(loc=cvar_0 * 0.05, scale=cvar_0 * 0.02, size=n))
    c = np.abs(rng.normal(loc=cvar_0 * 0.005, scale=cvar_0 * 0.002, size=n))

    raw = rng.normal(loc=0.0, scale=cvar_0 * 0.01, size=(n, n))
    C = (raw + raw.T) / 2
    np.fill_diagonal(C, 0.0)

    weights = {ticker: 1.0 / n for ticker in tickers}
    baseline = BaselineRisk(
        var_0=var_0, cvar_0=cvar_0, portfolio_weights=weights, alpha=alpha
    )
    return g, C, c, baseline


def action_effects_frame(
    g: np.ndarray, c: np.ndarray, tickers: list[str]
) -> pd.DataFrame:
    """Đúng `schemas/risk.py::ActionEffectsSchema` — `action_id` = index vào `tickers`."""
    return pd.DataFrame(
        {"action_id": range(len(tickers)), "ticker": tickers, "g": g, "c": c}
    )


def pairwise_effects_frame(C: np.ndarray) -> pd.DataFrame:
    """Đúng `schemas/risk.py::PairwiseEffectsSchema` — chỉ lưu `i<j` (tam giác trên)."""
    n = C.shape[0]
    rows = [
        {"action_i": i, "action_j": j, "C_ij": float(C[i, j])}
        for i in range(n)
        for j in range(i + 1, n)
    ]
    return pd.DataFrame(rows, columns=["action_i", "action_j", "C_ij"])


def generate_frames(
    tickers: list[str], *, seed: int, alpha: float
) -> tuple[pd.DataFrame, pd.DataFrame, BaselineRisk]:
    """Trả `(action_effects_df, pairwise_effects_df, baseline)` — đúng hình dạng artifact thật,
    để `cli.py` xử lý `--mock` và dữ liệu thật bằng cùng một đường code (qua `io.py`)."""
    g, C, c, baseline = generate_arrays(tickers, seed=seed, alpha=alpha)
    return action_effects_frame(g, c, tickers), pairwise_effects_frame(C), baseline
