# Đỗ Ngọc Tân - đọc và kiểm tra khóa `hybrid_experiment` (không hard-code tham số thí nghiệm).
"""Settings của thí nghiệm hybrid, đọc từ ``configs/experiments/hybrid_v1.yaml``."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_CANDIDATE_TRACKS = {
    "classical_true",
    "classical_surrogate",
    "random_uniform",
    "random_stratified",
    "boltzmann",
    "qaoa",
    "qaoa_transfer",
}
_COMPUTE_TRACKS = {
    "classical_true_compute",
    "random_uniform_compute",
    "classical_true_compute_transfer",
    "random_uniform_compute_transfer",
}
_ABLATION_TRACKS = {"heuristic_baselines"}


def _require(mapping: Mapping[str, Any], key: str, context: str) -> Any:
    if key not in mapping or mapping[key] is None:
        raise ValueError(f"[pipeline.hybrid.settings] missing {context}.{key}.")
    return mapping[key]


@dataclass(frozen=True)
class HybridSettings:
    raw: dict[str, Any]
    experiment_id: str
    candidate_count: int
    num_scenarios: int
    universe_lookback_start: str
    min_eligible_blocks: int
    candidate_budget: int
    polish_top_k: int
    polish_max_evaluations: int
    polish_max_adjustment: float
    reference_polish_top_k: int
    compute_budget_max_evaluations: int
    eval_timing_samples: int
    candidate_tracks: tuple[str, ...]
    compute_tracks: tuple[str, ...]
    ablation_tracks: tuple[str, ...]
    qaoa: dict[str, Any]
    generator_seeds: dict[str, int]
    grid_max_bits: int
    grid_workers: int
    grid_chunk_size: int
    near_optimal_eps: tuple[float, ...]
    recall_top_k: tuple[int, ...]
    diversity_sample: int
    statistics: dict[str, Any]

    @property
    def bit_count(self) -> int:
        return 2 * self.candidate_count

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> HybridSettings:
        raw = config.get("hybrid_experiment")
        if not isinstance(raw, Mapping):
            raise TypeError(
                "[pipeline.hybrid.settings] hybrid_experiment block is required; pass "
                "--override configs/experiments/hybrid_v1.yaml."
            )
        budgets = _require(raw, "budgets", "hybrid_experiment")
        tracks = _require(raw, "tracks", "hybrid_experiment")
        reference = _require(raw, "reference", "hybrid_experiment")
        metrics = _require(raw, "metrics", "hybrid_experiment")
        candidate_tracks = tuple(str(t) for t in tracks.get("candidate_budget", []))
        compute_tracks = tuple(str(t) for t in tracks.get("compute_budget", []))
        ablation_tracks = tuple(str(t) for t in tracks.get("ablation", []))
        unknown = (
            (set(candidate_tracks) - _CANDIDATE_TRACKS)
            | (set(compute_tracks) - _COMPUTE_TRACKS)
            | (set(ablation_tracks) - _ABLATION_TRACKS)
        )
        if unknown:
            raise ValueError(
                f"[pipeline.hybrid.settings] unknown tracks {sorted(unknown)}."
            )
        if "boltzmann" in candidate_tracks and "qaoa" not in candidate_tracks:
            raise ValueError(
                "[pipeline.hybrid.settings] boltzmann control needs the qaoa track."
            )
        seeds = {
            str(k): int(v)
            for k, v in _require(raw, "generator_seeds", "hybrid").items()
        }
        missing_seeds = sorted(
            (set(candidate_tracks) | set(compute_tracks))
            - {"qaoa", "qaoa_transfer"}
            - set(seeds)
        )
        if missing_seeds:
            raise ValueError(
                f"[pipeline.hybrid.settings] generator_seeds missing {missing_seeds}."
            )
        qaoa = dict(_require(raw, "qaoa", "hybrid_experiment"))
        if "qaoa_transfer" in candidate_tracks and not (qaoa.get("transfer") or {}).get(
            "maxiter"
        ):
            raise ValueError(
                "[pipeline.hybrid.settings] qaoa_transfer needs qaoa.transfer.maxiter."
            )
        needs_transfer = any(t.endswith("_transfer") for t in compute_tracks)
        if needs_transfer and "qaoa_transfer" not in candidate_tracks:
            raise ValueError(
                "[pipeline.hybrid.settings] *_transfer compute tracks need qaoa_transfer."
            )
        if len(qaoa.get("seeds", [])) < 1:
            raise ValueError("[pipeline.hybrid.settings] qaoa.seeds must be non-empty.")
        settings = cls(
            raw=dict(raw),
            experiment_id=str(_require(raw, "experiment_id", "hybrid_experiment")),
            candidate_count=int(_require(raw, "candidate_count", "hybrid_experiment")),
            num_scenarios=int(_require(raw, "num_scenarios", "hybrid_experiment")),
            universe_lookback_start=str(
                _require(raw, "universe_lookback_start", "hybrid")
            ),
            min_eligible_blocks=int(
                _require(raw, "min_eligible_blocks", "hybrid_experiment")
            ),
            candidate_budget=int(_require(budgets, "candidate_budget", "budgets")),
            polish_top_k=int(_require(budgets, "polish_top_k", "budgets")),
            polish_max_evaluations=int(
                _require(budgets, "polish_max_evaluations", "budgets")
            ),
            polish_max_adjustment=float(
                _require(budgets, "polish_max_adjustment", "budgets")
            ),
            reference_polish_top_k=int(
                _require(budgets, "reference_polish_top_k", "budgets")
            ),
            compute_budget_max_evaluations=int(
                _require(budgets, "compute_budget_max_evaluations", "budgets")
            ),
            eval_timing_samples=int(budgets.get("eval_timing_samples", 30)),
            candidate_tracks=candidate_tracks,
            compute_tracks=compute_tracks,
            ablation_tracks=ablation_tracks,
            qaoa=qaoa,
            generator_seeds=seeds,
            grid_max_bits=int(
                _require(reference, "exact_true_grid_max_bits", "reference")
            ),
            grid_workers=int(reference.get("grid_workers", 1)),
            grid_chunk_size=int(reference.get("grid_chunk_size", 2048)),
            near_optimal_eps=tuple(
                float(v) for v in metrics.get("near_optimal_eps", [])
            ),
            recall_top_k=tuple(int(v) for v in metrics.get("recall_top_k", [])),
            diversity_sample=int(metrics.get("diversity_sample", 200)),
            statistics=dict(raw.get("statistics") or {}),
        )
        if settings.candidate_count < 1 or settings.candidate_budget < 1:
            raise ValueError(
                "[pipeline.hybrid.settings] candidate_count/budget must be >= 1."
            )
        if not 0.0 <= settings.polish_max_adjustment <= 0.05:
            raise ValueError(
                "[pipeline.hybrid.settings] polish_max_adjustment must be <= 0.05."
            )
        return settings
