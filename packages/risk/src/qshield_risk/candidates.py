"""Rank candidates for the dynamic top-N selection step (`workflow_update` baseline).

Output columns match `configs/profiles/workflow_update.yaml` (`risk.candidate_selection.
required_columns`) — this is a NEW artifact (`candidate_top10.csv`) not yet in
`qshield_contracts.schemas.risk` (that module still only covers the `demo_fast`-shaped
`action_effects.csv`/`pairwise_effects.csv`).

Generic in N, not hard-coded to "10": when the configured universe has ``N <= output_candidates``
(today: 8 <= 10, per `configs/profiles/demo_fast.yaml` — "toan bo 8 ma duoc dua vao risk/quantum
demo"), every ticker is selected and nothing is filtered. Real ranking only takes effect once the
universe grows past `output_candidates` (30-ticker `workflow_update` scope).

`demo_fast` only computes ONE action level (`action_reduction_pct`, locked at 20%) — the 10%/30%
`marginal_CVaR_reduction_*` columns required by `workflow_update` are left `NaN` with an explanatory
`note` rather than fabricated; that math needs the 4-level action grid, not built yet (CLAUDE.md
"Quantum" section preamble).
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from qshield_risk.costs import CostRates, transaction_costs

REQUIRED_COLUMNS = (
    "rank",
    "ticker",
    "current_weight",
    "eligible_status",
    "baseline_CVaR_contribution",
    "marginal_CVaR_reduction_10pct",
    "marginal_CVaR_reduction_20pct",
    "marginal_CVaR_reduction_30pct",
    "transaction_cost_estimate",
    "liquidity_penalty",
    "net_risk_score",
    "selected_top10",
    "reason",
    "note",
)

_REDUCTION_COLUMN_BY_PCT = {
    10: "marginal_CVaR_reduction_10pct",
    20: "marginal_CVaR_reduction_20pct",
    30: "marginal_CVaR_reduction_30pct",
}


def select_candidates(
    action_effects: pd.DataFrame,
    *,
    baseline_cvar: float,
    weights: Mapping[str, float],
    cost_rates: CostRates,
    reduction_pct: float,
    output_candidates: int,
) -> pd.DataFrame:
    """Rank tickers by `net_risk_score = g - c` and flag the top `output_candidates`.

    ``action_effects`` must have the `action_id, ticker, g, c` columns `qshield_risk.effects.
    build_effects` produces. `net_risk_score` is PROVISIONAL (`g - c`, the simplest combination of
    the benefit/cost components available today) — `workflow_update.yaml` names the components but
    not their weights; needs Phuc/Ngoc sign-off before use as an approved ranking formula.

    Raises `ValueError` if `reduction_pct` is not one of the three locked action levels
    (0.10/0.20/0.30) — this function only knows how to label a level it recognizes, it does not
    guess which output column a given fraction belongs to.
    """
    pct = round(float(reduction_pct) * 100)
    if pct not in _REDUCTION_COLUMN_BY_PCT or not np.isclose(reduction_pct, pct / 100):
        raise ValueError(
            f"[risk.candidates] reduction_pct={reduction_pct!r} không khớp mức nào trong "
            f"{sorted(v / 100 for v in _REDUCTION_COLUMN_BY_PCT)} — không biết gán vào cột nào."
        )
    reduction_column = _REDUCTION_COLUMN_BY_PCT[pct]

    missing = [
        c for c in ("action_id", "ticker", "g", "c") if c not in action_effects.columns
    ]
    if missing:
        raise ValueError(
            f"[risk.candidates] action_effects thiếu cột {missing} — không phải output của "
            "qshield_risk.effects.build_effects."
        )
    if output_candidates <= 0:
        raise ValueError(
            f"[risk.candidates] output_candidates phải > 0, nhận {output_candidates!r}."
        )

    rows: list[dict[str, object]] = []
    for row in action_effects.itertuples(index=False):
        ticker = str(row.ticker)
        if ticker not in weights:
            raise ValueError(
                f"[risk.candidates] ticker {ticker!r} không có trong weights."
            )
        current_weight = float(weights[ticker])
        gross_sale = current_weight * float(reduction_pct)
        cost_breakdown = transaction_costs(gross_sale, cost_rates)

        rows.append(
            {
                "ticker": ticker,
                "current_weight": current_weight,
                "eligible_status": "eligible",
                "baseline_CVaR_contribution": current_weight * float(baseline_cvar),
                "marginal_CVaR_reduction_10pct": np.nan,
                "marginal_CVaR_reduction_20pct": np.nan,
                "marginal_CVaR_reduction_30pct": np.nan,
                reduction_column: float(row.g),
                "transaction_cost_estimate": float(row.c),
                "liquidity_penalty": cost_breakdown.liquidity_penalty,
                "net_risk_score": float(row.g) - float(row.c),
                "note": (
                    None
                    if reduction_column == "marginal_CVaR_reduction_20pct"
                    else f"chỉ tính được mức {pct}% — chưa có 4-mức hành động của workflow_update"
                ),
            }
        )

    frame = (
        pd.DataFrame(rows)
        .sort_values("net_risk_score", ascending=False, kind="stable")
        .reset_index(drop=True)
    )
    frame.insert(0, "rank", frame.index + 1)

    n = len(frame)
    if n <= output_candidates:
        frame["selected_top10"] = True
        frame["reason"] = f"N={n} <= output_candidates={output_candidates}, không lọc"
    else:
        frame["selected_top10"] = frame["rank"] <= output_candidates
        frame["reason"] = np.where(
            frame["selected_top10"],
            "rank <= output_candidates",
            "rank > output_candidates",
        )

    return frame[list(REQUIRED_COLUMNS)]
