"""Risk CLI: the only qshield_risk module that reads or writes artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import typer
from qshield_contracts.config import Config  # type: ignore[import-untyped]
from qshield_contracts.enums import ArtifactMode, Stage  # type: ignore[import-untyped]
from qshield_contracts.paths import ArtifactPaths  # type: ignore[import-untyped]
from qshield_contracts.runs import RunContext  # type: ignore[import-untyped]
from qshield_contracts.schemas.risk import (  # type: ignore[import-untyped]
    ActionEffectsSchema,
    BaselineRisk,
    PairwiseEffectsSchema,
)
from qshield_contracts.validate import validate_or_raise  # type: ignore[import-untyped]

from qshield_risk.costs import CostRates
from qshield_risk.effects import build_effects
from qshield_risk.evaluate import required_float
from qshield_risk.metrics import alpha_key
from qshield_risk.paths import validate_scenario_cube
from qshield_risk.portfolio import align_portfolio_weights, validate_ticker_order

app = typer.Typer(help="Q-SHIELD Risk Engine CLI.")

_CANONICAL_OUTPUTS = (
    "baseline_risk.json",
    "action_effects.csv",
    "pairwise_effects.csv",
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


def _mock_scenarios(config: Config) -> tuple[np.ndarray, tuple[str, ...], dict[str, Any]]:
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
        raise ValueError(f"[risk.input] invalid JSON in {manifest_path}: {exc}.") from exc

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
        raise FileNotFoundError(f"[risk.input] missing file after PASS gate: {cube_path}.")

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


def _portfolio(config: Config, ticker_order: tuple[str, ...]) -> tuple[dict[str, float], float]:
    raw = config.get("sample_portfolio_weights")
    if not isinstance(raw, dict):
        raise TypeError("[risk.config] sample_portfolio_weights must be a ticker-to-weight mapping.")
    weights = {str(ticker): float(weight) for ticker, weight in raw.items()}
    cash_weight = float(config.get("sample_portfolio_cash_weight", 0.0))
    tolerance = required_float(config, "weight_sum_tolerance")
    align_portfolio_weights(weights, ticker_order, cash_weight, tolerance=tolerance)
    return weights, cash_weight


def _validate_outputs(actions: Any, pairs: Any, n_assets: int) -> tuple[Any, Any]:
    action_frame = validate_or_raise(
        actions, ActionEffectsSchema, context="qshield_risk.effects:output.action_effects"
    )
    pair_frame = validate_or_raise(
        pairs, PairwiseEffectsSchema, context="qshield_risk.effects:output.pairwise_effects"
    )
    expected_pairs = n_assets * (n_assets - 1) // 2
    if len(action_frame) != n_assets or action_frame["action_id"].tolist() != list(
        range(n_assets)
    ):
        raise ValueError(
            f"[risk.output] action rows/ids invalid: rows={len(action_frame)}, expected={n_assets}."
        )
    if len(pair_frame) != expected_pairs or not (
        pair_frame["action_i"] < pair_frame["action_j"]
    ).all():
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


if __name__ == "__main__":
    app()
