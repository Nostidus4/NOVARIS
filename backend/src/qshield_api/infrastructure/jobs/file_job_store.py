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
        "k_actions": result.k_actions,
        "chosen_actions": result.chosen_actions,
        "requested_solver": result.requested_solver,
        "actual_solver": result.actual_solver,
        "exact_energy": result.exact_energy,
        "qaoa_energy_by_seed": result.qaoa_energy_by_seed,
        "optimality_gap": result.optimality_gap,
        "feasibility_rate": result.feasibility_rate,
        "true_cvar_before": result.true_cvar_before,
        "true_cvar_after": result.true_cvar_after,
        "shots": result.shots,
        "backend": result.backend,
        "runtime_seconds": result.runtime_seconds,
    }


def _result_from_dict(payload: dict[str, Any]) -> OptimizeResult:
    return OptimizeResult(
        bitstring=payload["bitstring"],
        k_actions=payload["k_actions"],
        chosen_actions=payload["chosen_actions"],
        requested_solver=payload["requested_solver"],
        actual_solver=payload["actual_solver"],
        exact_energy=payload["exact_energy"],
        qaoa_energy_by_seed=payload["qaoa_energy_by_seed"],
        optimality_gap=payload["optimality_gap"],
        feasibility_rate=payload["feasibility_rate"],
        true_cvar_before=payload["true_cvar_before"],
        true_cvar_after=payload["true_cvar_after"],
        shots=payload["shots"],
        backend=payload["backend"],
        runtime_seconds=payload["runtime_seconds"],
    )
