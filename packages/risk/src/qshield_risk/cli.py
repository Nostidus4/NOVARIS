"""Risk CLI: the only qshield_risk module that reads or writes artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
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

from qshield_risk.candidate_gate import evaluate_candidate_gate
from qshield_risk.candidates import (
    candidate_order,
    select_candidates,
    select_four_level_candidates,
)
from qshield_risk.costs import CostRates
from qshield_risk.effects import build_effects
from qshield_risk.evaluate import confidence_levels, required_float
from qshield_risk.metrics import RiskMetrics, alpha_key, risk_metrics_from_wealth
from qshield_risk.objective import financial_objective
from qshield_risk.paths import portfolio_wealth_paths, validate_scenario_cube
from qshield_risk.policy import RiskPolicy
from qshield_risk.portfolio import align_portfolio_weights, validate_ticker_order
from qshield_risk.rerank import (
    build_financial_baselines,
    materiality_from_cvar,
    polish_reductions,
    rerank_candidates,
)
from qshield_risk.sampling import sample_objective_dataset
from qshield_risk.true_benchmark import build_true_benchmark

app = typer.Typer(help="Q-SHIELD Risk Engine CLI.")

_V1_OUTPUTS = (
    "baseline_risk.json",
    "action_effects.csv",
    "pairwise_effects.csv",
)

_V2_OUTPUTS = (
    "baseline_risk.json",
    "candidate_top10.csv",
    "candidate_topn.csv",
    "candidate_order.json",
    "candidate_gate.json",
    "risk_summary.json",
    "qubo_objective_samples.parquet",
    "true_objective_samples.parquet",
    "objective_sample_manifest.json",
    "reranked_candidates.csv",
    "financial_baselines.csv",
    "portfolio_shortlist_top3.json",
    "final_recommendation.json",
    "true_benchmark.json",
)

_PREPARE_OUTPUTS = (
    "baseline_risk.json",
    "candidate_top10.csv",
    "candidate_topn.csv",
    "candidate_order.json",
    "candidate_gate.json",
    "risk_summary.json",
    "qubo_objective_samples.parquet",
    "true_objective_samples.parquet",
    "objective_sample_manifest.json",
)


def _pending_output(stage_dir: Path, filename: str) -> Path:
    return stage_dir / f".{filename}.pending"


def _cleanup_pending(stage_dir: Path, filenames: tuple[str, ...]) -> None:
    for filename in filenames:
        _pending_output(stage_dir, filename).unlink(missing_ok=True)


def _publish_pending(stage_dir: Path, filenames: tuple[str, ...]) -> None:
    """Atomically replace canonical files after the complete output set validates."""
    for filename in filenames:
        _pending_output(stage_dir, filename).replace(stage_dir / filename)


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
        for filename in _V1_OUTPUTS:
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
    except (FileNotFoundError, KeyError, RuntimeError, TypeError, ValueError) as exc:
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


def _load_workflow_config(config: str, profile: str, override: str | None) -> Config:
    loaded = Config.load_profiled(
        Path(config), Path(profile), Path(override) if override else None
    )
    policy_path = loaded.get("risk_policy_artifact")
    if policy_path:
        path = Path(str(policy_path))
        if not path.exists():
            raise FileNotFoundError(f"[risk.policy] policy artifact not found: {path}.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("[risk.policy] policy artifact must contain a JSON object.")
        loaded["risk_policy"] = payload
    return loaded


def _eligibility_snapshot(
    config: Config,
    tickers: tuple[str, ...],
    manifest: dict[str, Any],
    weights: dict[str, float],
    *,
    mock: bool,
    tolerance: float,
) -> tuple[dict[str, bool], dict[str, str], dict[str, str]]:
    """Read point-in-time Data eligibility; mock runs use an explicit local fixture."""
    if mock:
        mock_eligibility = {ticker: weights[ticker] > tolerance for ticker in tickers}
        mock_reasons = {
            ticker: "MOCK_ELIGIBLE" if mock_eligibility[ticker] else "MOCK_NOT_HELD"
            for ticker in tickers
        }
        return mock_eligibility, mock_reasons, {}

    paths_cfg = config.get("paths") or {}
    data_root = Path(str(paths_cfg.get("data_root", "data")))
    configured = config.get("eligibility_artifact")
    path = Path(str(configured)) if configured else data_root / "processed" / "eligibility_daily.parquet"
    if not path.exists():
        raise FileNotFoundError(f"[risk.eligibility] artifact not found: {path}.")
    frame = pd.read_parquet(path)
    required = {"date", "ticker", "eligible_flag", "reason_code"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"[risk.eligibility] artifact missing columns: {missing}.")
    evaluation_raw = manifest.get("evaluation_date")
    if evaluation_raw is None:
        raise ValueError("[risk.eligibility] scenario manifest evaluation_date is required.")
    evaluation_date = pd.Timestamp(evaluation_raw).normalize()
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame = frame.loc[frame["date"] <= evaluation_date]
    if frame.empty:
        raise ValueError(
            f"[risk.eligibility] no point-in-time rows available by {evaluation_date.date()}."
        )
    snapshot_date = frame["date"].max()
    frame = frame.loc[frame["date"] == snapshot_date]
    if frame["ticker"].duplicated().any():
        raise ValueError("[risk.eligibility] duplicate ticker rows in evaluation snapshot.")
    by_ticker = frame.set_index(frame["ticker"].astype(str))
    missing_tickers = sorted(set(tickers) - set(by_ticker.index))
    if missing_tickers:
        raise ValueError(f"[risk.eligibility] snapshot missing tickers: {missing_tickers}.")
    eligibility: dict[str, bool] = {}
    reasons: dict[str, str] = {}
    sectors: dict[str, str] = {}
    for ticker in tickers:
        row = by_ticker.loc[ticker]
        trade_flag = bool(row.get("trade_eligible_flag", True))
        model_flag = bool(row.get("model_eligible_flag", row["eligible_flag"]))
        eligibility[ticker] = bool(row["eligible_flag"]) and trade_flag and model_flag
        reasons[ticker] = str(row["reason_code"])
        if "sector" in frame.columns and pd.notna(row.get("sector")):
            sectors[ticker] = str(row["sector"])
    return eligibility, reasons, sectors


def _ranking_variants(config: Config) -> dict[str, list[str]] | None:
    raw = config.get("candidate_gate") or {}
    path_value = raw.get("stability_rankings_path")
    if not path_value:
        return None
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError(f"[risk.candidate_gate] stability artifact not found: {path}.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(isinstance(value, list) for value in payload.values()):
        raise TypeError("[risk.candidate_gate] stability artifact must map labels to ticker lists.")
    return {str(key): [str(ticker) for ticker in value] for key, value in payload.items()}


def _handoff_sample_frame(
    frame: pd.DataFrame,
    *,
    identity: dict[str, str],
    order_hash: str,
    policy_version: str,
    seed: int | None,
    artifact_metadata: dict[str, Any] | None = None,
) -> pd.DataFrame:
    result = frame.copy()
    mapping = {
        "intercept": "intercept",
        "main": "main_effect",
        "pairwise": "pairwise_effect",
        "random_stratified": "random",
    }
    result["sample_kind"] = result["sample_type"].map(mapping).fillna("random")
    result["actions_json"] = result["decoded_actions"].map(
        lambda value: json.dumps(value, sort_keys=True)
    )
    component_columns = [
        column
        for column in result.columns
        if column.endswith(("_raw", "_scaled", "_weight", "_contribution"))
    ]
    result["components_json"] = result.apply(
        lambda row: json.dumps(
            {column: row[column] for column in component_columns}, sort_keys=True
        ),
        axis=1,
    )
    result["scalar_objective"] = result["objective"]
    result["violations_json"] = result["constraint_violations"].map(
        lambda value: json.dumps(list(value))
    )
    result["seed"] = pd.Series([seed] * len(result), dtype="Int64")
    result["policy_version"] = policy_version
    result["candidate_order_hash"] = order_hash
    for key, value in identity.items():
        result[key] = value
    for key, value in (artifact_metadata or {}).items():
        result[key] = json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
    return result


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


def _uncertain_metrics(
    cube: np.ndarray,
    stock_amounts: np.ndarray,
    cash_amount: float,
    config: Config,
) -> RiskMetrics:
    """Compute report-only bootstrap uncertainty outside high-volume objective sampling."""
    uncertainty = config if config.get("tail_uncertainty") is not None else None
    return risk_metrics_from_wealth(
        portfolio_wealth_paths(cube, stock_amounts, cash_amount),
        confidence_levels(config),
        uncertainty_config=uncertainty,
    )


def _solver_candidate_pool(
    qaoa_payload: dict[str, Any],
    exact_payload: dict[str, Any] | None,
    benchmark_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Merge exact, QAOA and classical candidates while retaining source provenance."""
    entries: list[dict[str, Any]] = []
    for item in qaoa_payload.get("candidate_pool", []):
        entries.append(
            {
                **item,
                "qubo_energy": float(item.get("energy", item.get("qubo_energy"))),
                "feasible": bool(item.get("feasible", True)),
                "source_solver": ",".join(item.get("sources", [])),
            }
        )
    if exact_payload is not None:
        for item in exact_payload.get("top_feasible_candidates", []):
            entries.append(
                {
                    **item,
                    "qubo_energy": float(item.get("energy")),
                    "feasible": bool(item.get("feasible", True)),
                    "source_solver": "exact",
                }
            )
    if benchmark_payload is not None and benchmark_payload.get("classical_bitstring"):
        entries.append(
            {
                "bitstring": str(benchmark_payload["classical_bitstring"]),
                "qubo_energy": float(benchmark_payload["classical_energy"]),
                "feasible": bool(benchmark_payload.get("classical_feasible", True)),
                "source_solver": "classical",
                "fallback_status": benchmark_payload.get("fallback_status"),
            }
        )
    return entries


