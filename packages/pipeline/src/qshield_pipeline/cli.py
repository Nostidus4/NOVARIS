# Đỗ Ngọc Tân - CLI `uv run qshield-pipeline all` — một lệnh chạy toàn bộ pipeline.
"""CLI `qshield-pipeline all` — orchestrator end-to-end, xem `run.py` cho logic từng chặng (mỗi
chặng chạy trong một subprocess riêng — bắt buộc để tránh xung đột native library qiskit/pyarrow,
xem docstring `run.py`).

`@app.callback()` bắt buộc phải có: Typer gộp app chỉ-một-lệnh thành root command nếu thiếu, khiến
`qshield-pipeline all --config ...` thất bại với "no such option" — bug đã đo ở
`docs/perf/2026-08-04-pipeline-timing.md` §5 (cùng loại lỗi từng gặp ở `qshield-quantum solve`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from qshield_pipeline.run import (
    StageError,
    run_all,
    run_downstream,
    run_workflow_update,
)

app = typer.Typer(help="Q-SHIELD end-to-end pipeline CLI.")


def _tolerate_legacy_console_encoding() -> None:
    """Console cp1252 (Windows Git Bash/cmd.exe cũ) không mã hóa được tiếng Việt có dấu — copy từ
    `qshield_ai/cli.py`/`qshield_quantum/cli.py`, xem
    `docs/perf/2026-08-04-pipeline-timing.md` §8."""
    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", None)
        if encoding and encoding.lower() != "utf-8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


@app.callback()
def _main() -> None:
    """Giữ `all` là subcommand thật (bug đã đo ở §5, xem docstring module)."""
    _tolerate_legacy_console_encoding()


@app.command(name="all")
def run_all_command(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Đường dẫn config"
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Chạy trên dữ liệu giả từ qshield_contracts.mocks/fixtures — cho phép 5 người phát "
        "triển song song từ ngày 1",
    ),
) -> None:
    """Chạy tuần tự 5 bước: data → regime → scenarios → risk → optimize (qubo+solve gộp).

    Fail fast: dừng ngay tại chặng lỗi đầu tiên, in rõ tên chặng (xem `run.py`, `stages.py`).
    """
    try:
        run_id = run_all(Path(config), mock=mock)
    except StageError as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"[pipeline] OK — toàn bộ 5 chặng PASS (run_id={run_id or 'dev'}).")


@app.command(name="downstream")
def run_downstream_command(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Base config path"
    ),
    profile: str = typer.Option(
        "configs/workflow_update.yaml",
        "--profile",
        help="Product profile path",
    ),
    override: str | None = typer.Option(
        None,
        "--override",
        help="Optional extra YAML deep-merged after profile",
    ),
    mock: bool = typer.Option(
        False, "--mock", help="Use deterministic current eight-ticker scenario fixture"
    ),
) -> None:
    """Run Risk selection/sampling → generic Quantum → true rerank/local polishing."""
    try:
        run_id = run_downstream(
            Path(config),
            Path(profile),
            Path(override) if override else None,
            mock=mock,
        )
    except (StageError, ValueError) as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        "[pipeline/downstream] OK — NON_BASELINE_RUN 3 chặng PASS "
        f"(run_id={run_id or 'dev'})."
    )


@app.command(name="workflow-update")
def run_workflow_update_command(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Base config path"
    ),
    profile: str = typer.Option(
        "configs/workflow_update.yaml",
        "--profile",
        help="Product profile path",
    ),
    override: str | None = typer.Option(
        None,
        "--override",
        help="Optional extra YAML deep-merged after profile",
    ),
    run_data: bool = typer.Option(
        False,
        "--run-data",
        help="Also fetch/rebuild Data; default reuses the current 30-ticker Data artifacts",
    ),
    quantum_mode: str = typer.Option(
        "exact",
        "--quantum-mode",
        help="exact = safe fallback; qaoa = explicitly monitored NON_FINAL QAOA run",
    ),
) -> None:
    """Run Regime → Scenarios → Risk top-10 → Quantum → rerank/polish → true-benchmark."""
    try:
        run_id = run_workflow_update(
            Path(config),
            Path(profile),
            Path(override) if override else None,
            run_data=run_data,
            quantum_mode=quantum_mode,
        )
    except (StageError, ValueError) as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        "[pipeline/workflow-update] OK — NON_BASELINE_RUN "
        f"(run_id={run_id or 'dev'}, quantum_mode={quantum_mode})."
    )


_EXPERIMENT_OPTION = typer.Option(
    "configs/experiments/hybrid_v1.yaml",
    "--experiment",
    help="Experiment preregistration YAML (deep-merged as override)",
)
_SET_OPTION = typer.Option("exploratory", "--set", help="exploratory | confirmation")
_INSTANCE_OPTION = typer.Option(None, "--instance", help="Run these instance ids only")


def _hybrid_context(config: str, profile: str, experiment: str):
    from qshield_contracts.config import Config
    from qshield_contracts.paths import ArtifactPaths
    from qshield_contracts.runs import RunContext

    from qshield_pipeline.hybrid.settings import HybridSettings

    cfg = Config.load_profiled(Path(config), Path(profile), Path(experiment))
    settings = HybridSettings.from_config(cfg)
    paths = ArtifactPaths(cfg, run_id=settings.experiment_id)
    return cfg, settings, paths, RunContext(cfg, paths)


def _manifest_path(paths, settings, set_name: str) -> Path:
    from qshield_contracts.enums import Stage

    return paths.for_stage(
        Stage.HYBRID, f"{settings.experiment_id}/manifest_{set_name}.json"
    )


def _transfer_path(paths, settings) -> Path:
    from qshield_contracts.enums import Stage

    return paths.for_stage(
        Stage.HYBRID, f"{settings.experiment_id}/transfer_parameters.json"
    )


@app.command(name="hybrid-transfer")
def hybrid_transfer_command(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Base config path"
    ),
    profile: str = typer.Option(
        "configs/workflow_update.yaml", "--profile", help="Profile"
    ),
    experiment: str = _EXPERIMENT_OPTION,
    source_set: str = typer.Option(
        "exploratory", "--source-set", help="Set providing angles"
    ),
) -> None:
    """Gộp góc QAOA tối ưu của tập nguồn thành tham số transfer (KHÓA, không ghi đè)."""
    import json

    from qshield_contracts.enums import Stage

    from qshield_pipeline.hybrid.transfer import build_transfer_parameters

    _cfg, settings, paths, context = _hybrid_context(config, profile, experiment)
    target = _transfer_path(paths, settings)
    if target.exists():
        typer.echo(f"✗ {target} đã tồn tại (đã khóa) — không ghi đè.", err=True)
        raise typer.Exit(code=1)
    manifest = json.loads(
        _manifest_path(paths, settings, source_set).read_text(encoding="utf-8")
    )
    payload = build_transfer_parameters(
        paths.for_stage(Stage.HYBRID, settings.experiment_id),
        [item["instance_id"] for item in manifest["instances"]],
        source_set=source_set,
        reps=int(settings.qaoa.get("reps", 1)),
    )
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    context.write_config_snapshot()
    typer.echo(
        f"[hybrid] transfer pooled={payload['pooled']} std={payload['pooled_std']} → {target}"
    )


@app.command(name="hybrid-manifest")
def hybrid_manifest_command(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Base config path"
    ),
    profile: str = typer.Option(
        "configs/workflow_update.yaml", "--profile", help="Profile"
    ),
    experiment: str = _EXPERIMENT_OPTION,
    set_name: str = _SET_OPTION,
) -> None:
    """Chọn portfolio-date instance theo luật đã đăng ký và KHÓA manifest (hash)."""
    import json

    from qshield_contracts.schemas.hybrid import validate_hybrid_manifest

    from qshield_pipeline.hybrid.instances import build_manifest, load_hybrid_data

    cfg, settings, paths, context = _hybrid_context(config, profile, experiment)
    manifest = build_manifest(cfg, settings, load_hybrid_data(cfg, settings), set_name)
    target = _manifest_path(paths, settings, set_name)
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        validate_hybrid_manifest(existing)
        if existing["instances_hash"] != manifest["instances_hash"]:
            typer.echo(
                f"✗ {target} đã khóa với hash khác — không ghi đè; tạo experiment_id mới.",
                err=True,
            )
            raise typer.Exit(code=1)
        typer.echo(f"[hybrid] manifest đã khóa, khớp hash: {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    context.write_config_snapshot()
    typer.echo(
        f"[hybrid] manifest {set_name}: {len(manifest['instances'])} instance, "
        f"{manifest['unique_dates']} ngày, shortfall={manifest['date_shortfall_by_regime']} "
        f"→ {target}"
    )


@app.command(name="hybrid-run")
def hybrid_run_command(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Base config path"
    ),
    profile: str = typer.Option(
        "configs/workflow_update.yaml", "--profile", help="Profile"
    ),
    experiment: str = _EXPERIMENT_OPTION,
    set_name: str = _SET_OPTION,
    limit: int | None = typer.Option(
        None, "--limit", help="Run only the first N instances"
    ),
    instance: list[str] | None = _INSTANCE_OPTION,
    no_resume: bool = typer.Option(
        False, "--no-resume", help="Recompute finished instances"
    ),
    full_only: bool = typer.Option(
        False,
        "--full-only",
        help="Skip qaoa_transfer tracks (pass 1: collect source angles)",
    ),
) -> None:
    """Chạy các instance trong manifest đã khóa; ghi artifact + attempts (kể cả thất bại)."""
    import dataclasses
    import json

    from qshield_contracts.schemas.hybrid import validate_hybrid_manifest

    from qshield_pipeline.hybrid.instances import load_hybrid_data
    from qshield_pipeline.hybrid.runner import run_experiment
    from qshield_pipeline.hybrid.transfer import parameters_for_manifest

    cfg, settings, paths, context = _hybrid_context(config, profile, experiment)
    target = _manifest_path(paths, settings, set_name)
    if not target.exists():
        typer.echo(
            f"✗ Chưa có manifest {target}; chạy hybrid-manifest trước.", err=True
        )
        raise typer.Exit(code=1)
    manifest = json.loads(target.read_text(encoding="utf-8"))
    validate_hybrid_manifest(manifest)
    logger = context.logger("hybrid")
    context.write_config_snapshot()
    transfer_parameters = None
    if full_only:
        settings = dataclasses.replace(
            settings,
            candidate_tracks=tuple(
                t for t in settings.candidate_tracks if t != "qaoa_transfer"
            ),
            compute_tracks=tuple(
                t for t in settings.compute_tracks if not t.endswith("_transfer")
            ),
        )
    elif "qaoa_transfer" in settings.candidate_tracks:
        transfer_path = _transfer_path(paths, settings)
        if not transfer_path.exists():
            typer.echo(
                f"✗ Thiếu {transfer_path}; chạy --full-only rồi hybrid-transfer.",
                err=True,
            )
            raise typer.Exit(code=1)
        transfer_parameters = parameters_for_manifest(
            json.loads(transfer_path.read_text(encoding="utf-8")), manifest
        )
    counts = run_experiment(
        manifest,
        cfg,
        settings,
        load_hybrid_data(cfg, settings),
        paths,
        logger=logger,
        limit=limit,
        resume=not no_resume,
        only=instance,
        transfer_parameters=transfer_parameters,
    )
    context.write_metrics({"stage": "hybrid", "set": set_name, **counts})
    typer.echo(f"[hybrid] {set_name}: {counts}")


@app.command(name="hybrid-report")
def hybrid_report_command(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Base config path"
    ),
    profile: str = typer.Option(
        "configs/workflow_update.yaml", "--profile", help="Profile"
    ),
    experiment: str = _EXPERIMENT_OPTION,
    set_name: str = _SET_OPTION,
) -> None:
    """Tổng hợp paired uplift, gate H1–H6 và claim checklist từ artifact đã ghi."""
    import json

    from qshield_pipeline.hybrid.report import build_report

    _cfg, settings, paths, _context = _hybrid_context(config, profile, experiment)
    manifest = json.loads(
        _manifest_path(paths, settings, set_name).read_text(encoding="utf-8")
    )
    summary = build_report(paths, settings, manifest)
    typer.echo(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "set",
                    "instances_completed",
                    "instances_valid_for_statistics",
                    "gates",
                )
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    app()
