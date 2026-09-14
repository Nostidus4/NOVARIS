# Đỗ Ngọc Tân - kiểm attribution/fairness trước khi tin bất kỳ kết quả hybrid nào.
"""Checklist attribution cho thí nghiệm QAOA-assisted.

Chạy trên artifact đã ghi (DataFrame), không trên state trong bộ nhớ của runner — thứ được chấm là
thứ người review nhìn thấy. Mỗi check trả ``PASS``/``FAIL`` kèm chi tiết; runner hard-fail nếu có
check attribution FAIL.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from qshield_contracts.schemas.hybrid import (
    REFERENCE_TRACK,
    validate_candidate_pool,
    validate_polish_trace,
    validate_track_results,
)


def attribution_checklist(
    pools: pd.DataFrame,
    polish: pd.DataFrame,
    tracks: pd.DataFrame,
    *,
    bit_count: int,
    polish_top_k: int,
    polish_max_evaluations: int,
) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}

    def record(name: str, ok: bool, detail: Any = None) -> None:
        checks[name] = {"status": "PASS" if ok else "FAIL", "detail": detail}

    try:
        validate_candidate_pool(pools, bit_count=bit_count)
        record("pool_schema_and_no_exact_contamination", True)
    except ValueError as exc:
        record("pool_schema_and_no_exact_contamination", False, str(exc))
    try:
        validate_polish_trace(polish)
        record("polish_keeps_active_set_and_bounds", True)
    except ValueError as exc:
        record("polish_keeps_active_set_and_bounds", False, str(exc))
    try:
        validate_track_results(tracks)
        record("track_budget_accounting", True)
    except ValueError as exc:
        record("track_budget_accounting", False, str(exc))

    reference_bits = set(pools.loc[pools["track"] == REFERENCE_TRACK, "bitstring"])
    budget_view = tracks.loc[tracks["view"] == "candidate_budget"]
    record(
        "candidate_budget_equal_across_tracks",
        budget_view.groupby("instance_id")["budget_candidates"].nunique().le(1).all(),
    )
    generation_matches = (
        budget_view["true_evaluations_generation"] == budget_view["generated_unique"]
    ).all()
    record("generation_evaluations_equal_unique_candidates", bool(generation_matches))
    starts = polish.groupby(["instance_id", "track", "view"]).size()
    record(
        "same_polish_top_k",
        bool((starts <= polish_top_k).all()),
        {"max_starts": int(starts.max()) if len(starts) else 0, "limit": polish_top_k},
    )
    record(
        "same_polish_evaluation_cap",
        bool((polish["true_objective_evaluations"] <= polish_max_evaluations).all()),
        {"limit": polish_max_evaluations},
    )
    # Trùng bitstring với reference KHÔNG phải lỗi (QAOA được phép tự tìm ra optimum); lỗi là khi
    # provenance nói nguồn exact — đã chặn ở validate_candidate_pool. Ở đây chỉ báo số trùng.
    overlap = (
        pools.loc[pools["track"] != REFERENCE_TRACK]
        .assign(in_reference=lambda frame: frame["bitstring"].isin(reference_bits))
        .groupby("track")["in_reference"]
        .sum()
        .astype(int)
        .to_dict()
    )
    record(
        "reference_overlap_reported", True, {"overlap_with_reference_top_k": overlap}
    )
    status = (
        "PASS" if all(item["status"] == "PASS" for item in checks.values()) else "FAIL"
    )
    return {"status": status, "checks": checks}
