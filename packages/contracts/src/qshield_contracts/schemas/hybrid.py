# Đỗ Ngọc Tân - contracts cho thí nghiệm QAOA-assisted candidate generation + classical polishing.
"""Schemas cho track nghiên cứu hybrid (xem `plan-qaoa-assisted.md`).

Ba bất biến attribution được kiểm ở ĐÂY, tại ranh giới, thay vì tin vào code sinh ra artifact:

1. Exact chỉ là reference: không pool nào ngoài `exact_reference` được mang `source_method`
   chứa "exact" (không bí mật đưa nghiệm exact vào pool QAOA/random/classical).
2. Phân phối QAOA là lossless: tổng xác suất theo `(instance, seed)` xấp xỉ 1 — top-20 bị cắt
   không được phép đi qua schema này và bị gọi là "distribution".
3. Polishing giữ active set (primary attribution): trace có `active_set_changed=True` hoặc vi
   phạm zero-lock/±adjustment bị từ chối.

Module này chỉ kiểm hình dạng, provenance và nhất quán logic; không chứa công thức tài chính.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import pandera.pandas as pandera

from qshield_contracts.hashing import stable_hash
from qshield_contracts.validate import validate_or_raise

REFERENCE_TRACK = "exact_reference"
HYBRID_TRACKS = frozenset(
    {
        REFERENCE_TRACK,
        "classical_true",
        "classical_surrogate",
        "random_uniform",
        "random_stratified",
        "boltzmann",
        "qaoa",
        "qaoa_warm_start",
        "qaoa_transfer",
        "classical_true_compute",
        "random_uniform_compute",
        "classical_true_compute_transfer",
        "random_uniform_compute_transfer",
        "heuristic_baselines",
    }
)
BUDGET_VIEWS = frozenset(
    {"candidate_budget", "compute_budget", "reference", "ablation"}
)
POLISH_STOP_REASONS = frozenset({"converged", "eval_budget"})
TRACK_STATUSES = frozenset({"OK", "SHORTFALL", "FAILED", "TIMEOUT", "EMPTY"})
MANIFEST_STATUSES = frozenset({"EXPLORATORY_NON_BASELINE", "CONFIRMATION_NON_BASELINE"})

_BITSTRING = pandera.Check.str_matches(r"^[01]+$")

QaoaDistributionSchema = pandera.DataFrameSchema(
    {
        "experiment_id": pandera.Column(str),
        "instance_id": pandera.Column(str),
        "track": pandera.Column(
            str, pandera.Check.isin(["qaoa", "qaoa_warm_start", "qaoa_transfer"])
        ),
        "seed": pandera.Column(int),
        "bitstring": pandera.Column(str, _BITSTRING),
        "qubo_energy": pandera.Column(float),
        "probability": pandera.Column(float, pandera.Check.in_range(0.0, 1.0)),
        "measured_count": pandera.Column(int, pandera.Check.ge(0)),
        "predicate_feasible": pandera.Column(bool),
        "shots": pandera.Column(int, pandera.Check.gt(0)),
        "reps": pandera.Column(int, pandera.Check.ge(1)),
        "optimizer": pandera.Column(str),
        "maxiter": pandera.Column(int, pandera.Check.ge(1)),
        "backend": pandera.Column(str),
        "warm_start": pandera.Column(bool),
        "transpiled": pandera.Column(bool),
        "candidate_order_hash": pandera.Column(str),
        "qubo_hash": pandera.Column(str),
    },
    strict=False,
    coerce=True,
)

CandidatePoolSchema = pandera.DataFrameSchema(
    {
        "experiment_id": pandera.Column(str),
        "instance_id": pandera.Column(str),
        "track": pandera.Column(str, pandera.Check.isin(sorted(HYBRID_TRACKS))),
        "view": pandera.Column(str, pandera.Check.isin(sorted(BUDGET_VIEWS))),
        "source_method": pandera.Column(str),
        "source_seed": pandera.Column("Int64", nullable=True),
        "source_rank": pandera.Column(int, pandera.Check.ge(1)),
        "raw_probability": pandera.Column(float, nullable=True),
        "qubo_energy": pandera.Column(float),
        "bitstring": pandera.Column(str, _BITSTRING),
        "effective_action_hash": pandera.Column(str),
        "predicate_feasible": pandera.Column(bool),
        "true_objective": pandera.Column(float),
        "true_feasible": pandera.Column(bool),
        "candidate_order_hash": pandera.Column(str),
        "qubo_hash": pandera.Column(str),
    },
    strict=False,
    coerce=True,
)

PolishTraceSchema = pandera.DataFrameSchema(
    {
        "experiment_id": pandera.Column(str),
        "instance_id": pandera.Column(str),
        "track": pandera.Column(str, pandera.Check.isin(sorted(HYBRID_TRACKS))),
        "view": pandera.Column(str, pandera.Check.isin(sorted(BUDGET_VIEWS))),
        "start_rank": pandera.Column(int, pandera.Check.ge(1)),
        "start_bitstring": pandera.Column(str, _BITSTRING),
        "start_true_objective": pandera.Column(float),
        "final_true_objective": pandera.Column(float),
        "objective_improvement": pandera.Column(float),
        "true_objective_evaluations": pandera.Column(int, pandera.Check.ge(0)),
        "iterations": pandera.Column(int, pandera.Check.ge(0)),
        "wall_seconds": pandera.Column(float, pandera.Check.ge(0.0)),
        "active_set_changed": pandera.Column(bool),
        "zero_action_lock_respected": pandera.Column(bool),
        "max_adjustment_respected": pandera.Column(bool),
        "stop_reason": pandera.Column(
            str, pandera.Check.isin(sorted(POLISH_STOP_REASONS))
        ),
        "final_feasible": pandera.Column(bool),
    },
    strict=False,
    coerce=True,
)

TrackResultSchema = pandera.DataFrameSchema(
    {
        "experiment_id": pandera.Column(str),
        "instance_id": pandera.Column(str),
        "track": pandera.Column(str, pandera.Check.isin(sorted(HYBRID_TRACKS))),
        "view": pandera.Column(str, pandera.Check.isin(sorted(BUDGET_VIEWS))),
        "status": pandera.Column(str, pandera.Check.isin(sorted(TRACK_STATUSES))),
        "budget_candidates": pandera.Column(int, pandera.Check.ge(0)),
        "generated_unique": pandera.Column(int, pandera.Check.ge(0)),
        "shortfall": pandera.Column(int, pandera.Check.ge(0)),
        "true_evaluations_generation": pandera.Column(int, pandera.Check.ge(0)),
        "true_evaluations_polish": pandera.Column(int, pandera.Check.ge(0)),
        "raw_best_true_objective": pandera.Column(float, nullable=True),
        "polished_best_true_objective": pandera.Column(float, nullable=True),
        "generation_seconds": pandera.Column(float, pandera.Check.ge(0.0)),
        "polish_seconds": pandera.Column(float, pandera.Check.ge(0.0)),
    },
    strict=False,
    coerce=True,
)


def _check_bit_length(
    frame: pd.DataFrame, column: str, bit_count: int, context: str
) -> None:
    lengths = frame[column].astype(str).str.len()
    bad = frame.loc[lengths != bit_count, column]
    if not bad.empty:
        raise ValueError(
            f"[{context}] {len(bad)} {column} rows have length != {bit_count}; "
            f"first={bad.iloc[0]!r}."
        )


def _check_single_hash_per_instance(frame: pd.DataFrame, context: str) -> None:
    for column in ("candidate_order_hash", "qubo_hash"):
        counts = frame.groupby("instance_id")[column].nunique()
        mixed = counts[counts > 1]
        if not mixed.empty:
            raise ValueError(
                f"[{context}] mixed {column} inside instance(s): {mixed.index.tolist()}."
            )


def validate_qaoa_distribution(
    frame: pd.DataFrame, *, bit_count: int, probability_tolerance: float = 1e-6
) -> pd.DataFrame:
    """Lossless QAOA distribution: Σp≈1 theo (instance, track, seed), không trùng bitstring."""
    context = "contracts.hybrid.qaoa_distribution"
    validated = validate_or_raise(frame, QaoaDistributionSchema, context=context)
    if validated.empty:
        return validated
    _check_bit_length(validated, "bitstring", bit_count, context)
    _check_single_hash_per_instance(validated, context)
    keys = ["instance_id", "track", "seed", "bitstring"]
    if validated.duplicated(keys).any():
        raise ValueError(
            f"[{context}] duplicate (instance, track, seed, bitstring) rows."
        )
    sums = validated.groupby(["instance_id", "track", "seed"])["probability"].sum()
    off = sums[(sums - 1.0).abs() > probability_tolerance]
    if not off.empty:
        raise ValueError(
            f"[{context}] probability mass is not lossless for {off.index.tolist()[:3]}: "
            f"sums={off.tolist()[:3]}. Truncated distributions must not use this schema."
        )
    return validated


def validate_candidate_pool(frame: pd.DataFrame, *, bit_count: int) -> pd.DataFrame:
    """Pool theo nguồn: không exact contamination, dedup theo effective action trong từng track."""
    context = "contracts.hybrid.candidate_pool"
    validated = validate_or_raise(frame, CandidatePoolSchema, context=context)
    if validated.empty:
        return validated
    _check_bit_length(validated, "bitstring", bit_count, context)
    _check_single_hash_per_instance(validated, context)
    non_reference = validated["track"] != REFERENCE_TRACK
    contaminated = validated.loc[
        non_reference & validated["source_method"].str.contains("exact", case=False)
    ]
    if not contaminated.empty:
        raise ValueError(
            f"[{context}] exact contamination: {len(contaminated)} row(s) in tracks "
            f"{sorted(contaminated['track'].unique())} carry an exact source_method."
        )
    keys = ["instance_id", "track", "view", "effective_action_hash"]
    if validated.duplicated(keys).any():
        raise ValueError(
            f"[{context}] duplicate effective actions inside a track — dedup must happen "
            "after decode, before scoring."
        )
    return validated


def validate_polish_trace(
    frame: pd.DataFrame, *, tolerance: float = 1e-12
) -> pd.DataFrame:
    """Polish trace: cùng active set, zero-lock/±adjustment giữ, improvement khớp start−final."""
    context = "contracts.hybrid.polish_trace"
    validated = validate_or_raise(frame, PolishTraceSchema, context=context)
    if validated.empty:
        return validated
    for column in ("zero_action_lock_respected", "max_adjustment_respected"):
        if not validated[column].all():
            raise ValueError(f"[{context}] {column} is False for some polish rows.")
    if validated["active_set_changed"].any():
        raise ValueError(
            f"[{context}] active_set_changed=True — primary attribution requires the "
            "candidate's active set to survive polishing."
        )
    expected = validated["start_true_objective"] - validated["final_true_objective"]
    if ((validated["objective_improvement"] - expected).abs() > 1e-9).any():
        raise ValueError(f"[{context}] objective_improvement != start - final.")
    return validated


def validate_track_results(frame: pd.DataFrame) -> pd.DataFrame:
    """Kết quả tổng hợp theo (instance, track, view) — shortfall/budget nhất quán."""
    context = "contracts.hybrid.track_results"
    validated = validate_or_raise(frame, TrackResultSchema, context=context)
    if validated.empty:
        return validated
    keys = ["instance_id", "track", "view"]
    if validated.duplicated(keys).any():
        raise ValueError(f"[{context}] duplicate (instance, track, view) rows.")
    budget = validated["view"] == "candidate_budget"
    inconsistent = validated.loc[
        budget
        & (
            validated["generated_unique"] + validated["shortfall"]
            != validated["budget_candidates"]
        )
    ]
    if not inconsistent.empty:
        raise ValueError(
            f"[{context}] candidate_budget rows violate generated_unique + shortfall == budget "
            f"for {inconsistent[['instance_id', 'track']].values.tolist()[:3]}."
        )
    return validated


_REQUIRED_INSTANCE_KEYS = (
    "instance_id",
    "as_of_date",
    "target_regime",
    "portfolio_id",
    "scenario_seed",
    "set",
)


def manifest_instances_hash(instances: list[Mapping[str, Any]]) -> str:
    """Hash khóa danh sách instance — commit TRƯỚC khi chạy (preregistration)."""
    return stable_hash([dict(item) for item in instances])


def validate_hybrid_manifest(manifest: Mapping[str, Any]) -> None:
    """Manifest phải khóa được: instance unique, hash khớp nội dung, nhãn non-baseline."""
    context = "contracts.hybrid.manifest"
    for key in (
        "experiment_id",
        "status",
        "instances",
        "instances_hash",
        "selection_rule",
    ):
        if key not in manifest:
            raise ValueError(f"[{context}] missing key {key!r}.")
    if manifest["status"] not in MANIFEST_STATUSES:
        raise ValueError(
            f"[{context}] status={manifest['status']!r}; expected one of "
            f"{sorted(MANIFEST_STATUSES)}."
        )
    instances = list(manifest["instances"])
    if not instances:
        raise ValueError(f"[{context}] instances must be non-empty.")
    seen: set[str] = set()
    for item in instances:
        missing = [key for key in _REQUIRED_INSTANCE_KEYS if key not in item]
        if missing:
            raise ValueError(f"[{context}] instance missing keys {missing}: {item}.")
        instance_id = str(item["instance_id"])
        if instance_id in seen:
            raise ValueError(f"[{context}] duplicate instance_id {instance_id!r}.")
        seen.add(instance_id)
    if manifest_instances_hash(instances) != manifest["instances_hash"]:
        raise ValueError(
            f"[{context}] instances_hash does not match instance content — the manifest was "
            "edited after it was locked. Create a new experiment version instead."
        )
