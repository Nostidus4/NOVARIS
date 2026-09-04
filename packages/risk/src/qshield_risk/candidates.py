"""Rank candidates for the dynamic top-N selection step (`workflow_update`).

Output columns match `configs/workflow_update.yaml` (`risk.candidate_selection.
required_columns`) — artifact `candidate_top10.csv` (schema may still be catching up in
`qshield_contracts.schemas.risk`).

Generic in N: when the configured universe has ``N <= output_candidates``, every ticker is
selected. Real ranking takes effect once the universe grows past `output_candidates`
(30-ticker `workflow_update` scope → top 10).

Four-level marginal CVaR columns (10%/20%/30%) are required by `workflow_update`; leave
unavailable levels as `NaN` with an explanatory `note` rather than fabricating numbers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd  # type: ignore[import-untyped]

from qshield_risk.costs import CostRates, transaction_costs
from qshield_risk.evaluate import required_float
from qshield_risk.metrics import alpha_key, value_at_risk
from qshield_risk.objective import financial_objective
from qshield_risk.paths import (
    asset_growth_paths,
    portfolio_wealth_paths,
    validate_scenario_cube,
)
from qshield_risk.portfolio import align_portfolio_weights, validate_ticker_order

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


def select_four_level_candidates(
    scenarios: np.ndarray,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    eligibility: Mapping[str, bool],
    config: Mapping[str, Any],
    *,
    output_candidates: int = 10,
    ineligible_reasons: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Rank held-eligible assets using true 10/20/30% marginal CVaR reductions.

    The selected count is exactly ``min(N_eligible, output_candidates)``. All source assets remain
    in the explanatory table; ineligible and zero-weight assets carry an explicit reason.
    """
    if output_candidates <= 0:
        raise ValueError("[risk.candidates] output_candidates must be positive.")
    tickers = validate_ticker_order(ticker_order)
    cube = validate_scenario_cube(
        scenarios,
        expected_horizon=int(config.get("horizon_days", 20)),
        expected_assets=len(tickers),
    )
    tolerance = required_float(config, "weight_sum_tolerance")
    aligned = align_portfolio_weights(
        weights, tickers, cash_weight, tolerance=tolerance
    )
    missing = sorted(set(tickers) - set(eligibility))
    if missing:
        raise ValueError(f"[risk.candidates] eligibility missing tickers: {missing}.")

    selection_config = config.get("candidate_selection")
    if not isinstance(selection_config, Mapping):
        raise TypeError("[risk.candidates] candidate_selection mapping is required.")
    raw_score_weights = selection_config.get("score_weights")
    score_names = (
        "marginal_10",
        "marginal_20",
        "marginal_30",
        "baseline_contribution",
        "transaction_cost",
        "liquidity_penalty",
    )
    if not isinstance(raw_score_weights, Mapping):
        raise TypeError(
            "[risk.candidates] candidate_selection.score_weights is required."
        )
    score_weights: dict[str, float] = {}
    for name in score_names:
        value = raw_score_weights.get(name)
        if value is None or not np.isfinite(float(value)):
            raise ValueError(
                f"[risk.candidates] score weight {name!r} must be explicit and finite."
            )
        score_weights[name] = float(value)

    zero = np.zeros(len(tickers), dtype=float)
    baseline = financial_objective(zero, cube, tickers, weights, cash_weight, config)
    primary_key = alpha_key(required_float(config, "cvar_alpha"))
    baseline_cvar = baseline.before.cvar[primary_key]
    wealth = portfolio_wealth_paths(cube, aligned, cash_weight)
    portfolio_losses = 1.0 - wealth[:, -1]
    tail = portfolio_losses >= value_at_risk(
        portfolio_losses, required_float(config, "cvar_alpha")
    )
    asset_terminal_losses = 1.0 - asset_growth_paths(cube)[:, -1, :]
    contributions = (asset_terminal_losses[tail] * aligned).mean(axis=0)

    reasons = ineligible_reasons or {}
    rows: list[dict[str, object]] = []
    for index, ticker in enumerate(tickers):
        held_eligible = bool(eligibility[ticker]) and aligned[index] > tolerance
        marginals: dict[int, float] = {}
        evaluations = {}
        for pct in (10, 20, 30):
            reductions = zero.copy()
            reductions[index] = pct / 100
            evaluation = financial_objective(
                reductions, cube, tickers, weights, cash_weight, config
            )
            evaluations[pct] = evaluation
            marginals[pct] = baseline_cvar - evaluation.after.cvar[primary_key]
        cost = evaluations[30].trade.costs
        transaction_cost = cost.fee + cost.spread
        score = (
            score_weights["marginal_10"] * marginals[10]
            + score_weights["marginal_20"] * marginals[20]
            + score_weights["marginal_30"] * marginals[30]
            + score_weights["baseline_contribution"] * float(contributions[index])
            - score_weights["transaction_cost"] * transaction_cost
            - score_weights["liquidity_penalty"] * cost.liquidity_penalty
        )
        reason = (
            "eligible"
            if held_eligible
            else reasons.get(
                ticker, "not_held" if aligned[index] <= tolerance else "ineligible"
            )
        )
        rows.append(
            {
                "ticker": ticker,
                "current_weight": float(aligned[index]),
                "eligible_status": "eligible" if held_eligible else "ineligible",
                "baseline_CVaR_contribution": float(contributions[index]),
                "marginal_CVaR_reduction_10pct": marginals[10],
                "marginal_CVaR_reduction_20pct": marginals[20],
                "marginal_CVaR_reduction_30pct": marginals[30],
                "transaction_cost_estimate": transaction_cost,
                "liquidity_penalty": cost.liquidity_penalty,
                "net_risk_score": float(score),
                "reason": reason,
            }
        )

    frame = pd.DataFrame(rows)
    frame["_eligible"] = frame["eligible_status"].eq("eligible")
    frame = frame.sort_values(
        ["_eligible", "net_risk_score", "ticker"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    frame.insert(0, "rank", frame.index + 1)
    eligible_count = int(frame["_eligible"].sum())
    selected_count = min(eligible_count, output_candidates)
    frame["selected_top10"] = frame["_eligible"] & (frame["rank"] <= selected_count)
    underfilled_reason = (
        None
        if eligible_count >= output_candidates
        else f"underfilled: Neligible={eligible_count} < requested={output_candidates}"
    )
    frame["underfilled_reason"] = underfilled_reason
    frame["note"] = None
    return frame.drop(columns="_eligible")


def reselect_top_n(
    candidate_frame: pd.DataFrame, output_candidates: int
) -> pd.DataFrame:
    """Recompute `selected_top10`/`underfilled_reason` for a different N (CR-WF2-005).

    `select_four_level_candidates` ranks the *entire* eligible universe by `net_risk_score`
    before ever looking at `output_candidates` — that parameter only decides where the
    ``selected_top10`` cutoff falls. A dynamic-N sweep (try N in {10, 12, 15}, ...) therefore
    never needs to recompute marginal CVaR reductions for every candidate N; it only needs to
    move the cutoff on an already-ranked frame, which this function does.
    """
    required = {"rank", "eligible_status"}
    missing = sorted(required - set(candidate_frame.columns))
    if missing:
        raise ValueError(
            f"[risk.candidates] candidate frame missing columns: {missing}."
        )
    if output_candidates <= 0:
        raise ValueError("[risk.candidates] output_candidates must be positive.")
    frame = candidate_frame.copy()
    eligible = (
        frame["eligible_status"].astype(str).eq("eligible")
        if frame["eligible_status"].dtype == object
        else frame["eligible_status"].astype(bool)
    )
    eligible_count = int(eligible.sum())
    selected_count = min(eligible_count, output_candidates)
    frame["selected_top10"] = eligible & (
        pd.to_numeric(frame["rank"]) <= selected_count
    )
    frame["underfilled_reason"] = (
        None
        if eligible_count >= output_candidates
        else f"underfilled: Neligible={eligible_count} < requested={output_candidates}"
    )
    return frame


def _moving_block_bootstrap_indices(
    n_scenarios: int, *, block_length: int, rng: np.random.Generator
) -> np.ndarray:
    """One moving-block-bootstrap resample of scenario indices, length exactly `n_scenarios`."""
    if n_scenarios <= 0:
        raise ValueError("[risk.candidates] n_scenarios must be positive.")
    if block_length <= 0 or block_length > n_scenarios:
        raise ValueError(
            f"[risk.candidates] block_length must be in [1, {n_scenarios}], "
            f"got {block_length!r}."
        )
    n_blocks = -(-n_scenarios // block_length)  # ceil division, no extra import
    starts = rng.integers(0, n_scenarios - block_length + 1, size=n_blocks)
    indices = np.concatenate(
        [np.arange(start, start + block_length) for start in starts]
    )
    return indices[:n_scenarios]


def bootstrap_ranking_variants(
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    eligibility: Mapping[str, bool],
    config: Mapping[str, Any],
    *,
    seeds: Sequence[int],
    block_length: int,
    output_candidates: int,
    ineligible_reasons: Mapping[str, str] | None = None,
) -> dict[str, list[str]]:
    """Re-rank candidates on moving-block-bootstrap resamples of the scenario cube (P1-5).

    `candidate_gate.evaluate_candidate_gate`'s stability metrics (median/worst overlap, Jaccard,
    Spearman, Kendall) need at least one alternate ranking to compare against; before this
    function existed, `stability_rankings_path: null` meant they were silently never computed
    (`STABILITY_NOT_EVALUATED` on every run). Each seed here resamples the *scenario* axis with a
    moving block bootstrap (blocks of `block_length` consecutive scenarios keep any residual
    serial structure inside a block, matching the ``block_length`` convention already used for
    the ai package's own return-level bootstrap) and reruns `select_four_level_candidates` on the
    resampled cube. This asks "if Monte Carlo had drawn a different finite sample of paths from
    the same generative model, would the Top-N ranking change?" — a statement about sampling
    noise in the already-produced cube. It does **not** regenerate scenarios or touch the HMM
    regime model; that remains packages/ai's exclusive responsibility.
    """
    tickers = validate_ticker_order(ticker_order)
    cube = validate_scenario_cube(
        scenarios,
        expected_horizon=int(config.get("horizon_days", 20)),
        expected_assets=len(tickers),
    )
    if not seeds:
        raise ValueError("[risk.candidates] at least one bootstrap seed is required.")
    n_scenarios = cube.shape[0]
    variants: dict[str, list[str]] = {}
    for seed in seeds:
        rng = np.random.default_rng(int(seed))
        indices = _moving_block_bootstrap_indices(
            n_scenarios, block_length=block_length, rng=rng
        )
        resampled_frame = select_four_level_candidates(
            cube[indices],
            tickers,
            weights,
            cash_weight,
            eligibility,
            config,
            output_candidates=output_candidates,
            ineligible_reasons=ineligible_reasons,
        )
        variants[f"seed_{int(seed)}"] = (
            resampled_frame.sort_values("rank")["ticker"].astype(str).tolist()
        )
    return variants


def candidate_order(candidate_frame: pd.DataFrame) -> list[dict[str, object]]:
    """Return immutable decoding order from selected rows, sorted by candidate rank."""
    required = {"rank", "ticker", "current_weight", "net_risk_score", "selected_top10"}
    missing = sorted(required - set(candidate_frame.columns))
    if missing:
        raise ValueError(
            f"[risk.candidates] candidate frame missing columns: {missing}."
        )
    selected = candidate_frame.loc[candidate_frame["selected_top10"]].sort_values(
        ["rank", "ticker"], kind="stable"
    )
    return [
        {
            "rank": int(row.rank),
            "ticker": str(row.ticker),
            "current_weight": float(row.current_weight),
            "candidate_score": float(row.net_risk_score),
        }
        for row in selected.itertuples(index=False)
    ]
