"""Risk CLI: the only qshield_risk module that reads or writes artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import typer
from qshield_contracts.config import Config  # type: ignore[import-untyped]
from qshield_contracts.enums import ArtifactMode, Stage  # type: ignore[import-untyped]
from qshield_contracts.paths import ArtifactPaths  # type: ignore[import-untyped]
from qshield_contracts.runs import RunContext  # type: ignore[import-untyped]
from qshield_contracts.schemas.downstream import (  # type: ignore[import-untyped]
    validate_candidate_top10,
    validate_objective_samples,
)
from qshield_contracts.schemas.risk import (  # type: ignore[import-untyped]
    ActionEffectsSchema,
    BaselineRisk,
    PairwiseEffectsSchema,
)
from qshield_contracts.validate import validate_or_raise  # type: ignore[import-untyped]

from qshield_risk.candidates import (
    candidate_order,
    select_candidates,
    select_four_level_candidates,
)
from qshield_risk.costs import CostRates
from qshield_risk.effects import build_effects
from qshield_risk.evaluate import required_float
from qshield_risk.metrics import alpha_key
from qshield_risk.objective import financial_objective
from qshield_risk.paths import validate_scenario_cube
from qshield_risk.portfolio import align_portfolio_weights, validate_ticker_order
from qshield_risk.rerank import polish_reductions, rerank_candidates
from qshield_risk.sampling import sample_objective

app = typer.Typer(help="Q-SHIELD Risk Engine CLI.")

_CANONICAL_OUTPUTS = (
    "baseline_risk.json",
    "action_effects.csv",
    "pairwise_effects.csv",
    "candidate_top10.csv",
)


@app.callback()
def _main() -> None:
    """Expose Risk operations as explicit subcommands."""


def _resolve_run_id(config: Config) -> str | None:
    mode = ArtifactMode(str(config.get("artifacts", {}).get("mode", "dev")))
    if mode == ArtifactMode.DEV:
        return None
    return f"run_{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}"


def _configured_tickers(config: Config) -> tuple[str, ...]:
    entries = config.get("tickers")
    if not isinstance(entries, list):
        raise TypeError("[risk.config] tickers must be a list.")
    return validate_ticker_order([str(entry["ticker"]) for entry in entries])


def _mock_scenarios(
    config: Config,
) -> tuple[np.ndarray, tuple[str, ...], dict[str, Any]]:
    """Deterministic Risk-owned fixture; never evidence for a baseline run."""
    tickers = _configured_tickers(config)
    scenario_count = int(config.get("num_scenarios", 500))
    horizon = int(config.get("horizon_days", 20))
    seed = int(config.get("seed", 20260804)) + 1701
    rng = np.random.default_rng(seed)
    market = rng.normal(-0.0006, 0.014, size=(scenario_count, horizon, 1))
    idiosyncratic = rng.normal(0.0, 0.009, size=(scenario_count, horizon, len(tickers)))
    loadings = np.linspace(0.75, 1.20, len(tickers)).reshape(1, 1, -1)
    cube = np.clip(market * loadings + idiosyncratic, -0.95, None)
    manifest = {
        "run_id": "risk_mock_fixture",
        "gate_status": "PASS",
        "input_source": "mock",
        "evaluation_date": "mock",
        "target_regime": "volatile",
        "return_type": "simple",
        "ticker_order": list(tickers),
        "num_scenarios": scenario_count,
        "horizon_days": horizon,
        "data_version": "risk-mock-v1",
    }
    return cube, tickers, manifest


def _load_real_scenarios(
    config: Config, paths: ArtifactPaths
) -> tuple[np.ndarray, tuple[str, ...], dict[str, Any]]:
    manifest_path = paths.for_stage(Stage.SCENARIOS, "scenario_manifest.json")
    cube_path = paths.for_stage(Stage.SCENARIOS, "stress_scenarios.npz")
    if not manifest_path.exists():
        raise FileNotFoundError(f"[risk.input] missing file: {manifest_path}.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"[risk.input] invalid JSON in {manifest_path}: {exc}."
        ) from exc

    if manifest.get("gate_status") != "PASS":
        raise ValueError(
            f"[risk.input] {manifest_path}: gate_status={manifest.get('gate_status')!r}; "
            "Risk requires PASS."
        )
    if manifest.get("input_source") != "real":
        raise ValueError(
            f"[risk.input] {manifest_path}: input_source={manifest.get('input_source')!r}; "
            "real Risk run requires 'real'."
        )
    if manifest.get("return_type") != "simple":
        raise ValueError(
            f"[risk.input] {manifest_path}: return_type={manifest.get('return_type')!r}; "
            "expected 'simple'."
        )
    if not cube_path.exists():
        raise FileNotFoundError(
            f"[risk.input] missing file after PASS gate: {cube_path}."
        )

    with np.load(cube_path, allow_pickle=False) as data:
        if "scenarios" not in data.files or "ticker_order" not in data.files:
            raise ValueError(
                f"[risk.input] {cube_path}: required keys are scenarios and ticker_order; "
                f"found {data.files}."
            )
        cube = np.asarray(data["scenarios"], dtype=float)
        npz_tickers = tuple(str(ticker) for ticker in data["ticker_order"].tolist())

    manifest_tickers = validate_ticker_order(manifest.get("ticker_order", ()))
    configured_tickers = _configured_tickers(config)
    if npz_tickers != manifest_tickers or manifest_tickers != configured_tickers:
        raise ValueError(
            f"[risk.input] ticker order mismatch: npz={npz_tickers}, "
            f"manifest={manifest_tickers}, config={configured_tickers}."
        )
    expected_shape = (
        int(config.get("num_scenarios", 500)),
        int(config.get("horizon_days", 20)),
        len(configured_tickers),
    )
    if cube.shape != expected_shape:
        raise ValueError(
            f"[risk.input] {cube_path}: shape={cube.shape}; expected {expected_shape}."
        )
    if manifest.get("num_scenarios") != expected_shape[0]:
        raise ValueError(
            f"[risk.input] {manifest_path}: num_scenarios="
            f"{manifest.get('num_scenarios')!r}; expected {expected_shape[0]}."
        )
    if manifest.get("horizon_days") != expected_shape[1]:
        raise ValueError(
            f"[risk.input] {manifest_path}: horizon_days={manifest.get('horizon_days')!r}; "
            f"expected {expected_shape[1]}."
        )
    return cube, manifest_tickers, manifest


def _portfolio(
    config: Config, ticker_order: tuple[str, ...]
) -> tuple[dict[str, float], float]:
    raw = config.get("sample_portfolio_weights")
    if not isinstance(raw, dict):
        raise TypeError(
            "[risk.config] sample_portfolio_weights must be a ticker-to-weight mapping."
        )
    weights = {str(ticker): float(weight) for ticker, weight in raw.items()}
    cash_weight = float(config.get("sample_portfolio_cash_weight", 0.0))
    tolerance = required_float(config, "weight_sum_tolerance")
    align_portfolio_weights(weights, ticker_order, cash_weight, tolerance=tolerance)
    return weights, cash_weight


def _validate_outputs(actions: Any, pairs: Any, n_assets: int) -> tuple[Any, Any]:
    action_frame = validate_or_raise(
        actions,
        ActionEffectsSchema,
        context="qshield_risk.effects:output.action_effects",
    )
    pair_frame = validate_or_raise(
        pairs,
        PairwiseEffectsSchema,
        context="qshield_risk.effects:output.pairwise_effects",
    )
    expected_pairs = n_assets * (n_assets - 1) // 2
    if len(action_frame) != n_assets or action_frame["action_id"].tolist() != list(
        range(n_assets)
    ):
        raise ValueError(
            f"[risk.output] action rows/ids invalid: rows={len(action_frame)}, expected={n_assets}."
        )
    if (
        len(pair_frame) != expected_pairs
        or not (pair_frame["action_i"] < pair_frame["action_j"]).all()
    ):
        raise ValueError(
            f"[risk.output] pair rows/order invalid: rows={len(pair_frame)}, "
            f"expected={expected_pairs}, required action_i < action_j."
        )
    return action_frame, pair_frame


@app.command()
def effects(
    config: str = typer.Option("configs/base.yaml", "--config", help="Config path"),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Use a deterministic Risk-local fixture instead of real scenario artifacts",
    ),
) -> None:
    """Compute baseline CVaR plus raw g/C/c QUBO handoff artifacts."""
    cfg = Config.load(Path(config))
    paths = ArtifactPaths(cfg, run_id=_resolve_run_id(cfg))
    context = RunContext(cfg, paths)
    logger = context.logger("risk")
    paths.ensure(Stage.RISK)
    stage_dir = paths.stage_dir(Stage.RISK)

    if paths.mode == ArtifactMode.DEV:
        for filename in _CANONICAL_OUTPUTS:
            (stage_dir / filename).unlink(missing_ok=True)

    try:
        required_float(cfg, "weight_sum_tolerance")
        CostRates.from_config(cfg)
        cube, ticker_order, manifest = (
            _mock_scenarios(cfg) if mock else _load_real_scenarios(cfg, paths)
        )
        wanted_source = "mock" if mock else "real"
        if manifest.get("input_source") != wanted_source:
            raise ValueError(
                f"[risk.input] source mismatch: command={wanted_source}, "
                f"manifest={manifest.get('input_source')!r}."
            )
        validate_scenario_cube(
            cube,
            expected_horizon=int(cfg.get("horizon_days", 20)),
            expected_assets=len(ticker_order),
        )
        weights, cash_weight = _portfolio(cfg, ticker_order)
        result = build_effects(cube, ticker_order, weights, cash_weight, cfg)
        action_frame, pair_frame = _validate_outputs(
            result.actions, result.pairs, len(ticker_order)
        )

        alpha = required_float(cfg, "cvar_alpha")
        primary_key = alpha_key(alpha)
        canonical = BaselineRisk(
            var_0=result.baseline.var[primary_key],
            cvar_0=result.baseline.cvar[primary_key],
            portfolio_weights=weights,
            alpha=alpha,
        )
        baseline_payload = {
            **asdict(canonical),
            "cash_weight": cash_weight,
            "ticker_order": list(ticker_order),
            "risk_metrics": result.baseline.to_dict(),
            "evaluation_date": manifest.get("evaluation_date"),
            "target_regime": manifest.get("target_regime"),
            "input_source": wanted_source,
            "scenario_run_id": manifest.get("run_id"),
        }
        baseline_json = json.dumps(
            baseline_payload, ensure_ascii=False, indent=2, allow_nan=False
        )

        (stage_dir / "baseline_risk.json").write_text(baseline_json, encoding="utf-8")
        action_frame.to_csv(stage_dir / "action_effects.csv", index=False)
        pair_frame.to_csv(stage_dir / "pairwise_effects.csv", index=False)
        context.write_config_snapshot()
        context.write_data_version(str(manifest.get("data_version", "unknown")))
        context.write_metrics(
            {
                "stage": "risk",
                "input_source": wanted_source,
                "evaluation_date": manifest.get("evaluation_date"),
                "target_regime": manifest.get("target_regime"),
                "baseline_cvar": result.baseline.cvar[primary_key],
                "alpha": alpha,
                "action_count": len(action_frame),
                "pair_count": len(pair_frame),
                "units": "decimal_nav",
            }
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        logger.error("Risk effects failed: %s", exc)
        raise typer.BadParameter(str(exc)) from exc

    print(
        f"[risk] input_source={wanted_source} actions={len(action_frame)} "
        f"pairs={len(pair_frame)} -> {stage_dir}"
    )


@app.command()
def candidates(
    config: str = typer.Option("configs/base.yaml", "--config", help="Config path"),
) -> None:
    """Rank tickers and flag the dynamic top-N selection (`candidate_top10.csv`).

    Reads `action_effects.csv`/`baseline_risk.json` already written by `effects` — run `effects`
    first. Generic in N (see `qshield_risk.candidates`): with the current 8-ticker universe every
    row is selected; real filtering only kicks in once the universe passes `output_candidates`
    (the 30-ticker `workflow_update` baseline).
    """
    cfg = Config.load(Path(config))
    paths = ArtifactPaths(cfg, run_id=_resolve_run_id(cfg))
    context = RunContext(cfg, paths)
    logger = context.logger("risk")
    stage_dir = paths.stage_dir(Stage.RISK)

    action_effects_path = stage_dir / "action_effects.csv"
    baseline_path = stage_dir / "baseline_risk.json"
    for path in (action_effects_path, baseline_path):
        if not path.exists():
            typer.echo(
                f"✗ Chưa có {path} — chạy `qshield-risk effects` trước.", err=True
            )
            raise typer.Exit(code=1)

    try:
        action_effects = pd.read_csv(action_effects_path)
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        weights = {str(k): float(v) for k, v in baseline["portfolio_weights"].items()}
        cost_rates = CostRates.from_config(cfg)
        reduction_pct = required_float(cfg, "action_reduction_pct")
        output_candidates = int(
            (cfg.get("candidate_selection") or {}).get("output_candidates", 10)
        )

        frame = select_candidates(
            action_effects,
            baseline_cvar=float(baseline["cvar_0"]),
            weights=weights,
            cost_rates=cost_rates,
            reduction_pct=reduction_pct,
            output_candidates=output_candidates,
        )
        frame.to_csv(stage_dir / "candidate_top10.csv", index=False)
        context.write_metrics(
            {
                "stage": "risk_candidates",
                "n_tickers": len(frame),
                "output_candidates": output_candidates,
                "n_selected": int(frame["selected_top10"].sum()),
            }
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        logger.error("Risk candidates failed: %s", exc)
        raise typer.BadParameter(str(exc)) from exc

    print(
        f"[risk] candidates n_tickers={len(frame)} selected={int(frame['selected_top10'].sum())} "
        f"-> {stage_dir / 'candidate_top10.csv'}"
    )


def _stable_config_hash(config: Config) -> str:
    payload = json.dumps(
        dict(config), sort_keys=True, default=str, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _workflow_identity(config: Config, context: RunContext) -> dict[str, str]:
    profile = config.get("profile") or {}
    if not isinstance(profile, dict):
        raise TypeError("[risk.workflow] profile must be a mapping.")
    profile_id = str(profile.get("id", ""))
    profile_status = str(profile.get("status", ""))
    if not profile_id or not profile_status:
        raise ValueError("[risk.workflow] profile.id and profile.status are required.")
    if profile_status != "NON_BASELINE_RUN":
        raise ValueError(
            "[risk.workflow] underfilled development path must be NON_BASELINE_RUN."
        )
    return {
        "run_id": context.run_id,
        "profile_id": profile_id,
        "profile_status": profile_status,
        "config_version": str(
            (config.get("provenance") or {}).get("config_version", "provisional-v1")
        ),
        "config_hash": _stable_config_hash(config),
    }


def _load_workflow_config(config: str, profile: str, override: str) -> Config:
    return Config.load_profiled(Path(config), Path(profile), Path(override))


def _workflow_inputs(
    config: Config, paths: ArtifactPaths, *, mock: bool
) -> tuple[
    np.ndarray,
    tuple[str, ...],
    dict[str, Any],
    dict[str, float],
    float,
]:
    cube, ticker_order, manifest = (
        _mock_scenarios(config) if mock else _load_real_scenarios(config, paths)
    )
    validate_scenario_cube(
        cube,
        expected_horizon=int(config.get("horizon_days", 20)),
        expected_assets=len(ticker_order),
    )
    weights, cash_weight = _portfolio(config, ticker_order)
    return cube, ticker_order, manifest, weights, cash_weight


@app.command("prepare-workflow")
def prepare_workflow(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Base config path"
    ),
    profile: str = typer.Option(
        "configs/profiles/workflow_update.yaml",
        "--profile",
        help="Product profile path",
    ),
    override: str = typer.Option(
        "configs/provisional/workflow_update_downstream.yaml",
        "--override",
        help="Explicit NON_BASELINE override path",
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Use deterministic eight-ticker scenarios for NON_BASELINE development",
    ),
) -> None:
    """Create four-level candidate, order, risk-summary and objective-sample handoffs."""
    cfg = _load_workflow_config(config, profile, override)
    paths = ArtifactPaths(cfg, run_id=_resolve_run_id(cfg))
    context = RunContext(cfg, paths)
    logger = context.logger("risk_workflow")
    paths.ensure(Stage.RISK)
    stage_dir = paths.stage_dir(Stage.RISK)
    try:
        identity = _workflow_identity(cfg, context)
        cube, tickers, manifest, weights, cash_weight = _workflow_inputs(
            cfg, paths, mock=mock
        )
        output_candidates = int(
            (cfg.get("candidate_selection") or {}).get("output_candidates", 10)
        )
        tolerance = required_float(cfg, "weight_sum_tolerance")
        eligibility = {ticker: float(weights[ticker]) > tolerance for ticker in tickers}
        frame = select_four_level_candidates(
            cube,
            tickers,
            weights,
            cash_weight,
            eligibility,
            cfg,
            output_candidates=output_candidates,
        )
        selected_count = int(frame["selected_top10"].sum())
        if selected_count <= 0:
            raise ValueError("[risk.workflow] no held-eligible candidates.")
        frame["eligible_status"] = frame["eligible_status"].eq("eligible")
        for key, value in identity.items():
            frame[key] = value
        validate_candidate_top10(frame, expected_candidates=selected_count)
        candidate_path = stage_dir / "candidate_top10.csv"
        frame.to_csv(candidate_path, index=False)

        ordered = candidate_order(frame)
        selected_contribution = float(
            frame.loc[frame["selected_top10"], "baseline_CVaR_contribution"].abs().sum()
        )
        total_contribution = float(frame["baseline_CVaR_contribution"].abs().sum())
        coverage = (
            min(1.0, selected_contribution / total_contribution)
            if total_contribution > 0.0
            else 0.0
        )
        order_payload = {
            **identity,
            "candidate_count": selected_count,
            "bits_per_candidate": 2,
            "total_decision_bits": 2 * selected_count,
            "risk_coverage": coverage,
            "underfilled": selected_count < output_candidates,
            "deviation": (
                f"UNDERFILLED_CANDIDATES_{selected_count}_OF_{output_candidates}"
                if selected_count < output_candidates
                else None
            ),
            "bit_mapping": {"00": 0, "10": 10, "01": 20, "11": 30},
            "candidates": ordered,
        }
        order_json = json.dumps(
            order_payload, ensure_ascii=False, sort_keys=True, default=str
        )
        order_hash = hashlib.sha256(order_json.encode("utf-8")).hexdigest()
        order_payload["candidate_order_hash"] = order_hash
        (stage_dir / "candidate_order.json").write_text(
            json.dumps(order_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        selected_tickers = [str(item["ticker"]) for item in ordered]
        samples = sample_objective(
            cube,
            tickers,
            weights,
            cash_weight,
            selected_tickers,
            cfg,
        )
        samples["sample_kind"] = samples["sample_type"].map(
            {
                "intercept": "intercept",
                "main": "main_effect",
                "pairwise": "pairwise_effect",
            }
        )
        samples["actions_json"] = samples["decoded_actions"].map(
            lambda value: json.dumps(value, sort_keys=True)
        )
        component_columns = [
            column
            for column in samples.columns
            if column.endswith(("_raw", "_scaled", "_weight", "_contribution"))
        ]
        samples["components_json"] = samples.apply(
            lambda row: json.dumps(
                {column: row[column] for column in component_columns}, sort_keys=True
            ),
            axis=1,
        )
        samples["scalar_objective"] = samples["objective"]
        samples["violations_json"] = samples["constraint_violations"].map(
            lambda value: json.dumps(list(value))
        )
        samples["feasible"] = samples["constraint_violations"].map(
            lambda value: not value
        )
        samples["seed"] = pd.Series([pd.NA] * len(samples), dtype="Int64")
        samples["policy_version"] = str(
            (cfg.get("objective_sampling") or {}).get(
                "policy_version", "provisional-structured-v1"
            )
        )
        samples["candidate_order_hash"] = order_hash
        for key, value in identity.items():
            samples[key] = value
        validate_objective_samples(samples, expected_bit_count=2 * selected_count)
        samples_path = stage_dir / "qubo_objective_samples.parquet"
        samples.to_parquet(samples_path, index=False)

        baseline = financial_objective(
            np.zeros(len(tickers)), cube, tickers, weights, cash_weight, cfg
        )
        warnings = [
            "PROVISIONAL financial/candidate parameters; NON_BASELINE_RUN.",
        ]
        if selected_count < output_candidates:
            warnings.append(str(order_payload["deviation"]))
        risk_summary = {
            **identity,
            "input_source": "mock" if mock else "real",
            "evaluation_date": manifest.get("evaluation_date"),
            "scenario_count": int(cube.shape[0]),
            "ticker_order": list(tickers),
            "portfolio_weights": weights,
            "cash_weight": cash_weight,
            "candidate_order_hash": order_hash,
            "candidate_count": selected_count,
            "total_decision_bits": 2 * selected_count,
            "cvar_alpha_primary": required_float(cfg, "cvar_alpha"),
            "loss_sign_convention": "positive_is_loss",
            "metrics": baseline.before.to_dict(),
            "target_cash_increment": required_float(cfg, "target_cash_increment"),
            "quantum_constraints": (cfg.get("quantum_constraints") or {}),
            "warnings": warnings,
        }
        (stage_dir / "risk_summary.json").write_text(
            json.dumps(risk_summary, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        context.write_config_snapshot()
        context.write_data_version(str(manifest.get("data_version", "unknown")))
        context.write_metrics(
            {
                **identity,
                "stage": "risk_workflow",
                "gate_status": "PASS",
                "candidate_count": selected_count,
                "bit_count": 2 * selected_count,
                "structured_sample_count": len(samples),
                "deviation": order_payload["deviation"],
            }
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        logger.error("Risk workflow preparation failed: %s", exc)
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(
        f"[risk/workflow] candidates={selected_count}, bits={2 * selected_count}, "
        f"samples={len(samples)} -> {stage_dir}"
    )


@app.command("rerank-polish")
def rerank_polish(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Base config path"
    ),
    profile: str = typer.Option(
        "configs/profiles/workflow_update.yaml",
        "--profile",
        help="Product profile path",
    ),
    override: str = typer.Option(
        "configs/provisional/workflow_update_downstream.yaml",
        "--override",
        help="Explicit NON_BASELINE override path",
    ),
    mock: bool = typer.Option(
        False, "--mock", help="Recreate deterministic mock scenarios"
    ),
) -> None:
    """Rerank solver candidates with true risk and polish only the Quantum active set."""
    cfg = _load_workflow_config(config, profile, override)
    paths = ArtifactPaths(cfg, run_id=_resolve_run_id(cfg))
    context = RunContext(cfg, paths)
    logger = context.logger("risk_rerank_polish")
    paths.ensure(Stage.RISK)
    risk_dir = paths.stage_dir(Stage.RISK)
    optimization_dir = paths.stage_dir(Stage.QUBO)
    try:
        identity = _workflow_identity(cfg, context)
        cube, tickers, manifest, weights, cash_weight = _workflow_inputs(
            cfg, paths, mock=mock
        )
        order_payload = json.loads(
            (risk_dir / "candidate_order.json").read_text(encoding="utf-8")
        )
        qaoa_payload = json.loads(
            (optimization_dir / "qaoa_results.json").read_text(encoding="utf-8")
        )
        model_payload = json.loads(
            (optimization_dir / "qubo_model.json").read_text(encoding="utf-8")
        )
        ordered_tickers = [str(item["ticker"]) for item in order_payload["candidates"]]
        raw_pool = qaoa_payload.get("candidate_pool", [])
        pool = [
            {
                **item,
                "qubo_energy": float(item.get("energy", item.get("qubo_energy"))),
                "feasible": True,
                "source_solver": ",".join(item.get("sources", [])),
            }
            for item in raw_pool
        ]
        reranked = rerank_candidates(
            pool,
            cube,
            tickers,
            weights,
            cash_weight,
            ordered_tickers,
            cfg,
        )
        for key, value in identity.items():
            reranked[key] = value
        reranked["qubo_hash"] = str(model_payload.get("qubo_hash", ""))
        reranked["violations_json"] = reranked["constraint_violations"].map(
            lambda value: json.dumps(list(value))
        )
        reranked_path = risk_dir / "reranked_candidates.csv"
        serializable = reranked.copy()
        serializable["decoded_actions"] = serializable["decoded_actions"].map(
            lambda value: json.dumps(value, sort_keys=True)
        )
        serializable.to_csv(reranked_path, index=False)

        winner = reranked.iloc[0]
        candidate_reductions = dict(winner["decoded_actions"])
        full_quantum = np.zeros(len(tickers), dtype=float)
        ticker_index = {ticker: index for index, ticker in enumerate(tickers)}
        for ticker, reduction in candidate_reductions.items():
            full_quantum[ticker_index[str(ticker)]] = float(reduction)
        polishing_cfg = cfg.get("local_polishing") or {}
        polished = polish_reductions(
            full_quantum,
            cube,
            tickers,
            weights,
            cash_weight,
            cfg,
            max_adjustment=float(polishing_cfg.get("max_adjustment_pp", 5)) / 100,
            maximum_reduction=float(
                polishing_cfg.get("final_reduction_bounds_pct", [0, 30])[1]
            )
            / 100,
        )
        actions = []
        bitstring = str(winner["bitstring"])
        for position, ticker in enumerate(ordered_tickers):
            universe_index = ticker_index[ticker]
            actions.append(
                {
                    "ticker": ticker,
                    "bits": bitstring[2 * position : 2 * position + 2],
                    "quantum_reduction": polished.quantum_reductions[universe_index],
                    "polished_reduction": polished.polished_reductions[universe_index],
                    "current_weight": float(weights[ticker]),
                    "sell_value": float(
                        weights[ticker] * polished.polished_reductions[universe_index]
                    ),
                    "final_weight": float(
                        polished.polished_objective.trade.stock_weights[universe_index]
                    ),
                }
            )
        primary_key = alpha_key(required_float(cfg, "cvar_alpha"))
        final_payload = {
            **identity,
            "evaluation_date": manifest.get("evaluation_date"),
            "requested_solver": "qaoa",
            "actual_solver": "qaoa",
            "candidate_order_hash": order_payload["candidate_order_hash"],
            "qubo_hash": model_payload.get("qubo_hash"),
            "candidate_count": len(ordered_tickers),
            "bits_per_candidate": 2,
            "winning_bitstring": bitstring,
            "actions": actions,
            "portfolio_after": {
                "stock_weights": {
                    ticker: float(
                        polished.polished_objective.trade.stock_weights[index]
                    )
                    for index, ticker in enumerate(tickers)
                },
                "cash_weight": polished.polished_objective.trade.cash_weight,
                "nav_after": polished.polished_objective.trade.nav_after,
            },
            "cvar_before": polished.polished_objective.before.cvar,
            "cvar_after": polished.polished_objective.after.cvar,
            "true_cvar_before": polished.polished_objective.before.cvar[primary_key],
            "true_cvar_after": polished.polished_objective.after.cvar[primary_key],
            "expected_return_before": polished.polished_objective.before.expected_horizon_return,
            "expected_return_after": polished.polished_objective.after.expected_horizon_return,
            "transaction_cost": polished.polished_objective.trade.costs.total,
            "turnover": polished.polished_objective.trade.turnover,
            "objective_before_polish": polished.quantum_objective.value,
            "objective_after_polish": polished.polished_objective.value,
            "objective_improvement": polished.objective_improvement,
            "polishing_dependency": polished.polishing_dependency,
            "constraints_passed": not polished.polished_objective.constraint_violations,
            "warnings": [
                "NON_BASELINE_RUN: underfilled/provisional downstream development evidence."
            ],
        }
        (risk_dir / "final_recommendation.json").write_text(
            json.dumps(final_payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        context.write_metrics(
            {
                **identity,
                "stage": "rerank_polish",
                "gate_status": "PASS",
                "candidate_pool_size": len(reranked),
                "winning_bitstring": bitstring,
                "true_cvar_before": final_payload["true_cvar_before"],
                "true_cvar_after": final_payload["true_cvar_after"],
            }
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        logger.error("Risk rerank/polish failed: %s", exc)
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(
        f"[risk/rerank] winner={bitstring} true_rank=1 -> "
        f"{risk_dir / 'final_recommendation.json'}"
    )


if __name__ == "__main__":
    app()
