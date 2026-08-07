# Đỗ Ngọc Tân - SubprocessOptimizeRunner — implement OptimizeRunner, BẮT BUỘC qua subprocess.
"""Xem docs/architecture/backend_hexagonal_design.md §3-4 cho lý do bắt buộc subprocess và thiết
kế cô lập output theo job.

Tinh chỉnh so với thiết kế gốc (phát hiện khi viết code thật, không có trong doc thiết kế ban đầu):
ép `artifacts.mode=runs` + `run_id=f"job_{job_id}"` cô lập đúng thư mục OUTPUT
(`artifacts/runs/job_<id>/outputs/optimization/`), nhưng đồng thời cũng đổi luôn thư mục INPUT mà
`qshield-quantum solve` đi tìm `action_effects.csv`/`pairwise_effects.csv`/`baseline_risk.json`
(risk) và `stress_scenarios.npz`/`scenario_manifest.json` (scenarios) — hai thư mục đó KHÔNG tồn
tại trong không gian `job_<id>` mới toanh. Phải COPY 5 file input đó từ vị trí thật (theo
`artifacts.mode` gốc trong config, thường `dev`) sang không gian riêng của job trước khi chạy
subprocess. Tác dụng phụ tốt: mỗi job tự chụp lại đúng input đã dùng, không bị ảnh hưởng nếu ai đó
chạy lại `qshield-risk effects` trong lúc job đang chờ.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass

import yaml
from qshield_contracts.config import Config
from qshield_contracts.enums import Stage
from qshield_contracts.paths import ArtifactPaths

from qshield_api.domain.optimize.entities import OptimizeResult

_RISK_FILES = ("action_effects.csv", "pairwise_effects.csv", "baseline_risk.json")
_SCENARIO_FILES = ("stress_scenarios.npz", "scenario_manifest.json")
_SUBPROCESS_TIMEOUT_SECONDS = 180


class OptimizeRunFailedError(RuntimeError):
    """`qshield-quantum solve` thoát với exit code khác 0 — kèm stderr để dễ tra."""


class OptimizeInputMissingError(RuntimeError):
    """Chưa có đủ `action_effects.csv`/`pairwise_effects.csv`/`baseline_risk.json`/scenario cube —
    chạy `qshield-risk effects` + `qshield-ai scenarios` trước khi gọi `POST /optimize/jobs`."""


@dataclass(frozen=True)
class SubprocessOptimizeRunner:
    cfg: Config

    def run(self, job_id: str) -> OptimizeResult:
        source_paths = ArtifactPaths(self.cfg, run_id=None)

        run_id = f"job_{job_id}"
        job_cfg = dict(self.cfg)
        job_cfg["artifacts"] = {**dict(self.cfg.get("artifacts", {})), "mode": "runs"}
        job_cfg["run_id"] = (
            run_id  # `qshield_quantum.cli._resolve_run_id` đọc khoá này trước
        )
        job_paths = ArtifactPaths(job_cfg, run_id=run_id)

        self._snapshot_inputs(source_paths, job_paths)

        job_paths.run_root.mkdir(parents=True, exist_ok=True)
        resolved_config_path = job_paths.run_root / "_optimize_job_resolved_config.yaml"
        resolved_config_path.write_text(
            yaml.safe_dump(job_cfg, allow_unicode=True), encoding="utf-8"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from qshield_quantum.cli import app; app()",
                "solve",
                "--config",
                str(resolved_config_path),
            ],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SECONDS,
            check=False,
        )
        if result.returncode != 0:
            raise OptimizeRunFailedError(
                f"qshield-quantum solve (job={job_id}) thoát với exit code "
                f"{result.returncode}: {result.stderr[-2000:]}"
            )

        result_path = job_paths.stage_dir(Stage.SOLVE) / "qaoa_result.json"
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        return _payload_to_result(payload)

    @staticmethod
    def _snapshot_inputs(source_paths: ArtifactPaths, job_paths: ArtifactPaths) -> None:
        risk_src = source_paths.stage_dir(Stage.RISK)
        scenarios_src = source_paths.stage_dir(Stage.SCENARIOS)
        missing = [
            risk_src / name for name in _RISK_FILES if not (risk_src / name).exists()
        ] + [
            scenarios_src / name
            for name in _SCENARIO_FILES
            if not (scenarios_src / name).exists()
        ]
        if missing:
            raise OptimizeInputMissingError(
                f"Thiếu input: {[str(p) for p in missing]} — chạy `qshield-risk effects` và "
                "`qshield-ai scenarios` trước."
            )

        risk_dst = job_paths.stage_dir(Stage.RISK)
        scenarios_dst = job_paths.stage_dir(Stage.SCENARIOS)
        risk_dst.mkdir(parents=True, exist_ok=True)
        scenarios_dst.mkdir(parents=True, exist_ok=True)
        for name in _RISK_FILES:
            shutil.copy2(risk_src / name, risk_dst / name)
        for name in _SCENARIO_FILES:
            shutil.copy2(scenarios_src / name, scenarios_dst / name)


def _payload_to_result(payload: dict) -> OptimizeResult:
    return OptimizeResult(
        bitstring=payload["bitstring"],
        k_actions=payload["k_actions"],
        chosen_actions=payload["chosen_actions"],
        requested_solver=payload["requested_solver"],
        actual_solver=payload["actual_solver"],
        exact_energy=payload["exact_energy"],
        qaoa_energy_by_seed={
            str(k): v for k, v in payload["qaoa_energy_by_seed"].items()
        },
        optimality_gap=payload["optimality_gap"],
        feasibility_rate=payload["feasibility_rate"],
        true_cvar_before=payload["true_cvar_before"],
        true_cvar_after=payload["true_cvar_after"],
        shots=payload["shots"],
        backend=payload["backend"],
        runtime_seconds=payload["runtime_seconds"],
    )
