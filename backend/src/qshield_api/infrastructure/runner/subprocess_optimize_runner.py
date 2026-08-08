# Đỗ Ngọc Tân - SubprocessOptimizeRunner — gọi `qshield-quantum workflow --exact-only`.
"""Cô lập mỗi job dưới `artifacts/runs/job_<id>/`, snapshot handoff Risk từ packages, rồi subprocess
CLI quantum (tránh qiskit+pyarrow chung process với FastAPI).

Mặc định `--exact-only`: QAOA 20-qubit trên StatevectorSampler không hoàn tất trong budget demo;
artifact ghi `actual_solver=exact` trung thực (CLAUDE.md quy tắc 18).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from qshield_contracts.config import Config
from qshield_contracts.enums import Stage
from qshield_contracts.paths import ArtifactPaths

from qshield_api.config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_PROFILE_PATH,
)
from qshield_api.domain.optimize.entities import OptimizeResult

_RISK_WORKFLOW_FILES = (
    "candidate_top10.csv",
    "qubo_objective_samples.parquet",
    "risk_summary.json",
    "candidate_order.json",
)
_OPTIONAL_TRUE_BENCHMARK = "true_benchmark.json"
_SUBPROCESS_TIMEOUT_SECONDS = 600


class OptimizeRunFailedError(RuntimeError):
    """`qshield-quantum workflow` thoát khác 0."""


class OptimizeInputMissingError(RuntimeError):
    """Thiếu handoff Risk do packages sinh — chạy prepare-workflow trước."""


@dataclass(frozen=True)
class SubprocessOptimizeRunner:
    cfg: Config

    def run(self, job_id: str) -> OptimizeResult:
        source_paths = ArtifactPaths(self.cfg, run_id=None)
        run_id = f"job_{job_id}"

        job_cfg = dict(self.cfg)
        job_cfg["artifacts"] = {**dict(self.cfg.get("artifacts", {})), "mode": "runs"}
        job_cfg["run_id"] = run_id
        job_paths = ArtifactPaths(job_cfg, run_id=run_id)

        self._snapshot_inputs(source_paths, job_paths)

        job_paths.run_root.mkdir(parents=True, exist_ok=True)
        override_path = job_paths.run_root / "_optimize_job_override.yaml"
        override_path.write_text(
            yaml.safe_dump(
                {
                    "artifacts": {"mode": "runs"},
                    "run_id": run_id,
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from qshield_quantum.cli import app; app()",
                "workflow",
                "--config",
                str(Path(DEFAULT_CONFIG_PATH).resolve()),
                "--profile",
                str(Path(DEFAULT_PROFILE_PATH).resolve()),
                "--override",
                str(override_path),
                "--exact-only",
                "--no-warm-start",
            ],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SECONDS,
            check=False,
            cwd=str(Path.cwd()),
        )
        if result.returncode != 0:
            raise OptimizeRunFailedError(
                f"qshield-quantum workflow (job={job_id}) exit={result.returncode}: "
                f"{result.stderr[-2000:]}"
            )

        bench_path = job_paths.stage_dir(Stage.SOLVE) / "workflow_benchmark.json"
        if not bench_path.exists():
            raise OptimizeRunFailedError(
                f"Missing {bench_path} after workflow job={job_id}."
            )
        payload = json.loads(bench_path.read_text(encoding="utf-8"))
        true_before, true_after = self._optional_true_cvar(source_paths)
        return _payload_to_result(
            payload, true_before=true_before, true_after=true_after
        )

    @staticmethod
    def _snapshot_inputs(source_paths: ArtifactPaths, job_paths: ArtifactPaths) -> None:
        risk_src = source_paths.stage_dir(Stage.RISK)
        missing = [
            risk_src / name
            for name in _RISK_WORKFLOW_FILES
            if not (risk_src / name).exists()
        ]
        if missing:
            raise OptimizeInputMissingError(
                f"Thiếu Risk handoff: {[str(p) for p in missing]} — chạy "
                "`qshield-risk prepare-workflow` (packages) trước."
            )
        risk_dst = job_paths.stage_dir(Stage.RISK)
        risk_dst.mkdir(parents=True, exist_ok=True)
        for name in _RISK_WORKFLOW_FILES:
            shutil.copy2(risk_src / name, risk_dst / name)

    @staticmethod
    def _optional_true_cvar(
        source_paths: ArtifactPaths,
    ) -> tuple[float | None, float | None]:
        path = source_paths.stage_dir(Stage.RISK) / _OPTIONAL_TRUE_BENCHMARK
        if not path.exists():
            return None, None
        payload = json.loads(path.read_text(encoding="utf-8"))
        baseline = payload.get("baseline") or {}
        before = baseline.get("true_cvar")
        solvers = payload.get("solvers") or {}
        # Prefer actual_solver row, else exact.
        actual = str(payload.get("actual_solver") or "exact")
        row = solvers.get(actual) or solvers.get("exact") or {}
        after = row.get("true_cvar")
        return (
            None if before is None else float(before),
            None if after is None else float(after),
        )


def _payload_to_result(
    payload: dict,
    *,
    true_before: float | None,
    true_after: float | None,
) -> OptimizeResult:
    exact_bits = str(
        payload.get("exact_best_bitstring") or payload.get("winning_bitstring") or ""
    )
    exact_energy = float(
        payload.get("exact_best_energy")
        if payload.get("exact_best_energy") is not None
        else payload.get("winning_energy") or 0.0
    )
    runtime = payload.get("runtime_seconds") or {}
    if isinstance(runtime, dict) and runtime:
        runtime_seconds = float(sum(float(v) for v in runtime.values()))
    else:
        timings = payload.get("stage_timings_seconds") or {}
        runtime_seconds = float(timings.get("total") or 0.0)

    qaoa_cfg = payload.get("qaoa_config") or {}
    manifest = payload.get("solver_manifest") or {}
    return OptimizeResult(
        bitstring=str(payload.get("winning_bitstring") or exact_bits),
        requested_solver=str(payload.get("requested_solver") or "qaoa"),
        actual_solver=str(payload.get("actual_solver") or "exact"),
        exact_energy=exact_energy,
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
        runtime_seconds=runtime_seconds,
        shots=(
            None
            if qaoa_cfg.get("shots") is None and manifest.get("shots") is None
            else int(qaoa_cfg.get("shots") or manifest.get("shots"))
        ),
        backend=str(manifest.get("backend") or "StatevectorSampler"),
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
        true_cvar_before=true_before,
        true_cvar_after=true_after,
        source_artifact="workflow_benchmark.json",
    )
