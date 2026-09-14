# Đỗ Ngọc Tân - parameter transfer cho QAOA: góc tối ưu từ tập nguồn → điểm khởi đầu cho instance khác.
"""QAOA parameter transfer (khóa trước khi dùng cho confirmation).

Luật:
1. Nguồn = mọi seed ``completed`` của track ``qaoa`` (COBYLA đầy đủ, QUBO đã chuẩn hóa energy) trên
   các instance của ``source_set``.
2. Chuẩn tắc hóa đối xứng p=1 trước khi gộp: thứ tự tham số của Qiskit là ``[β..., γ...]``;
   ``(β, γ) → (−β, −γ)`` cho cùng phân phối đo (Hamiltonian thực) ⇒ ép ``γ_0 ≥ 0``; ``β`` tuần hoàn
   chu kỳ π (mixer X) ⇒ đưa về ``(−π/2, π/2]``.
3. Góc chuyển = median theo từng tham số. Instance thuộc chính ``source_set`` nhận median
   leave-one-out (không dùng góc của chính nó); instance ngoài tập nguồn nhận median gộp.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np


def canonicalize(parameters: Sequence[float], reps: int) -> np.ndarray:
    values = np.asarray(parameters, dtype=float)
    if values.shape != (2 * reps,):
        raise ValueError(f"expected {2 * reps} QAOA parameters, got {values.shape}.")
    if values[reps] < 0:
        values = -values
    betas = values[:reps]
    values[:reps] = np.mod(betas + np.pi / 2, np.pi) - np.pi / 2
    return values


def build_transfer_parameters(
    root: Path, instance_ids: Sequence[str], *, source_set: str, reps: int
) -> dict[str, Any]:
    per_instance: dict[str, list[list[float]]] = {}
    for instance_id in instance_ids:
        path = root / "instances" / instance_id / "instance_result.json"
        if not path.exists():
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        attempts = (result.get("qaoa_attempts_by_track") or {}).get("qaoa") or []
        vectors = [
            canonicalize(a["optimal_parameters"], reps).tolist()
            for a in attempts
            if a.get("status") == "completed" and a.get("optimal_parameters")
        ]
        if vectors:
            per_instance[instance_id] = vectors
    if len(per_instance) < 2:
        raise ValueError(
            f"[pipeline.hybrid.transfer] need >= 2 source instances with QAOA parameters, got "
            f"{len(per_instance)}. Run the full qaoa track on {source_set!r} first."
        )
    pooled = np.median(
        np.vstack([v for vs in per_instance.values() for v in vs]), axis=0
    )
    leave_one_out = {
        iid: np.median(
            np.vstack(
                [v for other, vs in per_instance.items() if other != iid for v in vs]
            ),
            axis=0,
        ).tolist()
        for iid in per_instance
    }
    spread = np.std(np.vstack([v for vs in per_instance.values() for v in vs]), axis=0)
    return {
        "source_set": source_set,
        "reps": reps,
        "parameter_order": "qiskit optimal_point order: [beta_0..beta_{p-1}, gamma_0..gamma_{p-1}]",
        "rule": "canonicalize (gamma_0>=0, beta in (-pi/2, pi/2]) then per-parameter median; "
        "source instances get leave-one-out medians",
        "source_seed_counts": {iid: len(vs) for iid, vs in per_instance.items()},
        "pooled": pooled.tolist(),
        "pooled_std": spread.tolist(),
        "leave_one_out": leave_one_out,
    }


def parameters_for_manifest(
    transfer: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, list[float]]:
    same_set = manifest.get("set") == transfer["source_set"]
    mapping: dict[str, list[float]] = {}
    for item in manifest["instances"]:
        instance_id = item["instance_id"]
        if same_set:
            if instance_id in transfer["leave_one_out"]:
                mapping[instance_id] = list(transfer["leave_one_out"][instance_id])
        else:
            mapping[instance_id] = list(transfer["pooled"])
    return mapping
