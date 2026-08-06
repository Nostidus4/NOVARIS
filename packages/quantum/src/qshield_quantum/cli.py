# Đỗ Ngọc Tân - CLI `uv run qshield-quantum solve` → artifacts/.../optimization/.
"""CLI `qshield-quantum` — nơi DUY NHẤT trong `packages/quantum` chạm vào đĩa.

Dựng QUBO từ `g/C/c` (thật hoặc `--mock` qua `fixtures.py`), chạy `verify/consistency` (BẮT BUỘC
trước QAOA — CLAUDE.md quy tắc 15), `exact`, `QAOA` (≥10 seed), `benchmark`, rồi chấm lại bằng true
CVaR (CLAUDE.md quy tắc 17 — BLOCKED tới khi `packages/risk` có thật, xem `plan.md` §1).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import typer
from qshield_contracts.config import Config
from qshield_contracts.enums import ArtifactMode, SolverKind, Stage
from qshield_contracts.paths import ArtifactPaths
from qshield_contracts.runs import RunContext
from qshield_contracts.schemas.optimization import QaoaResult, validate_qaoa_result
from qshield_contracts.schemas.risk import ActionEffectsSchema, PairwiseEffectsSchema
from qshield_contracts.validate import validate_or_raise

from qshield_quantum import fixtures
from qshield_quantum.benchmark import build_benchmark
from qshield_quantum.formulation.penalty import suggest_penalty
from qshield_quantum.formulation.qiskit_program import build_quadratic_program
from qshield_quantum.formulation.qubo import build_qubo
from qshield_quantum.io import action_effects_to_arrays, pairwise_to_matrix
from qshield_quantum.solvers.exact import solve_exact
from qshield_quantum.solvers.qaoa import solve_qaoa
from qshield_quantum.verify.consistency import verify_consistency


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


def _tickers(config: Config) -> list[str]:
    return [entry["ticker"] for entry in config["tickers"]]


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
        if not action_effects_path.exists() or not pairwise_effects_path.exists():
            typer.echo(
                f"✗ Chưa có {action_effects_path} / {pairwise_effects_path} — "
                "packages/risk chưa chạy (hoặc chưa implement, xem plan.md §1). "
                "Dùng --mock để chạy thử với dữ liệu giả.",
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
        baseline = (
            None  # TODO: đọc baseline_risk.json thật khi packages/risk có (plan.md §1)
        )

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
            "configs/quantum.yaml: qaoa.seeds chưa đăng ký — dùng tạm %s (PROVISIONAL, "
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
            "Chưa chấm lại bằng true CVaR (packages/risk.evaluate chưa có, hoặc --mock) — "
            "true_cvar_before/after = NaN, KHÔNG dùng làm bằng chứng baseline."
        )
    else:
        # BLOCKED tới khi packages/risk.evaluate có thật — xem plan.md §1.
        raise NotImplementedError(
            "qshield_risk.evaluate chưa implement — không chấm lại được true CVaR (quy tắc 17)."
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
