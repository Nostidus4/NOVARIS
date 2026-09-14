# Đỗ Ngọc Tân - gom artifact instance → bảng paired, summary, gate, claim checklist, report markdown.
"""Báo cáo thí nghiệm hybrid — chỉ đọc artifact đã ghi, không chạy lại tính toán."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd
from qshield_contracts.enums import Stage
from qshield_contracts.paths import ArtifactPaths

from qshield_pipeline.hybrid.settings import HybridSettings
from qshield_pipeline.hybrid.stats import (
    evaluate_gates,
    holm_adjust,
    paired_frame,
    summarize_uplift,
)


def _load_instances(root: Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frames: list[pd.DataFrame] = []
    results: list[dict[str, Any]] = []
    for result_path in sorted((root / "instances").glob("*/instance_result.json")):
        result = json.loads(result_path.read_text(encoding="utf-8"))
        tracks = pd.read_csv(result_path.parent / "track_results.csv")
        references = result["references"]
        tracks["set"] = result["instance"]["set"]
        tracks["target_regime"] = result["instance"]["target_regime"]
        tracks["portfolio_id"] = result["instance"]["portfolio_id"]
        tracks["as_of_date"] = result["instance"]["as_of_date"]
        tracks["scenario_gate"] = result["input_metadata"]["scenario_gate"]
        tracks["j_no_action"] = references["j_no_action"]
        tracks["j_star_grid"] = references.get("j_star_grid")
        tracks["j_best_known"] = references.get("j_best_known")
        tracks["improvement_scale"] = references.get(
            "improvement_scale_no_action_minus_best_known"
        )
        frames.append(tracks)
        results.append(result)
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), results


def _read_attempts(root: Path) -> list[dict[str, Any]]:
    path = root / "hybrid_attempts.jsonl"
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def build_report(
    paths: ArtifactPaths, settings: HybridSettings, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    root = paths.for_stage(Stage.HYBRID, settings.experiment_id)
    set_name = str(manifest["set"])
    per_instance, results = _load_instances(root)
    manifest_ids = {item["instance_id"] for item in manifest["instances"]}
    if not per_instance.empty:
        per_instance = per_instance.loc[per_instance["instance_id"].isin(manifest_ids)]
        results = [r for r in results if r["instance_id"] in manifest_ids]
    attempts = [a for a in _read_attempts(root) if a["instance_id"] in manifest_ids]
    latest_attempt: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        latest_attempt[attempt["instance_id"]] = attempt
    statistics = settings.statistics
    tie = float(statistics["tie_tolerance"])
    resamples = int(statistics["bootstrap_resamples"])
    seed = int(statistics["bootstrap_seed"])
    valid_ids = sorted(
        {
            r["instance_id"]
            for r in results
            if r["input_metadata"]["scenario_gate"]
            not in {"FAIL", "NO_REFERENCE_WINDOWS"}
            and r["references"].get("true_feasible_states", 1) > 0
        }
    )

    targets: dict[str, list[str]] = {
        str(name): list((spec or {}).get("compute_baselines", []))
        for name, spec in (statistics.get("targets") or {}).items()
    } or {"qaoa": list(statistics["compute_baselines"])}
    primary_baseline = str(statistics["primary_baseline"])
    comparisons: dict[str, dict[str, Any]] = {}
    paired_tables: list[pd.DataFrame] = []
    if not per_instance.empty:
        scoped = per_instance.loc[per_instance["instance_id"].isin(valid_ids)]
        available = set(scoped["track"])
        for target, compute_baselines in targets.items():
            if target not in available:
                continue
            baselines = [
                primary_baseline,
                *statistics["secondary_baselines"],
                *compute_baselines,
            ]
            names = []
            for baseline in baselines:
                if baseline not in available:
                    continue
                joined = paired_frame(scoped, target=target, baseline=baseline)
                name = f"{target}_vs_{baseline}"
                names.append(name)
                comparisons[name] = summarize_uplift(
                    joined,
                    tie_tolerance=tie,
                    bootstrap_resamples=resamples,
                    bootstrap_seed=seed,
                )
                paired_tables.append(joined.assign(comparison=name, target=target))
            adjusted = holm_adjust(
                {
                    n: comparisons[n].get("wilcoxon_two_sided_p")
                    for n in names
                    if n != f"{target}_vs_{primary_baseline}"
                }
            )
            for name, value in adjusted.items():
                comparisons[name]["wilcoxon_holm_p"] = value

    checklists_pass = bool(results) and all(
        r["attribution_checklist"]["status"] == "PASS" for r in results
    )
    gates = evaluate_gates(
        comparisons,
        per_instance=per_instance
        if not per_instance.empty
        else pd.DataFrame(columns=["instance_id", "view", "track"]),
        checklists_pass=checklists_pass,
        set_name=set_name,
        n_valid=len(valid_ids),
        statistics=statistics,
        primary_baseline=primary_baseline,
        targets=targets,
    )
    by_regime: dict[str, Any] = {}
    if paired_tables:
        all_pairs = pd.concat(paired_tables)
        for target in targets:
            primary = all_pairs.loc[
                all_pairs["comparison"] == f"{target}_vs_{primary_baseline}"
            ]
            for regime, group in primary.groupby("target_regime_target"):
                by_regime[f"{target}:{regime}"] = {
                    "n": len(group),
                    "median_uplift": float(group["uplift"].median()),
                    "wins": int((group["uplift"] > tie).sum()),
                    "losses": int((group["uplift"] < -tie).sum()),
                }
    phase0 = [
        {
            "instance_id": r["instance_id"],
            **r["phase0_answers"],
            "unique_measured": r["qaoa_distribution_metrics"].get("unique_measured"),
            "total_shots": r["qaoa_distribution_metrics"].get("total_shots"),
            "mass_on_reference": r["qaoa_distribution_metrics"].get(
                "mass_on_reference"
            ),
            "spearman_energy_vs_true": r["references"].get(
                "spearman_energy_vs_true_all_feasible"
            ),
            "qubo_optimum_true_rank": r["references"].get("qubo_optimum_true_rank"),
        }
        for r in results
    ]
    summary = {
        "experiment_id": settings.experiment_id,
        "set": set_name,
        "status_label": manifest["status"],
        "manifest_hash": manifest["instances_hash"],
        "instances_in_manifest": len(manifest_ids),
        "instances_completed": len(results),
        "instances_valid_for_statistics": len(valid_ids),
        "attempt_status_counts": pd.Series(
            [a["status"] for a in latest_attempt.values()]
        )
        .value_counts()
        .to_dict()
        if latest_attempt
        else {},
        "failure_rule": "failed/infeasible track final := J_no_action (counts as loss)",
        "comparisons": comparisons,
        "by_regime_primary": by_regime,
        "gates": gates,
        "phase0_answers": phase0,
        "claim_scope": "QAOA-assisted hybrid on StatevectorSampler simulator; no quantum "
        "advantage or speedup claim",
    }
    prefix = f"{set_name}_"
    if not per_instance.empty:
        per_instance.to_csv(
            root / f"{prefix}hybrid_benchmark_per_instance.csv", index=False
        )
    if paired_tables:
        pd.concat(paired_tables).to_csv(
            root / f"{prefix}hybrid_paired_uplift.csv", index=False
        )
    (root / f"{prefix}hybrid_benchmark_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    checklist = {
        "experiment_id": settings.experiment_id,
        "set": set_name,
        "artifacts_per_instance": [
            "qaoa_distribution.csv.gz",
            "candidate_pools.csv.gz",
            "polishing_results.csv.gz",
            "track_results.csv",
            "instance_result.json",
        ],
        "exact_isolated_in_reference_track": checklists_pass,
        "both_budget_views": gates["H2_fairness"],
        "failures_retained_in_attempts": len(attempts),
        "gates": gates,
        "allowed_wording": (
            "Trong protocol đã đăng ký, QAOA-assisted cải thiện true objective sau cùng polishing "
            "so với control"
            if any(
                v.get("H4_confirmation") == "PASS" for v in gates["by_target"].values()
            )
            else "Chưa đủ bằng chứng để claim QAOA tạo giá trị tăng thêm ở scope hiện tại"
        ),
    }
    (root / f"{prefix}hybrid_claim_checklist.json").write_text(
        json.dumps(checklist, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return summary
