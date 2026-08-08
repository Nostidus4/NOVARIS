# Đỗ Ngọc Tân - FileOptimizeJobRepository — implement OptimizeJobRepository, ghi file (không in-memory).
"""Thiết kế chi tiết: docs/architecture/backend_hexagonal_design.md §4.

Ghi `artifacts/jobs/{job_id}.json` — SIBLING với `artifacts/dev/`/`artifacts/runs/`, KHÔNG thuộc
`Stage` nào (job tracking là bookkeeping tầng API, không phải artifact khoa học/tài chính) — vì
vậy đọc `artifacts.root` trực tiếp từ config thay vì qua `ArtifactPaths.stage_dir()`.

Đánh đổi đã chọn: ghi file để sống sót qua restart backend (job có thể chạy 70+ giây). Dọn dẹp job
cũ theo NGÀY — CHƯA implement ở đây (xem §6.1 design doc, để sau: script tay hoặc Airflow DAG).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qshield_contracts.config import Config

from qshield_api.domain.optimize.entities import (
    OptimizeJob,
    OptimizeJobStatus,
    OptimizeResult,
)


@dataclass(frozen=True)
class FileOptimizeJobRepository:
    cfg: Config

    def _jobs_dir(self) -> Path:
        artifacts_root = Path(
            str(self.cfg.get("artifacts", {}).get("root", "artifacts"))
        )
        jobs_dir = artifacts_root / "jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        return jobs_dir

    def _path(self, job_id: str) -> Path:
        return self._jobs_dir() / f"{job_id}.json"

    def save(self, job: OptimizeJob) -> None:
        payload: dict[str, Any] = {
            "job_id": job.job_id,
            "status": str(job.status),
            "created_at": job.created_at.isoformat(),
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "error": job.error,
            "result": _result_to_dict(job.result) if job.result is not None else None,
        }
        self._path(job.job_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get(self, job_id: str) -> OptimizeJob | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return OptimizeJob(
            job_id=payload["job_id"],
            status=OptimizeJobStatus(payload["status"]),
            created_at=datetime.fromisoformat(payload["created_at"]),
            finished_at=(
                datetime.fromisoformat(payload["finished_at"])
                if payload["finished_at"]
                else None
            ),
            result=_result_from_dict(payload["result"]) if payload["result"] else None,
            error=payload["error"],
        )

    def list(self) -> list[OptimizeJob]:
        jobs = []
        for path in sorted(self._jobs_dir().glob("*.json")):
            job = self.get(path.stem)
            if job is not None:
                jobs.append(job)
        return jobs


def _result_to_dict(result: OptimizeResult) -> dict[str, Any]:
    return {
        "bitstring": result.bitstring,
        "requested_solver": result.requested_solver,
        "actual_solver": result.actual_solver,
        "exact_energy": result.exact_energy,
        "classical_energy": result.classical_energy,
        "optimality_gap": result.optimality_gap,
        "qaoa_beats_classical": result.qaoa_beats_classical,
        "runtime_seconds": result.runtime_seconds,
        "shots": result.shots,
        "backend": result.backend,
        "fallback_reason": result.fallback_reason,
        "profile_id": result.profile_id,
        "qubo_hash": result.qubo_hash,
        "true_cvar_before": result.true_cvar_before,
        "true_cvar_after": result.true_cvar_after,
        "source_artifact": result.source_artifact,
    }


def _result_from_dict(payload: dict[str, Any]) -> OptimizeResult:
    # Backward-compatible with older job JSON field shapes.
    if "source_artifact" not in payload and "k_actions" in payload:
        return OptimizeResult(
            bitstring=str(payload["bitstring"]),
            requested_solver=str(payload.get("requested_solver") or "qaoa"),
            actual_solver=str(payload.get("actual_solver") or "qaoa"),
            exact_energy=float(payload["exact_energy"]),
            classical_energy=None,
            optimality_gap=(
                None
                if payload.get("optimality_gap") is None
                else float(payload["optimality_gap"])
            ),
            qaoa_beats_classical=False,
            runtime_seconds=float(payload.get("runtime_seconds") or 0.0),
            shots=(None if payload.get("shots") is None else int(payload["shots"])),
            backend=str(payload.get("backend") or "StatevectorSampler"),
            fallback_reason=None,
            profile_id=None,
            qubo_hash=None,
            true_cvar_before=(
                None
                if payload.get("true_cvar_before") is None
                else float(payload["true_cvar_before"])
            ),
            true_cvar_after=(
                None
                if payload.get("true_cvar_after") is None
                else float(payload["true_cvar_after"])
            ),
            source_artifact="legacy_qaoa_result.json",
        )
    return OptimizeResult(
        bitstring=str(payload["bitstring"]),
        requested_solver=str(payload["requested_solver"]),
        actual_solver=str(payload["actual_solver"]),
        exact_energy=float(payload["exact_energy"]),
        classical_energy=(
            None
            if payload.get("classical_energy") is None
            else float(payload["classical_energy"])
        ),
        optimality_gap=(
            None
            if payload.get("optimality_gap") is None
            else float(payload["optimality_gap"])
        ),
        qaoa_beats_classical=bool(payload.get("qaoa_beats_classical", False)),
        runtime_seconds=float(payload["runtime_seconds"]),
        shots=None if payload.get("shots") is None else int(payload["shots"]),
        backend=str(payload["backend"]),
        fallback_reason=(
            None
            if payload.get("fallback_reason") is None
            else str(payload["fallback_reason"])
        ),
        profile_id=(
            None if payload.get("profile_id") is None else str(payload["profile_id"])
        ),
        qubo_hash=(
            None if payload.get("qubo_hash") is None else str(payload["qubo_hash"])
        ),
        true_cvar_before=(
            None
            if payload.get("true_cvar_before") is None
            else float(payload["true_cvar_before"])
        ),
        true_cvar_after=(
            None
            if payload.get("true_cvar_after") is None
            else float(payload["true_cvar_after"])
        ),
        source_artifact=str(payload["source_artifact"]),
    )
