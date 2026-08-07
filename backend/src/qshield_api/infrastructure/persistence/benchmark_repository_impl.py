# Đỗ Ngọc Tân - FileBenchmarkRepository — ưu tiên workflow_benchmark.json (packages workflow_update).
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qshield_contracts.config import Config
from qshield_contracts.enums import Stage

from qshield_api.domain.benchmark.entities import BenchmarkView
from qshield_api.infrastructure.persistence.artifact_reader import (
    build_paths,
    read_json,
)


def _runtime_total(payload: dict[str, Any]) -> float:
    if payload.get("runtime_seconds_total") not in (None, 0, 0.0):
        return float(payload["runtime_seconds_total"])
    runtime = payload.get("runtime_seconds") or {}
    if isinstance(runtime, dict) and runtime:
        return float(sum(float(v) for v in runtime.values()))
    timings = payload.get("stage_timings_seconds") or {}
    if isinstance(timings, dict) and "total" in timings:
        return float(timings["total"])
    return 0.0


def _view_from_workflow(payload: dict[str, Any]) -> BenchmarkView:
    exact_bits = str(
        payload.get("exact_best_bitstring")
        or payload.get("exact_best_feasible_bitstring")
        or payload.get("winning_bitstring")
        or ""
    )
    exact_energy = float(
        payload.get("exact_best_energy")
        if payload.get("exact_best_energy") is not None
        else payload.get("exact_best_feasible_energy")
        if payload.get("exact_best_feasible_energy") is not None
        else payload.get("winning_energy") or 0.0
    )
    winning_seed = payload.get("winning_seed")
    return BenchmarkView(
        winning_seed=None if winning_seed is None else int(winning_seed),
        winning_bitstring=str(payload.get("winning_bitstring") or exact_bits),
        winning_energy=float(payload.get("winning_energy") or exact_energy),
        winning_is_feasible=bool(payload.get("winning_is_feasible", True)),
        n_seeds_feasible=int(payload.get("n_seeds_feasible") or 0),
        n_seeds_total=int(payload.get("n_seeds_total") or 0),
        exact_best_feasible_bitstring=exact_bits,
        exact_best_feasible_energy=exact_energy,
        exact_evaluated_states=int(payload.get("exact_evaluated_states") or 0),
        optimality_gap=(
            None
            if payload.get("optimality_gap") is None
            else float(payload["optimality_gap"])
        ),
        mean_feasibility_rate=(
            None
            if payload.get("mean_feasibility_rate") is None
            else float(payload["mean_feasibility_rate"])
        ),
        mean_success_prob=(
            None
            if payload.get("mean_success_prob") is None
            else float(payload["mean_success_prob"])
        ),
        classical_bitstring=str(payload.get("classical_bitstring") or exact_bits),
        classical_energy=float(
            payload.get("classical_energy")
            if payload.get("classical_energy") is not None
            else exact_energy
        ),
        classical_gap=(
            None
            if payload.get("classical_gap") is None
            else float(payload["classical_gap"])
        ),
        qaoa_beats_classical=bool(payload.get("qaoa_beats_classical", False)),
        runtime_seconds_total=_runtime_total(payload),
        caveat=str(payload.get("caveat") or ""),
        source_artifact="workflow_benchmark.json",
        profile_id=(
            None if payload.get("profile_id") is None else str(payload["profile_id"])
        ),
        requested_solver=(
            None
            if payload.get("requested_solver") is None
            else str(payload["requested_solver"])
        ),
        actual_solver=(
            None
            if payload.get("actual_solver") is None
            else str(payload["actual_solver"])
        ),
        fallback_reason=(
            None
            if payload.get("fallback_reason") is None
            else str(payload["fallback_reason"])
        ),
    )


def _view_from_legacy(payload: dict[str, Any]) -> BenchmarkView:
    return BenchmarkView(
        winning_seed=int(payload["winning_seed"]),
        winning_bitstring=str(payload["winning_bitstring"]),
        winning_energy=float(payload["winning_energy"]),
        winning_is_feasible=bool(payload["winning_is_feasible"]),
        n_seeds_feasible=int(payload["n_seeds_feasible"]),
        n_seeds_total=int(payload["n_seeds_total"]),
        exact_best_feasible_bitstring=str(payload["exact_best_feasible_bitstring"]),
        exact_best_feasible_energy=float(payload["exact_best_feasible_energy"]),
        exact_evaluated_states=int(payload["exact_evaluated_states"]),
        optimality_gap=float(payload["optimality_gap"]),
        mean_feasibility_rate=float(payload["mean_feasibility_rate"]),
        mean_success_prob=float(payload["mean_success_prob"]),
        classical_bitstring=str(payload["classical_bitstring"]),
        classical_energy=float(payload["classical_energy"]),
        classical_gap=float(payload["classical_gap"]),
        qaoa_beats_classical=bool(payload["qaoa_beats_classical"]),
        runtime_seconds_total=float(payload["runtime_seconds_total"]),
        caveat=str(payload["caveat"]),
        source_artifact="benchmark.json",
        profile_id=None,
        requested_solver=None,
        actual_solver=None,
        fallback_reason=None,
    )


@dataclass(frozen=True)
class FileBenchmarkRepository:
    cfg: Config

    def get_benchmark(self) -> BenchmarkView | None:
        paths = build_paths(self.cfg)
        workflow = read_json(paths, Stage.SOLVE, "workflow_benchmark.json")
        if workflow is not None:
            return _view_from_workflow(workflow)
        legacy = read_json(paths, Stage.SOLVE, "benchmark.json")
        if legacy is None:
            return None
        return _view_from_legacy(legacy)
