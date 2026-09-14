# Đỗ Ngọc Tân - thống kê paired theo instance + gate H1–H6 cho thí nghiệm hybrid.
"""Thống kê cho claim QAOA-assisted.

- Đơn vị quan sát = instance (portfolio-date), không phải scenario hay candidate.
- ``uplift = J_final(baseline) − J_final(qaoa)``; dương ⇒ QAOA-assisted tốt hơn (minimization).
- Track thất bại/không có nghiệm feasible được gán ``J_no_action`` (bảo thủ: thất bại tính là thua,
  không được biến thành hòa hay bị loại khỏi mẫu).
- Wilcoxon signed-rank HAI PHÍA + sign test + bootstrap CI của median; Holm cho so sánh phụ.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import binomtest, wilcoxon

_OK = {"OK", "SHORTFALL"}


def effective_final(frame: pd.DataFrame) -> pd.Series:
    usable = (
        frame["status"].isin(_OK)
        & frame["polished_best_true_objective"].notna()
        & frame["polished_best_feasible"].fillna(False).astype(bool)
    )
    return frame["polished_best_true_objective"].where(usable, frame["j_no_action"])


def paired_frame(
    per_instance: pd.DataFrame, *, target: str, baseline: str
) -> pd.DataFrame:
    columns = [
        "instance_id",
        "track",
        "status",
        "polished_best_true_objective",
        "polished_best_feasible",
        "j_no_action",
        "improvement_scale",
        "target_regime",
    ]
    data = per_instance[[c for c in columns if c in per_instance.columns]].copy()
    data["final"] = effective_final(data)
    left = data.loc[data["track"] == target].set_index("instance_id")
    right = data.loc[data["track"] == baseline].set_index("instance_id")
    joined = left.join(right, how="inner", lsuffix="_target", rsuffix="_baseline")
    joined["uplift"] = joined["final_baseline"] - joined["final_target"]
    scale = joined["improvement_scale_target"].where(
        joined["improvement_scale_target"] > 0
    )
    joined["uplift_normalized"] = joined["uplift"] / scale
    return joined.reset_index()


def summarize_uplift(
    joined: pd.DataFrame,
    *,
    tie_tolerance: float,
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    uplift = joined["uplift"].to_numpy(dtype=float)
    normalized = joined["uplift_normalized"].to_numpy(dtype=float)
    n = int(uplift.size)
    if n == 0:
        return {"n": 0}
    wins = int((uplift > tie_tolerance).sum())
    losses = int((uplift < -tie_tolerance).sum())
    ties = n - wins - losses
    nonzero = uplift[np.abs(uplift) > tie_tolerance]
    wilcoxon_p = (
        float(wilcoxon(nonzero, alternative="two-sided").pvalue)
        if nonzero.size
        else None
    )
    sign_p = (
        float(binomtest(wins, wins + losses, 0.5).pvalue) if wins + losses else None
    )
    rng = np.random.default_rng(bootstrap_seed)
    draws = rng.integers(0, n, size=(bootstrap_resamples, n))
    medians = np.median(uplift[draws], axis=1)
    finite_norm = normalized[np.isfinite(normalized)]
    norm_medians = (
        np.median(
            finite_norm[
                rng.integers(
                    0, finite_norm.size, size=(bootstrap_resamples, finite_norm.size)
                )
            ],
            axis=1,
        )
        if finite_norm.size
        else np.array([np.nan])
    )
    return {
        "n": n,
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "median_uplift": float(np.median(uplift)),
        "mean_uplift": float(np.mean(uplift)),
        "std_uplift": float(np.std(uplift, ddof=1)) if n > 1 else None,
        "median_uplift_ci95": [
            float(np.quantile(medians, 0.025)),
            float(np.quantile(medians, 0.975)),
        ],
        "median_uplift_normalized": float(np.median(finite_norm))
        if finite_norm.size
        else None,
        "median_uplift_normalized_ci95": [
            float(np.nanquantile(norm_medians, 0.025)),
            float(np.nanquantile(norm_medians, 0.975)),
        ],
        "wilcoxon_two_sided_p": wilcoxon_p,
        "sign_test_two_sided_p": sign_p,
    }


def holm_adjust(pvalues: Mapping[str, float | None]) -> dict[str, float | None]:
    present = sorted((p, name) for name, p in pvalues.items() if p is not None)
    m = len(present)
    adjusted: dict[str, float | None] = {
        name: None for name, p in pvalues.items() if p is None
    }
    running = 0.0
    for rank, (p, name) in enumerate(present):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return adjusted


def evaluate_gates(
    comparisons: Mapping[str, Mapping[str, Any]],
    *,
    per_instance: pd.DataFrame,
    checklists_pass: bool,
    set_name: str,
    n_valid: int,
    statistics: Mapping[str, Any],
    primary_baseline: str,
    targets: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """Gate chung (H1, H2, H6) + gate theo từng target QAOA (H3, H4, H5).

    ``targets`` = {tên track QAOA: danh sách compute baseline khớp compute của nó}.
    """
    materiality = float(statistics["materiality_normalized_min"])
    severe = float(statistics["compute_view_severe_loss_normalized"])
    minimum = int(statistics["confirmation_min_instances"])
    latency = float(statistics["latency_budget_seconds"])
    gates: dict[str, Any] = {
        "H1_attribution": "PASS" if checklists_pass else "FAIL",
        "H6_quantum_claim": "SIMULATOR_ONLY_NO_ADVANTAGE_CLAIM",
        "by_target": {},
    }
    views = per_instance.groupby("instance_id")["view"].agg(set)
    both_views = bool(
        views.map(lambda v: {"candidate_budget", "compute_budget"} <= v).all()
    )
    gates["H2_fairness"] = "PASS" if both_views else "FAIL"
    controls = per_instance.loc[
        per_instance["track"].isin(["random_uniform", "boltzmann"])
    ]
    for target, compute_baselines in targets.items():
        target_rows = per_instance.loc[per_instance["track"] == target]
        verdicts: dict[str, Any] = {}
        if not target_rows.empty and "raw_best_abs_gap" in per_instance:
            gap = float(target_rows["raw_best_abs_gap"].median())
            control_gaps = controls.groupby("track")["raw_best_abs_gap"].median()
            signal = bool(len(control_gaps) and (gap < control_gaps).all())
            verdicts["H3_distribution_signal"] = {
                "verdict": "SIGNAL" if signal else "NO_SIGNAL",
                "median_raw_gap": gap,
                "control_median_raw_gap": control_gaps.to_dict(),
            }
        primary = comparisons.get(f"{target}_vs_{primary_baseline}", {})
        boltzmann = comparisons.get(f"{target}_vs_boltzmann", {})
        compute = [
            comparisons.get(f"{target}_vs_{name}", {}) for name in compute_baselines
        ]
        if set_name != "confirmation":
            h4 = "NOT_APPLICABLE_EXPLORATORY_SET"
        elif n_valid < minimum:
            h4 = f"INCONCLUSIVE_N_{n_valid}_LT_{minimum}"
        elif not primary.get("n"):
            h4 = "INCONCLUSIVE_NO_PAIRS"
        else:
            passes = (
                primary["median_uplift"] > 0
                and primary["median_uplift_ci95"][0] > 0
                and (primary.get("median_uplift_normalized") or 0.0) >= materiality
                and boltzmann.get("median_uplift", 0.0) >= 0.0
                and all(
                    (c.get("median_uplift_normalized") or 0.0) >= severe
                    for c in compute
                    if c
                )
            )
            h4 = "PASS" if passes else "FAIL"
        verdicts["H4_confirmation"] = h4
        if h4 == "PASS":
            wall = target_rows.get("extra_qaoa_wall_seconds")
            within = bool(wall is not None and wall.median() <= latency)
            verdicts["H5_product_value"] = "PASS" if within else "FAIL_LATENCY"
        else:
            verdicts["H5_product_value"] = "NOT_EVALUATED_H4_NOT_PASS"
        gates["by_target"][target] = verdicts
    return gates
