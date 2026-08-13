"""Coverage and ranking-stability gate for the Risk V2 Top-N shortlist."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from scipy.stats import kendalltau, spearmanr  # type: ignore[import-untyped]


@dataclass(frozen=True)
class CandidateGateResult:
    """Auditable Top-N gate result; baseline and analysis handoffs are separate."""

    status: str
    selected_count: int
    requested_count: int
    coverage_at_n: float
    coverage_by_metric: dict[str, float]
    sector_coverage: float | None
    median_overlap_at_n: float | None
    worst_overlap_at_n: float | None
    median_jaccard: float | None
    median_spearman: float | None
    median_kendall: float | None
    thresholds: dict[str, float]
    sensitivity_coverage: dict[str, float]
    reasons: tuple[str, ...]
    baseline_handoff_allowed: bool
    analysis_handoff_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_COVERAGE_COLUMNS = {
    "baseline_contribution": "baseline_CVaR_contribution",
    "marginal_10": "marginal_CVaR_reduction_10pct",
    "marginal_20": "marginal_CVaR_reduction_20pct",
    "marginal_30": "marginal_CVaR_reduction_30pct",
    "net_benefit": "net_risk_score",
}


def _positive_coverage(values: pd.Series, selected: pd.Series) -> float:
    positive = np.maximum(pd.to_numeric(values, errors="coerce").fillna(0.0), 0.0)
    total = float(positive.sum())
    return float(positive[selected].sum() / total) if total > 0.0 else 0.0


def _coverage_at_rank(frame: pd.DataFrame, column: str, count: int) -> float:
    eligible = frame["eligible_status"].isin((True, "eligible", "MODEL_ELIGIBLE"))
    selected = eligible & (pd.to_numeric(frame["rank"]) <= count)
    return _positive_coverage(frame[column], selected)


def _rank_correlations(base: Sequence[str], variant: Sequence[str]) -> tuple[float, float]:
    common = [ticker for ticker in base if ticker in set(variant)]
    if len(common) < 2:
        return 0.0, 0.0
    base_rank = {ticker: index for index, ticker in enumerate(base)}
    variant_rank = {ticker: index for index, ticker in enumerate(variant)}
    left = [base_rank[ticker] for ticker in common]
    right = [variant_rank[ticker] for ticker in common]
    spearman = float(spearmanr(left, right).statistic)
    kendall = float(kendalltau(left, right).statistic)
    return (
        spearman if np.isfinite(spearman) else 0.0,
        kendall if np.isfinite(kendall) else 0.0,
    )


def evaluate_candidate_gate(
    candidate_frame: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    output_candidates: int = 10,
    ranking_variants: Mapping[str, Sequence[str]] | None = None,
    sectors: Mapping[str, str] | None = None,
) -> CandidateGateResult:
    """Evaluate coverage, stability and underfill without changing candidate order."""
    required = {
        "rank",
        "ticker",
        "eligible_status",
        "selected_top10",
        *_COVERAGE_COLUMNS.values(),
    }
    missing = sorted(required - set(candidate_frame.columns))
    if missing:
        raise ValueError(f"[risk.candidate_gate] candidate frame missing columns: {missing}.")
    if output_candidates <= 0:
        raise ValueError("[risk.candidate_gate] output_candidates must be positive.")
    raw = config.get("candidate_gate")
    if not isinstance(raw, Mapping):
        raise TypeError("[risk.candidate_gate] candidate_gate config is required.")
    threshold_names = (
        "coverage_at_n_min",
        "median_overlap_at_n_min",
        "worst_overlap_at_n_min",
    )
    if any(raw.get(name) is None for name in threshold_names):
        raise ValueError(
            "[risk.candidate_gate] all provisional gate thresholds are required."
        )
    thresholds = {name: float(raw[name]) for name in threshold_names}
    if any(not np.isfinite(value) or not 0.0 <= value <= 1.0 for value in thresholds.values()):
        raise ValueError("[risk.candidate_gate] thresholds must be finite and in [0, 1].")

    frame = candidate_frame.copy()
    selected = frame["selected_top10"].astype(bool)
    selected_count = int(selected.sum())
    coverage = {
        name: _positive_coverage(frame[column], selected)
        for name, column in _COVERAGE_COLUMNS.items()
    }
    # Workflow V2 MRC gate uses the central 20% action; all other coverages remain reportable.
    coverage_at_n = coverage["marginal_20"]

    sector_coverage = None
    if sectors is not None:
        eligible_tickers = frame.loc[
            frame["eligible_status"].isin((True, "eligible", "MODEL_ELIGIBLE")),
            "ticker",
        ].astype(str)
        eligible_sectors = {sectors[ticker] for ticker in eligible_tickers if ticker in sectors}
        selected_sectors = {
            sectors[ticker]
            for ticker in frame.loc[selected, "ticker"].astype(str)
            if ticker in sectors
        }
        sector_coverage = (
            len(selected_sectors) / len(eligible_sectors) if eligible_sectors else None
        )

    base_ranking = frame.sort_values("rank")["ticker"].astype(str).tolist()
    base_top = set(frame.loc[selected, "ticker"].astype(str))
    overlaps: list[float] = []
    jaccards: list[float] = []
    spearmans: list[float] = []
    kendalls: list[float] = []
    for variant in (ranking_variants or {}).values():
        ordered = [str(ticker) for ticker in variant]
        variant_top = set(ordered[:output_candidates])
        intersection = len(base_top & variant_top)
        overlaps.append(intersection / output_candidates)
        union = len(base_top | variant_top)
        jaccards.append(intersection / union if union else 1.0)
        spearman, kendall = _rank_correlations(base_ranking, ordered)
        spearmans.append(spearman)
        kendalls.append(kendall)

    median_overlap = float(np.median(overlaps)) if overlaps else None
    worst_overlap = float(min(overlaps)) if overlaps else None
    median_jaccard = float(np.median(jaccards)) if jaccards else None
    median_spearman = float(np.median(spearmans)) if spearmans else None
    median_kendall = float(np.median(kendalls)) if kendalls else None

    reasons: list[str] = []
    if selected_count < output_candidates:
        reasons.append(f"UNDERFILLED_CANDIDATES_{selected_count}_OF_{output_candidates}")
    if coverage_at_n < thresholds["coverage_at_n_min"]:
        reasons.append("COVERAGE_BELOW_THRESHOLD")
    if not overlaps:
        reasons.append("STABILITY_NOT_EVALUATED")
    else:
        if median_overlap is not None and median_overlap < thresholds["median_overlap_at_n_min"]:
            reasons.append("MEDIAN_OVERLAP_BELOW_THRESHOLD")
        if worst_overlap is not None and worst_overlap < thresholds["worst_overlap_at_n_min"]:
            reasons.append("WORST_OVERLAP_BELOW_THRESHOLD")

    hard_fail = any(reason != "STABILITY_NOT_EVALUATED" for reason in reasons)
    status = "FAIL" if hard_fail else "NOT_EVALUATED" if reasons else "PASS"
    sensitivity_counts = tuple(int(value) for value in (raw.get("sensitivity_counts", (12, 15)) or ()))
    sensitivity = {
        f"coverage_at_{count}": _coverage_at_rank(
            frame, _COVERAGE_COLUMNS["marginal_20"], count
        )
        for count in sensitivity_counts
        if count > output_candidates
    }
    return CandidateGateResult(
        status=status,
        selected_count=selected_count,
        requested_count=output_candidates,
        coverage_at_n=coverage_at_n,
        coverage_by_metric=coverage,
        sector_coverage=sector_coverage,
        median_overlap_at_n=median_overlap,
        worst_overlap_at_n=worst_overlap,
        median_jaccard=median_jaccard,
        median_spearman=median_spearman,
        median_kendall=median_kendall,
        thresholds=thresholds,
        sensitivity_coverage=sensitivity,
        reasons=tuple(reasons),
        baseline_handoff_allowed=status == "PASS",
        analysis_handoff_allowed=selected_count > 0,
    )