@app.command("prepare-workflow")
def prepare_workflow(
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
        help="Optional YAML deep-merged after profile",
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
    for filename in _V2_OUTPUTS:
        (stage_dir / filename).unlink(missing_ok=True)
    _cleanup_pending(stage_dir, _PREPARE_OUTPUTS)
    try:
        identity = _workflow_identity(cfg, context)
        cube, tickers, manifest, weights, cash_weight = _workflow_inputs(
            cfg, paths, mock=mock
        )
        output_candidates = int(
            (cfg.get("candidate_selection") or {}).get("output_candidates", 10)
        )
        tolerance = required_float(cfg, "weight_sum_tolerance")
        eligibility, ineligible_reasons, sectors = _eligibility_snapshot(
            cfg,
            tickers,
            manifest,
            weights,
            mock=mock,
            tolerance=tolerance,
        )
        frame = select_four_level_candidates(
            cube,
            tickers,
            weights,
            cash_weight,
            eligibility,
            cfg,
            output_candidates=output_candidates,
            ineligible_reasons=ineligible_reasons,
        )
        selected_count = int(frame["selected_top10"].sum())
        if selected_count <= 0:
            raise ValueError("[risk.workflow] no held-eligible candidates.")
        gate = evaluate_candidate_gate(
            frame,
            cfg,
            output_candidates=output_candidates,
            ranking_variants=_ranking_variants(cfg),
            sectors=sectors or None,
        )
        policy = RiskPolicy.from_config(cfg)
        policy_version = policy.policy_version if policy is not None else "UNAPPROVED_POLICY"
        parent_hashes = {
            "scenario_manifest": hashlib.sha256(
                json.dumps(manifest, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest(),
            "risk_policy": (
                hashlib.sha256(
                    json.dumps(policy.to_dict(), sort_keys=True, default=str).encode("utf-8")
                ).hexdigest()
                if policy is not None
                else None
            ),
        }
        artifact_metadata: dict[str, Any] = {
            "schema_version": "risk-workflow-v2",
            "producer": "qshield_risk",
            "policy_version": policy_version,
            "gate_status": gate.status,
            "parent_hashes": parent_hashes,
        }
        frame["eligible_status"] = frame["eligible_status"].eq("eligible")
        for key, value in identity.items():
            frame[key] = value
        for key, value in artifact_metadata.items():
            frame[key] = json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
        validate_candidate_top10(frame, expected_candidates=selected_count)
        candidate_path = _pending_output(stage_dir, "candidate_top10.csv")
        frame.to_csv(candidate_path, index=False)
        frame.to_csv(_pending_output(stage_dir, "candidate_topn.csv"), index=False)

        gate_payload = {**identity, **artifact_metadata, **gate.to_dict()}
        _pending_output(stage_dir, "candidate_gate.json").write_text(
            json.dumps(gate_payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        ordered = candidate_order(frame)
        order_payload = {
            **identity,
            **artifact_metadata,
            "candidate_count": selected_count,
            "bits_per_candidate": 2,
            "total_decision_bits": 2 * selected_count,
            "risk_coverage": gate.coverage_at_n,
            "candidate_gate_status": gate.status,
            "candidate_gate_baseline_handoff_allowed": gate.baseline_handoff_allowed,
            "baseline_handoff_allowed": False,
            "handoff_status": "ANALYSIS_ONLY_NON_BASELINE_RUN",
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
        _pending_output(stage_dir, "candidate_order.json").write_text(
            json.dumps(order_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        selected_tickers = [str(item["ticker"]) for item in ordered]
        dataset = sample_objective_dataset(
            cube,
            tickers,
            weights,
            cash_weight,
            selected_tickers,
            cfg,
            candidate_order_hash=order_hash,
        )
        sampling_cfg = cfg.get("objective_sampling") or {}
        split_seeds = sampling_cfg.get("seeds") or {}
        required_split_seeds = ("train", "validation", "holdout")
        if any(split_seeds.get(name) is None for name in required_split_seeds):
            raise ValueError(
                "[risk.prepare_workflow] objective sampling split seeds are required."
            )
        train = _handoff_sample_frame(
            dataset.train,
            identity=identity,
            order_hash=order_hash,
            policy_version=policy_version,
            seed=int(split_seeds["train"]),
            artifact_metadata=artifact_metadata,
        )
        validation = _handoff_sample_frame(
            dataset.validation,
            identity=identity,
            order_hash=order_hash,
            policy_version=policy_version,
            seed=int(split_seeds["validation"]),
            artifact_metadata=artifact_metadata,
        )
        holdout = _handoff_sample_frame(
            dataset.holdout,
            identity=identity,
            order_hash=order_hash,
            policy_version=policy_version,
            seed=int(split_seeds["holdout"]),
            artifact_metadata=artifact_metadata,
        )
        validate_objective_samples(train, expected_bit_count=2 * selected_count)
        samples_path = _pending_output(stage_dir, "qubo_objective_samples.parquet")
        train.to_parquet(samples_path, index=False)
        combined = pd.concat((train, validation, holdout), ignore_index=True)
        combined.to_parquet(
            _pending_output(stage_dir, "true_objective_samples.parquet"), index=False
        )
        _pending_output(stage_dir, "objective_sample_manifest.json").write_text(
            json.dumps(
                {**identity, **artifact_metadata, **dataset.manifest},
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        baseline = financial_objective(
            np.zeros(len(tickers)), cube, tickers, weights, cash_weight, cfg
        )
        baseline_metrics = _uncertain_metrics(
            cube,
            np.asarray([weights[ticker] for ticker in tickers], dtype=float),
            cash_weight,
            cfg,
        )
        warnings = [
            "PROVISIONAL financial/candidate parameters; NON_BASELINE_RUN.",
        ]
        if policy is None:
            warnings.append("UNAPPROVED_POLICY: compatibility cash target is analysis-only.")
        warnings.append("SELL_TAX_POLICY_MISSING: baseline promotion is blocked.")
        if selected_count < output_candidates:
            warnings.append(str(order_payload["deviation"]))
        if gate.status != "PASS":
            warnings.append(
                f"CANDIDATE_GATE_{gate.status}: baseline Quantum handoff blocked; "
                "analysis handoff only."
            )
        risk_summary = {
            **identity,
            **artifact_metadata,
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
            "metrics": baseline_metrics.to_dict(),
            "risk_policy": baseline.policy_metadata,
            "target_cash_increment": (
                required_float(cfg, "target_cash_increment")
                if baseline.policy_metadata is None
                else None
            ),
            "candidate_gate": gate.to_dict(),
            "baseline_handoff_allowed": False,
            "handoff_status": "ANALYSIS_ONLY_NON_BASELINE_RUN",
            "quantum_constraints": (cfg.get("quantum_constraints") or {}),
            "warnings": warnings,
        }
        primary_key = alpha_key(required_float(cfg, "cvar_alpha"))
        baseline_payload = {
            **identity,
            **artifact_metadata,
            "input_source": "mock" if mock else "real",
            "evaluation_date": manifest.get("evaluation_date"),
            "alpha": required_float(cfg, "cvar_alpha"),
            "var_0": baseline.before.var[primary_key],
            "cvar_0": baseline.before.cvar[primary_key],
            "portfolio_weights": weights,
            "cash_weight": cash_weight,
            "ticker_order": list(tickers),
            "risk_metrics": baseline_metrics.to_dict(),
            "risk_policy": baseline.policy_metadata,
            "constraint_violations": list(baseline.constraint_violations),
            "constraint_details": [item.to_dict() for item in baseline.constraint_details],
            "status": baseline.status,
        }
        _pending_output(stage_dir, "baseline_risk.json").write_text(
            json.dumps(baseline_payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        _pending_output(stage_dir, "risk_summary.json").write_text(
            json.dumps(risk_summary, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        context.write_config_snapshot()
        context.write_data_version(str(manifest.get("data_version", "unknown")))
        context.write_metrics(
            {
                **identity,
                "stage": "risk_workflow",
                "gate_status": gate.status,
                "candidate_count": selected_count,
                "bit_count": 2 * selected_count,
                "structured_sample_count": int(dataset.manifest["structured_count"]),
                "objective_sample_count": len(combined),
                "deviation": order_payload["deviation"],
            }
        )
        _publish_pending(stage_dir, _PREPARE_OUTPUTS)
    except (FileNotFoundError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        _cleanup_pending(stage_dir, _PREPARE_OUTPUTS)
        logger.error("Risk workflow preparation failed: %s", exc)
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(
        f"[risk/workflow] candidates={selected_count}, bits={2 * selected_count}, "
        f"samples={len(combined)}, candidate_gate={gate.status} -> {stage_dir}"
    )


@app.command("rerank-polish")
def rerank_polish(
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
        help="Optional YAML deep-merged after profile",
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
    for filename in (
        "reranked_candidates.csv",
        "financial_baselines.csv",
        "portfolio_shortlist_top3.json",
        "final_recommendation.json",
    ):
        (risk_dir / filename).unlink(missing_ok=True)
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
        exact_payload = _load_optional_json(optimization_dir / "exact_solution.json")
        benchmark_payload = _load_optional_json(
            optimization_dir / "workflow_benchmark.json"
        )
        expected_order_hash = str(order_payload.get("candidate_order_hash", ""))
        model_order_hash = str(model_payload.get("candidate_order_hash", ""))
        if model_order_hash and model_order_hash != expected_order_hash:
            raise ValueError(
                "[risk.rerank] candidate_order_hash mismatch between Risk and QUBO model."
            )
        qubo_hash = str(model_payload.get("qubo_hash", ""))
        if not qubo_hash:
            raise ValueError("[risk.rerank] QUBO model must provide qubo_hash.")
        observed_qubo_hashes = {
            str(payload["qubo_hash"])
            for payload in (qaoa_payload, exact_payload, benchmark_payload)
            if payload is not None and payload.get("qubo_hash")
        }
        if observed_qubo_hashes and observed_qubo_hashes != {qubo_hash}:
            raise ValueError(
                f"[risk.rerank] qubo_hash mismatch: {sorted(observed_qubo_hashes)}."
            )
        ordered_tickers = [str(item["ticker"]) for item in order_payload["candidates"]]
        pool = _solver_candidate_pool(qaoa_payload, exact_payload, benchmark_payload)
        reranked = rerank_candidates(
            pool,
            cube,
            tickers,
            weights,
            cash_weight,
            ordered_tickers,
            cfg,
        )
        policy = RiskPolicy.from_config(cfg)
        rerank_metadata: dict[str, Any] = {
            "schema_version": "risk-workflow-v2",
            "producer": "qshield_risk",
            "policy_version": (
                policy.policy_version if policy is not None else "UNAPPROVED_POLICY"
            ),
            "parent_hashes": {
                "scenario_manifest": hashlib.sha256(
                    json.dumps(manifest, sort_keys=True, default=str).encode("utf-8")
                ).hexdigest(),
                "candidate_order": expected_order_hash,
                "qubo": qubo_hash,
            },
            "gate_status": (
                "PASS" if bool(reranked["feasible"].astype(bool).any()) else "FAIL"
            ),
        }
        for key, value in identity.items():
            reranked[key] = value
        for key, value in rerank_metadata.items():
            reranked[key] = json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
        reranked["qubo_hash"] = qubo_hash
        reranked["violations_json"] = reranked["constraint_violations"].map(
            lambda value: json.dumps(list(value))
        )
        reranked_path = risk_dir / "reranked_candidates.csv"
        serializable = reranked.copy()
        serializable["decoded_actions"] = serializable["decoded_actions"].map(
            lambda value: json.dumps(value, sort_keys=True)
        )
        if "solver_provenance" in serializable:
            serializable["solver_provenance"] = serializable["solver_provenance"].map(
                lambda value: json.dumps(value, sort_keys=True)
            )
        serializable.to_csv(reranked_path, index=False)

        baselines = build_financial_baselines(
            cube, tickers, weights, cash_weight, cfg
        )
        for key, value in {**identity, **rerank_metadata}.items():
            baselines[key] = json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
        baselines_serializable = baselines.copy()
        baselines_serializable["reductions"] = baselines_serializable["reductions"].map(
            lambda value: json.dumps(list(value))
        )
        baselines_serializable["constraint_violations"] = baselines_serializable[
            "constraint_violations"
        ].map(lambda value: json.dumps(list(value)))
        baselines_serializable.to_csv(
            risk_dir / "financial_baselines.csv", index=False
        )
        top_three = serializable.head(3).to_dict(orient="records")
        (risk_dir / "portfolio_shortlist_top3.json").write_text(
            json.dumps(
                {
                    **identity,
                    **rerank_metadata,
                    "shortlist_type": "action_portfolios",
                    "does_not_change_asset_top_n": True,
                    "candidates": top_three,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        feasible_rows = reranked.loc[reranked["feasible"].astype(bool)]
        if feasible_rows.empty:
            infeasible_payload = {
                **identity,
                **rerank_metadata,
                "status": "INFEASIBLE_POLICY",
                "recommendation_available": False,
                "candidate_order_hash": order_payload["candidate_order_hash"],
                "qubo_hash": model_payload.get("qubo_hash"),
                "candidate_pool_size": len(reranked),
                "warnings": [
                    "No solver candidate passed the canonical Risk policy constraints."
                ],
            }
            (risk_dir / "final_recommendation.json").write_text(
                json.dumps(infeasible_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            context.write_metrics(
                {
                    **identity,
                    "stage": "rerank_polish",
                    "gate_status": "FAIL",
                    "status": "INFEASIBLE_POLICY",
                    "candidate_pool_size": len(reranked),
                }
            )
            typer.echo("[risk/rerank] INFEASIBLE_POLICY; no final recommendation.")
            return

        winner = feasible_rows.iloc[0]
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
        cvar_before = polished.polished_objective.before.cvar[primary_key]
        cvar_after = polished.polished_objective.after.cvar[primary_key]
        before_uncertain = _uncertain_metrics(
            cube,
            np.asarray([weights[ticker] for ticker in tickers], dtype=float),
            cash_weight,
            cfg,
        )
        after_uncertain = _uncertain_metrics(
            cube,
            polished.polished_objective.trade.stock_amounts,
            polished.polished_objective.trade.cash_amount,
            cfg,
        )
        materiality_cfg = cfg.get("materiality") or {}
        materiality = materiality_from_cvar(
            float(cvar_before),
            float(cvar_after),
            threshold=float(
                materiality_cfg.get("true_cvar_relative_reduction_min", 0.01)
            ),
        )
        warnings = [
            "NON_BASELINE_RUN: underfilled/provisional downstream development evidence."
        ]
        if not materiality["materiality_met"]:
            warnings.append(
                "TL-018 materiality not met: true CVaR relative reduction "
                f"< {materiality['materiality_threshold']:.0%} after cost — "
                "no improvement claim / consider no-action fallback."
            )
        final_payload = {
            **identity,
            **rerank_metadata,
            "status": materiality["recommendation_status"],
            "recommendation_available": True,
            "evaluation_date": manifest.get("evaluation_date"),
            "requested_solver": str(qaoa_payload.get("requested_solver", "qaoa")),
            "actual_solver": str(qaoa_payload.get("actual_solver", "qaoa")),
            "fallback_reason": qaoa_payload.get("fallback_reason"),
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
            "risk_metrics_before": before_uncertain.to_dict(),
            "risk_metrics_after": after_uncertain.to_dict(),
            "true_cvar_before": cvar_before,
            "true_cvar_after": cvar_after,
            "expected_return_before": polished.polished_objective.before.expected_horizon_return,
            "expected_return_after": polished.polished_objective.after.expected_horizon_return,
            "transaction_cost": polished.polished_objective.trade.costs.total,
            "liquidity_penalty": polished.polished_objective.trade.costs.liquidity_penalty,
            "turnover": polished.polished_objective.trade.turnover,
            "objective_before_polish": polished.quantum_objective.value,
            "objective_after_polish": polished.polished_objective.value,
            "objective_improvement": polished.objective_improvement,
            "polishing_dependency": polished.polishing_dependency,
            "constraints_passed": not polished.polished_objective.constraint_violations,
            "constraint_violations": list(
                polished.polished_objective.constraint_violations
            ),
            "constraint_details": [
                item.to_dict()
                for item in polished.polished_objective.constraint_details
            ],
            "risk_policy": polished.polished_objective.policy_metadata,
            **materiality,
            "warnings": warnings,
        }
        (risk_dir / "final_recommendation.json").write_text(
            json.dumps(final_payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        context.write_metrics(
            {
                **identity,
                "stage": "rerank_polish",
                "gate_status": (
                    "PASS"
                    if not polished.polished_objective.constraint_violations
                    else "FAIL"
                ),
                "candidate_pool_size": len(reranked),
                "winning_bitstring": bitstring,
                "true_cvar_before": final_payload["true_cvar_before"],
                "true_cvar_after": final_payload["true_cvar_after"],
            }
        )
    except (FileNotFoundError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        logger.error("Risk rerank/polish failed: %s", exc)
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(
        f"[risk/rerank] winner={bitstring} true_rank=1 -> "
        f"{risk_dir / 'final_recommendation.json'}"
    )


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"[risk.input] invalid JSON in {path}: {exc}.") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"[risk.input] {path} must contain a JSON object.")
    return payload


def _require_json(path: Path) -> dict[str, Any]:
    payload = _load_optional_json(path)
    if payload is None:
        raise FileNotFoundError(f"[risk.input] missing file: {path}.")
    return payload


@app.command("benchmark-true")
def benchmark_true(
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
        help="Optional YAML deep-merged after profile",
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Use deterministic mock scenarios for NON_BASELINE development",
    ),
) -> None:
    """Score exact/QAOA/classical best bitstrings with the true financial objective (G8)."""
    cfg = _load_workflow_config(config, profile, override)
    paths = ArtifactPaths(cfg, run_id=_resolve_run_id(cfg))
    context = RunContext(cfg, paths)
    logger = context.logger("risk_true_benchmark")
    paths.ensure(Stage.RISK)
    risk_dir = paths.stage_dir(Stage.RISK)
    optimization_dir = paths.stage_dir(Stage.QUBO)
    artifact_names = cfg.get("artifacts") or {}
    true_name = str(artifact_names.get("true_benchmark", "true_benchmark.json"))
    out_path = risk_dir / true_name
    out_path.unlink(missing_ok=True)
    try:
        identity = _workflow_identity(cfg, context)
        cube, tickers, manifest, weights, cash_weight = _workflow_inputs(
            cfg, paths, mock=mock
        )
        order_payload = _require_json(risk_dir / "candidate_order.json")
        model_payload = _require_json(optimization_dir / "qubo_model.json")
        exact_payload = _require_json(optimization_dir / "exact_solution.json")
        qaoa_payload = _require_json(optimization_dir / "qaoa_results.json")
        workflow_benchmark = _require_json(optimization_dir / "workflow_benchmark.json")
        final_recommendation = _load_optional_json(
            risk_dir / "final_recommendation.json"
        )
        payload = build_true_benchmark(
            identity=identity,
            scenarios=cube,
            ticker_order=tickers,
            weights=weights,
            cash_weight=cash_weight,
            config=cfg,
            candidate_order_payload=order_payload,
            qubo_model=model_payload,
            exact_payload=exact_payload,
            qaoa_payload=qaoa_payload,
            workflow_benchmark=workflow_benchmark,
            final_recommendation=final_recommendation,
        )
        payload["evaluation_date"] = manifest.get("evaluation_date")
        payload["input_source"] = "mock" if mock else "real"
        policy = RiskPolicy.from_config(cfg)
        payload.update(
            {
                "schema_version": "risk-workflow-v2",
                "producer": "qshield_risk",
                "policy_version": (
                    policy.policy_version if policy is not None else "UNAPPROVED_POLICY"
                ),
                "parent_hashes": {
                    "scenario_manifest": hashlib.sha256(
                        json.dumps(manifest, sort_keys=True, default=str).encode("utf-8")
                    ).hexdigest(),
                    "candidate_order": payload["candidate_order_hash"],
                    "qubo": payload["qubo_hash"],
                },
                "gate_status": "NON_BASELINE_EVIDENCE",
            }
        )
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        context.write_metrics(
            {
                **identity,
                "stage": "true_benchmark",
                "gate_status": "PASS",
                "qubo_hash": payload["qubo_hash"],
                "requested_solver": payload["requested_solver"],
                "actual_solver": payload["actual_solver"],
                "financial_ranking": payload["financial_ranking"],
                "solvers_available": {
                    name: bool(entry.get("available"))
                    for name, entry in payload["solvers"].items()
                },
            }
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        logger.error("Risk true-benchmark failed: %s", exc)
        raise typer.BadParameter(str(exc)) from exc
    ranking = ",".join(payload["financial_ranking"]) or "(none)"
    typer.echo(
        f"[risk/true-benchmark] ranking={ranking} "
        f"requested={payload['requested_solver']} actual={payload['actual_solver']} "
        f"-> {out_path}"
    )


if __name__ == "__main__":
    app()
