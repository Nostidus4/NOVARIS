# Đỗ Ngọc Tân - CLI `uv run qshield-quantum solve` → artifacts/.../optimization/.
"""CLI `qshield-quantum` — nơi DUY NHẤT trong `packages/quantum` chạm vào đĩa.

Dựng QUBO từ `g/C/c` (thật hoặc `--mock` qua `fixtures.py`), chạy `verify/consistency` (BẮT BUỘC
trước QAOA — CLAUDE.md quy tắc 15), `exact`, `QAOA` (≥10 seed), `benchmark`, rồi chấm lại bằng true
CVaR qua `qshield_risk.evaluate()` (CLAUDE.md quy tắc 17). Cross-import `qshield_risk` là ngoại lệ
DUY NHẤT được phép trong chiều phụ thuộc một chiều (CLAUDE.md quy tắc 11: `risk ← quantum`).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import typer
from qshield_contracts.config import Config
from qshield_contracts.enums import ArtifactMode, SolverKind, Stage
from qshield_contracts.paths import ArtifactPaths
from qshield_contracts.runs import RunContext
from qshield_contracts.schemas.downstream import (
    ArtifactProvenance,
    BenchmarkReport,
    SolverManifest,
    validate_benchmark_report,
    validate_candidate_top10,
    validate_objective_samples,
)
from qshield_contracts.schemas.optimization import QaoaResult, validate_qaoa_result
from qshield_contracts.schemas.risk import ActionEffectsSchema, PairwiseEffectsSchema
from qshield_contracts.validate import validate_or_raise
from qshield_risk.evaluate import evaluate as risk_evaluate
from qshield_risk.metrics import alpha_key as risk_alpha_key

from qshield_quantum import fixtures
from qshield_quantum.benchmark import build_benchmark
from qshield_quantum.formulation.penalty import suggest_penalty
from qshield_quantum.formulation.qiskit_program import build_quadratic_program
from qshield_quantum.formulation.qubo import build_qubo
from qshield_quantum.io import action_effects_to_arrays, pairwise_to_matrix
from qshield_quantum.solvers.exact import solve_exact
from qshield_quantum.solvers.qaoa import solve_qaoa
from qshield_quantum.verify.consistency import verify_consistency
from qshield_quantum.workflow import (
    exact_result_payload,
    qaoa_result_payload,
    run_four_level_workflow,
    validate_four_level_profile,
)


def _fast_exit_if_standalone() -> None:
    """⚠️ **Bẫy kỹ thuật đã verify** (qua `sample <pid>` — không phải suy đoán): sau khi chạy nhiều
    seed QAOA, `Py_FinalizeEx` (dọn dẹp interpreter lúc thoát bình thường) có thể treo VÔ HẠN bên
    trong Rust `drop_glue` của `qiskit_circuit::CircuitData` (`_accelerate.abi3.so`, qiskit 2.5.1).
    Không phải bug của package này — `gc.disable()` quanh vòng lặp seed (`solvers/qaoa.py`) giảm
    tần suất nhưng KHÔNG loại bỏ hoàn toàn; `os._exit()` là cách duy nhất verify được là tránh
    treo tuyệt đối, vì nó bỏ qua toàn bộ finalization (mọi ghi file đã xong trước khi gọi hàm này
    nên không mất dữ liệu).

    CHỈ gọi khi chạy CLI thật (`uv run qshield-quantum solve`) — khi test gọi qua
    `typer.testing.CliRunner` trong CÙNG tiến trình pytest, `os._exit()` sẽ giết luôn pytest, nên
    phải chừa lại bằng biến môi trường `PYTEST_CURRENT_TEST` (pytest tự set trong suốt mỗi test).

    `packages/pipeline` gọi lệnh này qua SUBPROCESS riêng (`qshield_pipeline/run.py`), không import
    trực tiếp — nên `os._exit()` ở đây chỉ kết thúc đúng tiến trình con đó, không ảnh hưởng tiến
    trình `qshield-pipeline all` phía trên (xem `run.py` để biết lý do bắt buộc phải subprocess:
    qiskit + pyarrow ghi parquet cùng một tiến trình sẽ segfault, đã verify bằng `faulthandler`).
    """
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


def _tolerate_legacy_console_encoding() -> None:
    """Console cp1252 (Windows Git Bash/cmd.exe cũ) không mã hóa được tiếng Việt có dấu — copy từ
    `qshield_ai/cli.py`, xem `docs/perf/2026-08-04-pipeline-timing.md` §8."""
    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", None)
        if encoding and encoding.lower() != "utf-8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


app = typer.Typer(help="Q-SHIELD Quantum solver CLI.")


@app.callback()
def _main() -> None:
    """Giữ `solve` là subcommand thật — app chỉ có 1 lệnh nên Typer sẽ tự gộp thành root command
    nếu thiếu callback này (bug đã đo ở `docs/perf/2026-08-04-pipeline-timing.md` §5, cùng loại lỗi
    với `qshield-pipeline all`)."""
    _tolerate_legacy_console_encoding()


_CONFIG_OPTION = typer.Option("configs/base.yaml", "--config", help="Đường dẫn config")
_MOCK_OPTION = typer.Option(
    False, "--mock", help="Sinh g/C/c giả từ fixtures.py thay vì đọc packages/risk thật"
)


def _resolve_run_id(config: Config) -> str | None:
    """Nếu config có khóa `run_id` (tiêm bởi `packages/pipeline` khi chạy cả chuỗi — xem
    `qshield_pipeline/run_context.py`), dùng nguyên giá trị đó thay vì tự sinh, để chia sẻ đúng
    một run_id với các chặng khác (docs/perf/2026-08-04-pipeline-timing.md §6)."""
    if config.get("run_id"):
        return str(config["run_id"])
    mode = ArtifactMode(str(config.get("artifacts", {}).get("mode", "dev")))
    if mode == ArtifactMode.DEV:
        return None
    return f"run_{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}"


def _solver_package_versions() -> dict[str, str]:
    """Record package versions that travel with GATE-08 BenchmarkReport."""
    versions: dict[str, str] = {"python": sys.version.split()[0]}
    for name in ("qiskit", "qiskit_algorithms", "qiskit_optimization", "numpy"):
        try:
            module = __import__(name)
            versions[name] = str(getattr(module, "__version__", "unknown"))
        except Exception:  # noqa: BLE001 — optional deps must not block artifact write
            versions[name] = "unavailable"
    return versions


def _validate_workflow_benchmark_report(payload: dict) -> None:
    """Fail fast if workflow_benchmark.json cannot satisfy BenchmarkReport contract."""
    manifest_raw = dict(payload.get("solver_manifest") or {})
    package_versions = dict(manifest_raw.get("package_versions") or {})
    if not package_versions:
        package_versions = _solver_package_versions()
    manifest = SolverManifest(
        shots=int(manifest_raw.get("shots") or 1),
        registered_seeds=[
            int(seed) for seed in (manifest_raw.get("registered_seeds") or [0])
        ],
        reps=int(manifest_raw.get("reps") or 1),
        optimizer=str(manifest_raw.get("optimizer") or "COBYLA"),
        maxiter=int(manifest_raw.get("maxiter") or 1),
        backend=str(manifest_raw.get("backend") or "StatevectorSampler"),
        package_versions=package_versions,
        warm_start=bool(manifest_raw.get("warm_start", False)),
        seed_status={
            str(k): str(v)
            for k, v in dict(manifest_raw.get("seed_status") or {}).items()
        },
        NON_FINAL_CONFIG=bool(manifest_raw.get("NON_FINAL_CONFIG", False)),
    )
    provenance = ArtifactProvenance(
        run_id=str(payload.get("run_id") or "dev"),
        profile_id=str(payload.get("profile_id") or ""),
        profile_status=str(payload.get("profile_status") or ""),
        config_version=str(payload.get("config_version") or ""),
        config_hash=str(payload.get("config_hash") or ""),
    )
    qaoa_energy = payload.get("winning_energy")
    if (
        payload.get("qaoa_seed_count") in (0, None)
        and payload.get("actual_solver") != "qaoa"
    ):
        qaoa_energy = None
    report = BenchmarkReport(
        provenance=provenance,
        qubo_hash=str(payload.get("qubo_hash") or ""),
        candidate_order_hash=str(payload.get("candidate_order_hash") or ""),
        solver_manifest=manifest,
        requested_solver=str(payload.get("requested_solver") or "qaoa"),
        actual_solver=str(payload.get("actual_solver") or "exact"),
        exact_best_energy=float(payload.get("exact_best_energy") or 0.0),
        qaoa_best_energy=None if qaoa_energy is None else float(qaoa_energy),
        classical_best_energy=(
            None
            if payload.get("classical_energy") is None
            else float(payload["classical_energy"])
        ),
        success_prob=(
            None
            if payload.get("success_prob") is None
            else float(payload["success_prob"])
        ),
        feasible_rate=(
            None
            if payload.get("feasible_rate") is None
            else float(payload["feasible_rate"])
        ),
        optimality_gap=(
            None
            if payload.get("optimality_gap") is None
            else float(payload["optimality_gap"])
        ),
        energy_stats=dict(payload.get("energy_stats") or {}),
        runtime_seconds={
            str(k): float(v)
            for k, v in dict(payload.get("runtime_seconds") or {}).items()
        },
        peak_memory_mb=(
            None
            if payload.get("peak_memory_mb") is None
            else float(payload["peak_memory_mb"])
        ),
        reference_hardware=dict(payload.get("reference_hardware") or {}),
        fallback_reason=(
            None
            if payload.get("fallback_reason") is None
            else str(payload["fallback_reason"])
        ),
        caveats=[str(payload["caveat"])] if payload.get("caveat") else [],
    )
    validate_benchmark_report(report)


def _tickers(config: Config) -> list[str]:
    return [entry["ticker"] for entry in config["tickers"]]


def _load_scenario_cube(paths: ArtifactPaths, tickers: list[str]) -> np.ndarray:
    """Đọc lại scenario cube thật để chấm true CVaR (quy tắc 17) — validate ĐỘC LẬP với
    `packages/risk` (CLAUDE.md quy tắc 12: validate ở mọi ranh giới module, không tin ngầm dữ liệu
    chặng trước dù cùng đã PASS ở đó)."""
    manifest_path = paths.for_stage(Stage.SCENARIOS, "scenario_manifest.json")
    cube_path = paths.for_stage(Stage.SCENARIOS, "stress_scenarios.npz")
    if not manifest_path.exists() or not cube_path.exists():
        raise typer.BadParameter(
            f"Chưa có {manifest_path} / {cube_path} — chạy `qshield-ai scenarios` trước."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("gate_status") != "PASS":
        raise typer.BadParameter(
            f"{manifest_path}: gate_status={manifest.get('gate_status')!r}; cần PASS để dùng làm "
            "true CVaR."
        )
    manifest_tickers = list(manifest.get("ticker_order", []))
    if manifest_tickers != tickers:
        raise typer.BadParameter(
            f"{manifest_path}: ticker_order={manifest_tickers} không khớp configs "
            f"tickers={tickers}."
        )
    with np.load(cube_path, allow_pickle=False) as data:
        if "scenarios" not in data.files:
            raise typer.BadParameter(f"{cube_path}: thiếu key 'scenarios'.")
        cube = np.asarray(data["scenarios"], dtype=float)
    expected_shape = (
        int(manifest["num_scenarios"]),
        int(manifest["horizon_days"]),
        len(tickers),
    )
    if cube.shape != expected_shape:
        raise typer.BadParameter(
            f"{cube_path}: shape={cube.shape}; expected {expected_shape} (theo chính manifest)."
        )
    return cube


def _resolved_penalty(cfg: Config, g, C, c) -> tuple[float, float, float, bool]:
    """Đọc `lambda_1`/`lambda_2`/`P` từ config; nếu `null` (TBD-006, chưa Phúc/Ngọc duyệt) thì tự
    suy ra PROVISIONAL bằng `suggest_penalty` — không phải số đoán mò, xem `plan.md` câu hỏi 3.
    Trả thêm cờ `is_provisional` để ghi rõ vào log/metrics — không âm thầm dùng số tạm."""
    penalty_cfg = cfg.get("penalty", {}) or {}
    lambda_1 = penalty_cfg.get("lambda_1")
    lambda_2 = penalty_cfg.get("lambda_2")
    p = penalty_cfg.get("P")
    is_provisional = lambda_1 is None or lambda_2 is None or p is None
    lambda_1 = 1.0 if lambda_1 is None else float(lambda_1)
    lambda_2 = 1.0 if lambda_2 is None else float(lambda_2)
    p = (
        suggest_penalty(g, C, c, lambda_1=lambda_1, lambda_2=lambda_2)
        if p is None
        else float(p)
    )
    return lambda_1, lambda_2, p, is_provisional


@app.command("workflow")
def solve_workflow(
    config: str = _CONFIG_OPTION,
    profile: str = typer.Option(
        "configs/workflow_update.yaml",
        "--profile",
        help="Profile declaring top10_four_level_actions",
    ),
    override: str | None = typer.Option(
        None,
        "--override",
        help="Optional YAML deep-merged after profile",
    ),
    no_warm_start: bool = typer.Option(
        False, "--no-warm-start", help="Disable Qiskit warm-start even when installed"
    ),
    exact_only: bool = typer.Option(
        False,
        "--exact-only",
        help="NON_FINAL fallback: run surrogate/verify/exact/classical and skip QAOA",
    ),
) -> None:
    """Consume the workflow risk handoff and emit model/exact/QAOA candidate artifacts."""
    cfg = Config.load_profiled(
        Path(config), Path(profile), Path(override) if override else None
    )
    quantum = validate_four_level_profile(cfg)
    paths = ArtifactPaths(cfg, run_id=_resolve_run_id(cfg))
    context = RunContext(cfg, paths)
    logger = context.logger("quantum_workflow")
    paths.ensure(Stage.QUBO)

    candidate_path = paths.for_stage(Stage.RISK, "candidate_top10.csv")
    samples_path = paths.for_stage(Stage.RISK, "qubo_objective_samples.parquet")
    summary_path = paths.for_stage(Stage.RISK, "risk_summary.json")
    missing = [
        path
        for path in (candidate_path, samples_path, summary_path)
        if not path.exists()
    ]
    if missing:
        raise typer.BadParameter(
            f"Missing workflow risk handoff files: {[str(path) for path in missing]}."
        )
    candidates = pd.read_csv(candidate_path)
    samples = pd.read_parquet(samples_path)
    risk_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    profile_id = str((cfg.get("profile", {}) or {}).get("id", ""))
    handoff_profiles = set(candidates["profile_id"].astype(str))
    if handoff_profiles != {profile_id} or risk_summary.get("profile_id") != profile_id:
        raise typer.BadParameter(
            "Risk handoff profile_id does not match the resolved Quantum profile."
        )

    qaoa_cfg = dict(quantum.get("qaoa", {}) or {})
    non_final = bool(qaoa_cfg.get("NON_FINAL_CONFIG"))
    dev_mode = dict(qaoa_cfg.get("dev_mode") or {})
    if non_final and bool(dev_mode.get("enabled")):
        configured_seeds = list(
            dev_mode.get("reduced_seeds") or qaoa_cfg.get("seeds") or []
        )
        shots = int(dev_mode.get("reduced_shots", qaoa_cfg.get("shots", 1024)))
        maxiter = int(
            dev_mode.get("reduced_maxiter", qaoa_cfg.get("optimizer_maxiter", 200))
        )
        minimum_seeds = max(1, len(configured_seeds))
        if bool(dev_mode.get("disable_warm_start")):
            no_warm_start = True
    else:
        minimum_seeds = max(10, int(qaoa_cfg.get("min_seeds", 10)))
        configured_seeds = qaoa_cfg.get("seeds")
        shots = int(qaoa_cfg.get("shots", 1024))
        maxiter = int(qaoa_cfg.get("optimizer_maxiter", 200))
    seed_base = int(cfg.get("seed") or 0)
    seeds = (
        [int(seed) for seed in configured_seeds]
        if configured_seeds
        else [seed_base + offset for offset in range(minimum_seeds)]
    )
    if len(seeds) < minimum_seeds:
        raise typer.BadParameter(
            f"Workflow QAOA requires at least {minimum_seeds} seeds, got {len(seeds)}."
        )
    # Align quantum.input_candidates with handoff when Risk selected a different M.
    if "selected_top10" in candidates.columns:
        selected_mask = candidates["selected_top10"].astype(str).str.lower().isin(
            {"true", "1", "yes"}
        ) | (candidates["selected_top10"] == True)
        selected_count = int(selected_mask.sum())
    else:
        selected_count = len(candidates)
    quantum = dict(quantum)
    quantum["input_candidates"] = selected_count
    bit_encoding = dict(quantum.get("bit_encoding") or {})
    bit_encoding["asset_count"] = selected_count
    bit_encoding["total_decision_bits"] = 2 * selected_count
    bit_encoding["exact_reference_states"] = 2 ** (2 * selected_count)
    quantum["bit_encoding"] = bit_encoding
    cfg["quantum"] = quantum
    runtime_bits = 2 * selected_count
    validate_candidate_top10(candidates, expected_candidates=selected_count)
    validate_objective_samples(samples, expected_bit_count=runtime_bits)
    logger.info(
        "Four-level workflow: %d candidates, %d bits, %d QAOA seeds "
        "(shots=%d, maxiter=%d, NON_FINAL_CONFIG=%s).",
        selected_count,
        runtime_bits,
        len(seeds),
        shots,
        maxiter,
        non_final,
    )
    performance_budget = dict(cfg.get("performance_budget") or {})
    result = run_four_level_workflow(
        candidates,
        samples,
        profile=cfg,
        risk_summary=risk_summary,
        seeds=seeds,
        shots=shots,
        maxiter=maxiter,
        candidate_pool_size=20,
        warm_start=not no_warm_start,
        logger=logger,
        verify_sample_size=4096 if non_final and runtime_bits >= 16 else None,
        run_qaoa=not exact_only,
        allow_non_final=non_final,
        performance_budget=performance_budget,
    )

    provenance = {
        "run_id": context.run_id or "dev",
        "profile_id": profile_id,
        "profile_status": str((cfg.get("profile", {}) or {}).get("status", "")),
        "config_version": str(
            (cfg.get("provenance") or {}).get("config_version", "provisional-v1")
        ),
        "config_hash": str(risk_summary.get("config_hash", "")),
        "candidate_order_hash": str(risk_summary.get("candidate_order_hash", "")),
    }
    model_payload = {
        **provenance,
        "mode": quantum["mode"],
        "candidate_order": list(result.candidate_order),
        "bit_encoding": {
            "bits_per_candidate": 2,
            "mapping": {"00": 0, "10": 10, "01": 20, "11": 30},
        },
        "target_column": result.target_column,
        **result.model.to_dict(),
    }
    # qubo_hash identifies the MODEL, not the run: `run_id` is excluded so two runs over the same
    # config/candidates/coefficients hash identically. TL-015/G1 needs that stability to prove
    # exact, QAOA and classical solved one QUBO — including across separate runs.
    model_hash_payload = json.dumps(
        {key: value for key, value in model_payload.items() if key != "run_id"},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    model_payload["qubo_hash"] = hashlib.sha256(
        model_hash_payload.encode("utf-8")
    ).hexdigest()
    actual_solver = str(result.benchmark.get("actual_solver", "qaoa"))
    fallback_reason = result.benchmark.get("fallback_reason")
    exact_payload = {
        **provenance,
        "qubo_hash": model_payload["qubo_hash"],
        **exact_result_payload(result.exact),
    }
    qaoa_payload = {
        **provenance,
        "qubo_hash": model_payload["qubo_hash"],
        "requested_solver": "qaoa",
        "actual_solver": actual_solver,
        "fallback_reason": fallback_reason,
        **qaoa_result_payload(result.qaoa_by_seed, result.candidate_pool),
    }
    seed_status = {
        str(seed): ("completed" if seed_result.feasible else "failed")
        for seed, seed_result in result.qaoa_by_seed.items()
    }
    for seed in seeds:
        seed_status.setdefault(str(seed), "timeout" if fallback_reason else "failed")
    package_versions = _solver_package_versions()
    solver_manifest = {
        "shots": shots,
        "registered_seeds": list(seeds),
        "reps": int(qaoa_cfg.get("p", 1)),
        "optimizer": str(qaoa_cfg.get("optimizer", "COBYLA")),
        "maxiter": maxiter,
        "backend": "StatevectorSampler",
        "package_versions": package_versions,
        "warm_start": not no_warm_start,
        "seed_status": seed_status,
        "NON_FINAL_CONFIG": non_final,
    }
    benchmark_payload = {
        **provenance,
        "qubo_hash": model_payload["qubo_hash"],
        "NON_FINAL_CONFIG": non_final,
        "qaoa_config": {
            "seeds": seeds,
            "shots": shots,
            "maxiter": maxiter,
            "warm_start": not no_warm_start,
        },
        "solver_manifest": solver_manifest,
        "reference_hardware": dict(performance_budget.get("reference_hardware") or {}),
        "stage_timings_seconds": result.stage_timings,
        **result.benchmark,
    }
    # Ensure requested/actual from benchmark win over any stale keys.
    benchmark_payload["requested_solver"] = str(
        result.benchmark.get("requested_solver", "qaoa")
    )
    benchmark_payload["actual_solver"] = actual_solver
    benchmark_payload["fallback_reason"] = fallback_reason
    _validate_workflow_benchmark_report(benchmark_payload)
    outputs = {
        "qubo_model.json": model_payload,
        "exact_solution.json": exact_payload,
        "qaoa_results.json": qaoa_payload,
        "workflow_benchmark.json": benchmark_payload,
    }
    for filename, payload in outputs.items():
        paths.for_stage(Stage.QUBO, filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    context.write_config_snapshot()
    context.write_metrics(
        {
            "stage": "quantum",
            "profile_id": model_payload["profile_id"],
            "gate_status": "PASS",
            "mode": quantum["mode"],
            "evaluated_states": result.exact.evaluated_states,
            "qaoa_seed_count": len(result.qaoa_by_seed),
            "candidate_pool_size": len(result.candidate_pool),
        }
    )
    typer.echo(
        f"[quantum/workflow] OK — {result.exact.evaluated_states} states, "
        f"{len(result.candidate_pool)} candidates → {paths.stage_dir(Stage.QUBO)}"
    )
    _fast_exit_if_standalone()


@app.command()
def solve(config: str = _CONFIG_OPTION, mock: bool = _MOCK_OPTION) -> None:
    """Dựng QUBO từ `action_effects.csv`/`pairwise_effects.csv`, chạy `verify/consistency` +
    `exact` + `QAOA` → `qaoa_result.json`."""
    cfg = Config.load(Path(config))
    paths = ArtifactPaths(cfg, run_id=_resolve_run_id(cfg))
    context = RunContext(cfg, paths)
    logger = context.logger("quantum")
    paths.ensure(Stage.QUBO)
    stage_dir = paths.stage_dir(Stage.QUBO)

    tickers = _tickers(cfg)
    k_actions = int(cfg["k_actions"])
    alpha = float(cfg["cvar_alpha"])

    if mock:
        action_effects_df, pairwise_effects_df, baseline = fixtures.generate_frames(
            tickers, seed=int(cfg.get("seed") or 0), alpha=alpha
        )
        logger.warning(
            "Chạy --mock: g/C/c là dữ liệu giả (fixtures.py), KHÔNG phải run baseline."
        )
    else:
        risk_dir = paths.stage_dir(Stage.RISK)
        action_effects_path = risk_dir / "action_effects.csv"
        pairwise_effects_path = risk_dir / "pairwise_effects.csv"
        baseline_path = risk_dir / "baseline_risk.json"
        missing = [
            p
            for p in (action_effects_path, pairwise_effects_path, baseline_path)
            if not p.exists()
        ]
        if missing:
            typer.echo(
                f"✗ Chưa có {missing} — packages/risk chưa chạy "
                "(`qshield-risk effects`). Dùng --mock để chạy thử với dữ liệu giả.",
                err=True,
            )
            raise typer.Exit(code=1)
        action_effects_df = validate_or_raise(
            pd.read_csv(action_effects_path),
            ActionEffectsSchema,
            context="qshield_quantum:input.action_effects",
        )
        pairwise_effects_df = validate_or_raise(
            pd.read_csv(pairwise_effects_path),
            PairwiseEffectsSchema,
            context="qshield_quantum:input.pairwise_effects",
        )
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    g, c = action_effects_to_arrays(action_effects_df, tickers)
    C = pairwise_to_matrix(pairwise_effects_df, tickers)

    lambda_1, lambda_2, penalty, penalty_is_provisional = _resolved_penalty(
        cfg, g, C, c
    )
    if penalty_is_provisional:
        logger.warning(
            "lambda_1=%.6f lambda_2=%.6f P=%.6f là PROVISIONAL (suggest_penalty, chưa Phúc/Ngọc "
            "duyệt — plan.md câu hỏi 3). Run này là NON_BASELINE_RUN.",
            lambda_1,
            lambda_2,
            penalty,
        )

    logger.info(
        "Chạy verify/consistency trước khi tin bất kỳ kết quả QAOA nào (quy tắc 15)..."
    )
    verify_consistency(
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
        ticker_order=tickers,
    )
    logger.info("verify/consistency PASS trên toàn bộ 256 bitstring.")

    exact_result = solve_exact(
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )
    logger.info(
        "Exact: best_feasible=%s energy=%.6f (duyệt %d trạng thái)",
        exact_result.best_feasible_bitstring,
        exact_result.best_feasible_energy,
        exact_result.evaluated_states,
    )

    Q, linear, constant = build_qubo(
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )
    qp = build_quadratic_program(Q, linear, constant, ticker_order=tickers)

    qaoa_cfg = cfg["qaoa"]
    seeds = qaoa_cfg.get("seeds")
    if not seeds:
        seeds = list(range(int(qaoa_cfg["min_seeds"])))
        logger.warning(
            "configs/base.yaml: qaoa.seeds chưa đăng ký — dùng tạm %s (PROVISIONAL, "
            "plan.md câu hỏi 4). Run này là NON_BASELINE_RUN.",
            seeds,
        )
    qaoa_by_seed = solve_qaoa(
        qp,
        seeds=seeds,
        shots=int(qaoa_cfg["shots"]),
        maxiter=int(qaoa_cfg["optimizer_maxiter"]),
        k_actions=k_actions,
        reference_bitstring=exact_result.best_feasible_bitstring,
    )
    logger.info("QAOA: chạy xong %d seed.", len(qaoa_by_seed))

    bench = build_benchmark(
        exact_result,
        qaoa_by_seed,
        g=g,
        C=C,
        c=c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )
    (stage_dir / "benchmark.json").write_text(
        json.dumps(bench, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    if not bench["qaoa_beats_classical"]:
        logger.warning(
            "QAOA KHÔNG thắng classical baseline (greedy theo g) — báo cáo trung thực theo "
            "CLAUDE.md quy tắc 18, không diễn giải có lợi cho QAOA."
        )

    winning_bitstring = bench["winning_bitstring"]
    actual_solver = SolverKind.QAOA
    if not bench["winning_is_feasible"]:
        winning_bitstring = exact_result.best_feasible_bitstring
        actual_solver = SolverKind.EXACT
        logger.warning(
            "Không seed QAOA nào trả bitstring feasible — fallback dùng nghiệm exact. "
            "actual_solver=exact (docs/runbook/troubleshooting.md §5)."
        )

    # CLAUDE.md quy tắc 17 — chấm lại bằng true CVaR, KHÔNG dùng objective value để chọn nghiệm.
    if mock or baseline is None:
        true_cvar_before = float("nan")
        true_cvar_after = float("nan")
        logger.warning(
            "Chạy --mock: không có scenario cube/baseline thật để chấm true CVaR — "
            "true_cvar_before/after = NaN, KHÔNG dùng làm bằng chứng baseline."
        )
    else:
        if not isinstance(baseline, dict):
            raise TypeError(
                "[quantum] non-mock baseline_risk.json must decode to a mapping."
            )
        scenario_cube = _load_scenario_cube(paths, tickers)
        bits = [int(b) for b in winning_bitstring]
        risk_eval = risk_evaluate(
            bits,
            scenario_cube,
            tickers,
            weights=baseline["portfolio_weights"],
            cash_weight=float(baseline["cash_weight"]),
            config=cfg,
        )
        primary_key = risk_alpha_key(alpha)
        true_cvar_before = risk_eval.before.cvar[primary_key]
        true_cvar_after = risk_eval.after.cvar[primary_key]
        logger.info(
            "True CVaR (qshield_risk.evaluate): before=%.6f after=%.6f (%s)",
            true_cvar_before,
            true_cvar_after,
            risk_eval.recommendation_status,
        )
        if risk_eval.constraint_violations:
            logger.warning(
                "qshield_risk.evaluate báo vi phạm ràng buộc: %s",
                risk_eval.constraint_violations,
            )
        if not risk_eval.improves_primary_cvar:
            logger.warning(
                "Nghiệm KHÔNG cải thiện true CVaR (before=%.6f, after=%.6f) — báo cáo trung thực "
                "theo CLAUDE.md quy tắc 18, không diễn giải có lợi.",
                true_cvar_before,
                true_cvar_after,
            )

    qaoa_result = QaoaResult(
        bitstring=winning_bitstring,
        k_actions=k_actions,
        chosen_actions=[i for i, b in enumerate(winning_bitstring) if b == "1"],
        requested_solver=SolverKind.QAOA,
        actual_solver=actual_solver,
        exact_energy=exact_result.best_feasible_energy,
        qaoa_energy_by_seed={seed: r.energy for seed, r in qaoa_by_seed.items()},
        optimality_gap=bench["optimality_gap"],
        feasibility_rate=bench["mean_feasibility_rate"],
        true_cvar_before=true_cvar_before,
        true_cvar_after=true_cvar_after,
        shots=int(qaoa_cfg["shots"]),
        backend=str(cfg.get("backend", "simulator")),
        runtime_seconds=bench["runtime_seconds_total"],
    )
    validate_qaoa_result(qaoa_result)

    out_path = stage_dir / "qaoa_result.json"
    out_path.write_text(
        json.dumps(
            {
                "bitstring": qaoa_result.bitstring,
                "k_actions": qaoa_result.k_actions,
                "chosen_actions": qaoa_result.chosen_actions,
                "requested_solver": str(qaoa_result.requested_solver),
                "actual_solver": str(qaoa_result.actual_solver),
                "exact_energy": qaoa_result.exact_energy,
                "qaoa_energy_by_seed": qaoa_result.qaoa_energy_by_seed,
                "optimality_gap": qaoa_result.optimality_gap,
                "feasibility_rate": qaoa_result.feasibility_rate,
                "true_cvar_before": qaoa_result.true_cvar_before,
                "true_cvar_after": qaoa_result.true_cvar_after,
                "shots": qaoa_result.shots,
                "backend": qaoa_result.backend,
                "runtime_seconds": qaoa_result.runtime_seconds,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    context.write_config_snapshot()
    context.write_metrics(
        {
            "stage": "quantum",
            "gate_status": "PASS",
            "winning_bitstring": winning_bitstring,
            "actual_solver": str(actual_solver),
            "optimality_gap": bench["optimality_gap"],
            "penalty_is_provisional": penalty_is_provisional,
        }
    )
    typer.echo(f"[quantum] OK — bitstring={winning_bitstring} → {out_path}")
    _fast_exit_if_standalone()


if __name__ == "__main__":
    app()
