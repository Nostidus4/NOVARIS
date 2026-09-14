# Đỗ Ngọc Tân - QAOA pool: chạy đủ seed, xuất phân phối lossless, chọn B ứng viên theo luật khóa trước.
"""QAOA candidate pool — không bao giờ nhận nghiệm exact.

Luật chọn B ứng viên (khóa trước): gộp phân phối đo được của MỌI seed hoàn tất → chỉ giữ trạng
thái predicate-feasible → xếp theo tổng ``measured_count`` giảm dần, hòa thì energy tăng dần, rồi
bitstring. Four-level codec là song ánh nên dedup bitstring ≡ dedup effective action.

Energy mỗi trạng thái lấy từ state space NumPy; lệch với ``fval`` của Qiskit quá tolerance ⇒
raise (QUBO sai thì không tin QAOA — CLAUDE.md quy tắc 15).
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from qiskit_optimization import QuadraticProgram

from qshield_quantum.generators.common import (
    Proposal,
    StateSpace,
    bitstring_to_index,
)
from qshield_quantum.solvers.qaoa import (
    QaoaSeedResult,
    TranspileFallbackUnavailableError,
    solve_qaoa_one_seed_fast,
)

_ENERGY_TOLERANCE = 1e-6


@dataclass(frozen=True)
class QaoaRun:
    results: dict[int, QaoaSeedResult]
    attempts: list[dict[str, Any]] = field(default_factory=list)
    wall_seconds: float = 0.0
    shots: int = 0
    reps: int = 1
    maxiter: int = 1
    warm_start: bool = False


def run_qaoa_seeds(
    qp: QuadraticProgram,
    *,
    seeds: Sequence[int],
    shots: int,
    maxiter: int,
    reps: int,
    warm_start: bool,
    feasibility_constraints: Mapping[str, Any] | None,
    seed_timeout_seconds: float,
    total_timeout_seconds: float | None,
    solver: Any = solve_qaoa_one_seed_fast,
    aggregation: float | None = None,
    initial_point: Sequence[float] | None = None,
) -> QaoaRun:
    """Chạy tuần tự mọi seed; crash/timeout được GHI LẠI, không lọc bỏ."""
    results: dict[int, QaoaSeedResult] = {}
    attempts: list[dict[str, Any]] = []
    started = time.perf_counter()
    kwargs: dict[str, Any] = {
        "shots": shots,
        "maxiter": maxiter,
        "reps": reps,
        "warm_start": warm_start,
        "candidate_pool_size": 1,
        "subprocess_timeout_seconds": seed_timeout_seconds,
        "export_full_distribution": True,
    }
    if aggregation is not None:
        kwargs["aggregation"] = float(aggregation)
    if initial_point is not None:
        kwargs["initial_point"] = [float(v) for v in initial_point]
    if feasibility_constraints:
        kwargs["feasibility_constraints"] = dict(feasibility_constraints)
    else:
        kwargs["always_feasible"] = True
    for seed in seeds:
        elapsed = time.perf_counter() - started
        if total_timeout_seconds is not None and elapsed >= total_timeout_seconds:
            attempts.append(
                {"seed": int(seed), "status": "timeout", "reason": "total_timeout"}
            )
            continue
        seed_started = time.perf_counter()
        try:
            result = solver(qp, seed=int(seed), **kwargs)
        except TranspileFallbackUnavailableError as exc:
            attempts.append({"seed": int(seed), "status": "failed", "reason": str(exc)})
            continue
        except Exception as exc:  # noqa: BLE001 — mọi lỗi seed phải được ghi, không nuốt im lặng
            attempts.append(
                {
                    "seed": int(seed),
                    "status": "failed",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        seconds = time.perf_counter() - seed_started
        if not result.distribution:
            attempts.append(
                {"seed": int(seed), "status": "failed", "reason": "empty distribution"}
            )
            continue
        results[int(seed)] = result
        attempts.append(
            {
                "seed": int(seed),
                "status": "completed",
                "runtime_seconds": seconds,
                "transpiled": bool(result.transpiled),
                "warm_start_used": bool(result.warm_start_used),
                "optimal_parameters": list(result.optimal_parameters),
                "circuit_evaluations": int(result.circuit_evaluations),
                "initial_point": None if initial_point is None else list(initial_point),
            }
        )
    return QaoaRun(
        results=results,
        attempts=attempts,
        wall_seconds=time.perf_counter() - started,
        shots=shots,
        reps=reps,
        maxiter=maxiter,
        warm_start=warm_start,
    )


def distribution_rows(
    run: QaoaRun,
    space: StateSpace,
    *,
    energy_scale: float = 1.0,
    energy_offset: float = 0.0,
) -> list[dict[str, Any]]:
    """Một hàng / (seed, bitstring) đo được. Energy = NumPy state space (ground truth).

    Nếu QAOA chạy trên QUBO đã chuẩn hóa, energy Qiskit phải bằng
    ``energy_scale * (E_numpy − energy_offset)``; hàng ghi energy GỐC (chưa chuẩn hóa).
    """
    rows: list[dict[str, Any]] = []
    for seed, result in sorted(run.results.items()):
        for sample in result.distribution:
            index = bitstring_to_index(sample.bitstring)
            energy = float(space.energies[index])
            expected = energy_scale * (energy - energy_offset)
            if abs(expected - float(sample.energy)) > _ENERGY_TOLERANCE * max(
                1.0, abs(expected)
            ):
                raise ValueError(
                    f"[quantum.qaoa_pool] seed={seed} bitstring={sample.bitstring}: Qiskit "
                    f"energy {sample.energy} != expected {expected} (NumPy {energy}, "
                    f"scale={energy_scale}, offset={energy_offset}). Run verify/consistency.py."
                )
            rows.append(
                {
                    "seed": int(seed),
                    "bitstring": sample.bitstring,
                    "qubo_energy": energy,
                    "probability": float(sample.probability),
                    "measured_count": int(sample.measured_count),
                    "predicate_feasible": bool(space.predicate_feasible[index]),
                    "shots": int(run.shots),
                    "reps": int(run.reps),
                    "optimizer": "COBYLA",
                    "maxiter": int(run.maxiter),
                    "backend": "StatevectorSampler",
                    "warm_start": bool(run.warm_start),
                    "transpiled": bool(result.transpiled),
                }
            )
    return rows


def _pooled_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    pooled: dict[str, dict[str, Any]] = {}
    for row in rows:
        entry = pooled.setdefault(
            str(row["bitstring"]),
            {
                "count": 0,
                "by_seed": {},
                "energy": float(row["qubo_energy"]),
                "feasible": bool(row["predicate_feasible"]),
            },
        )
        entry["count"] += int(row["measured_count"])
        entry["by_seed"][int(row["seed"])] = int(row["measured_count"])
    return pooled


def qaoa_proposals(
    rows: Sequence[Mapping[str, Any]],
    space: StateSpace,
    *,
    budget: int,
    track: str = "qaoa",
) -> list[Proposal]:
    pooled = _pooled_counts(rows)
    total = sum(entry["count"] for entry in pooled.values())
    ordered = sorted(
        ((bits, entry) for bits, entry in pooled.items() if entry["feasible"]),
        key=lambda item: (-item[1]["count"], item[1]["energy"], item[0]),
    )[:budget]
    proposals: list[Proposal] = []
    for rank, (bits, entry) in enumerate(ordered, start=1):
        best_seed = min(entry["by_seed"].items(), key=lambda kv: (-kv[1], kv[0]))[0]
        proposals.append(
            space.proposal(
                bitstring_to_index(bits),
                source_method=f"{track}_sample",
                source_rank=rank,
                source_seed=int(best_seed),
                raw_probability=entry["count"] / total if total else None,
            )
        )
    return proposals


def distribution_metrics(
    rows: Sequence[Mapping[str, Any]],
    space: StateSpace,
    *,
    reference_indices: Mapping[str, int] | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """Coverage/entropy với numerator tuyệt đối — trả lời trực tiếp câu hỏi "1,9% tính thế nào"."""
    pooled = _pooled_counts(rows)
    total_shots = int(sum(entry["count"] for entry in pooled.values()))
    unique = len(pooled)
    unique_feasible = sum(1 for entry in pooled.values() if entry["feasible"])
    probabilities = (
        np.asarray([entry["count"] for entry in pooled.values()], dtype=float)
        / total_shots
        if total_shots
        else np.zeros(0)
    )
    entropy = (
        float(-(probabilities * np.log2(probabilities)).sum()) if total_shots else 0.0
    )
    per_seed: dict[int, dict[str, float]] = {}
    for row in rows:
        seed = int(row["seed"])
        item = per_seed.setdefault(
            seed,
            {
                "unique": 0,
                "feasible_mass": 0.0,
                "best_energy": float("inf"),
                "shots": 0,
            },
        )
        item["unique"] += 1
        item["shots"] += int(row["measured_count"])
        if row["predicate_feasible"]:
            item["feasible_mass"] += float(row["probability"])
            item["best_energy"] = min(item["best_energy"], float(row["qubo_energy"]))
    reference_mass = {
        name: pooled.get(format(index, f"0{space.bit_count}b"), {"count": 0})["count"]
        / total_shots
        if total_shots
        else 0.0
        for name, index in (reference_indices or {}).items()
    }
    return {
        "seeds_completed": len(per_seed),
        "total_shots": total_shots,
        "unique_measured": unique,
        "unique_predicate_feasible": unique_feasible,
        "total_states": space.total_states,
        "total_feasible_states": space.total_feasible_states,
        "coverage_all": unique / space.total_states,
        "coverage_all_fraction": f"{unique}/{space.total_states}",
        "coverage_feasible": unique_feasible / space.total_feasible_states,
        "coverage_feasible_fraction": f"{unique_feasible}/{space.total_feasible_states}",
        "duplicate_rate": 1.0 - unique / total_shots if total_shots else 0.0,
        "pooled_entropy_bits": entropy,
        "effective_sample_size": float(1.0 / (probabilities**2).sum())
        if total_shots
        else 0.0,
        "top_k": top_k,
        "top_k_mass": float(np.sort(probabilities)[::-1][:top_k].sum())
        if total_shots
        else 0.0,
        "feasible_mass_mean_per_seed": (
            float(np.mean([item["feasible_mass"] for item in per_seed.values()]))
            if per_seed
            else 0.0
        ),
        "pooled_mean_feasible_energy": (
            float(
                sum(e["count"] * e["energy"] for e in pooled.values() if e["feasible"])
                / max(1, sum(e["count"] for e in pooled.values() if e["feasible"]))
            )
            if unique_feasible
            else None
        ),
        "mass_on_reference": reference_mass,
        "per_seed": {str(seed): item for seed, item in sorted(per_seed.items())},
        "note": (
            "duplicates across shots/seeds counted once; coverage is unique measured states, "
            "not probability mass"
        ),
    }
