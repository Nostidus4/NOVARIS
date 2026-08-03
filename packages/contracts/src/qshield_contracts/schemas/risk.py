# Đỗ Ngọc Tân - schema action_effects.csv: vector g, ma trận C, vector chi phí c. Phối hợp Liêu Hoài Phúc.
"""Schema cho 3 artifact chặng Risk — SPEC ĐI TRƯỚC, `packages/risk/` còn là scaffold.

3 file riêng (không gộp 1) theo `docs/Structure.md` §4 (bàn giao Phúc → Tân:
`baseline_risk.json`, `action_effects.csv`, `pairwise_effects.csv`) — `C_ij` là ma trận NxN, khó nhét
chung 1 file phẳng với `g_i`/`c_i` theo hàng (plan-contracts.md §3.4).

Quy ước dấu bắt buộc (CLAUDE.md quy tắc 1-2): `L_s = -R^(H)_{p,s}`, CVaR tính trên loss (loss dương =
lỗi), Rockafellar–Uryasev, α = 0.95.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandera.pandas as pandera


@dataclass(frozen=True)
class BaselineRisk:
    """`baseline_risk.json` — chỉ tiêu tài chính TRƯỚC khi áp dụng bất kỳ hành động phòng vệ nào."""

    var_0: float
    cvar_0: float
    portfolio_weights: dict[
        str, float
    ]  # ticker -> weight, tổng phải = 1.0 (CLAUDE.md quy tắc 6)
    alpha: float  # 0.95


ActionEffectsSchema = pandera.DataFrameSchema(
    {
        "action_id": pandera.Column(int, pandera.Check.ge(0)),
        "ticker": pandera.Column(str),
        "g": pandera.Column(
            float
        ),  # g_i = CVaR_0 - CVaR_i (giảm CVaR khi làm hành động i một mình)
        "c": pandera.Column(
            float, pandera.Check.ge(0)
        ),  # TC_i = |Δw_i| × (fee + spread + liquidity_penalty)
    },
    unique=["action_id"],
    coerce=True,
)

PairwiseEffectsSchema = pandera.DataFrameSchema(
    {
        "action_i": pandera.Column(int, pandera.Check.ge(0)),
        "action_j": pandera.Column(int, pandera.Check.ge(0)),
        "C_ij": pandera.Column(
            float
        ),  # C_ij = g_i + g_j - R_ij (R_ij = hiệu ứng thật khi làm cả hai)
    },
    unique=["action_i", "action_j"],
    coerce=True,
)
