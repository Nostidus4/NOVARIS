# Nguyễn Anh Tú - CLI `uv run qshield-ai regime` / `uv run qshield-ai scenarios`.
"""CLI chặng AI — nơi DUY NHẤT trong `packages/ai` chạm vào đĩa.

Mọi module dưới `qshield_ai/` là hàm thuần: nhận mảng/DataFrame/tham số, trả dữ liệu. File này
phân giải đường dẫn qua `ArtifactPaths` (quy tắc 8), ghi artifact của chặng, và giao 4 file metadata
chuẩn cho `RunContext` (quy tắc 13). `print` chỉ được dùng ở đây.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import typer
from qshield_contracts.config import Config
from qshield_contracts.enums import ArtifactMode, Stage
from qshield_contracts.paths import ArtifactPaths
from qshield_contracts.runs import RunContext
from qshield_contracts.schemas.features import MarketFeaturesSchema
from qshield_contracts.schemas.regime import (
    RegimeDailySchema,
    check_probabilities_sum_to_one,
)
from qshield_contracts.schemas.returns import ReturnsSchema
from qshield_contracts.validate import validate_or_raise

from qshield_ai.baseline.rule_based_regime import rule_based_labels
from qshield_ai.fixtures import synthetic_dataset
from qshield_ai.regime.feature_set import (
    CORR_FEATURE,
    apply_transforms,
    build_feature_frame,
    fit_scaler,
    to_matrix,
)
from qshield_ai.regime.output import (
    RUN_MODE_NON_BASELINE,
    build_regime_daily,
    build_regime_summary,
)
from qshield_ai.regime.selection import GATE_OK, run_selection
from qshield_ai.regime.train import (
    filtered_probabilities,
    smoothed_probabilities,
    viterbi_states,
)


def _tolerate_legacy_console_encoding() -> None:
    """Một số console Windows (Git Bash/mintty, cmd.exe cũ) mặc định cp1252, không mã hóa được
    tiếng Việt có dấu hay ký tự '→'/'—'. `print()` (khác `logging`) không tự bắt
    `UnicodeEncodeError`, nên CLI có thể crash NGAY SAU KHI đã ghi xong toàn bộ artifact — trông
    như lỗi nhưng dữ liệu vẫn đúng. Chỉ nới lỏng khi console không phải UTF-8; PowerShell/Windows
    Terminal hiện đại đã UTF-8 sẵn nên không đổi hành vi ở đó.
    """
    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", None)
        if encoding and encoding.lower() != "utf-8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


_tolerate_legacy_console_encoding()

app = typer.Typer(
    help="Q-SHIELD AI CLI: market regime detection & scenario generation."
)

_FEATURE_COLUMNS = {
    "return_column": "market_log_return",
    "volatility_column": "realized_vol_20d",
    "drawdown_column": "drawdown",
    "correlation_column": CORR_FEATURE,
}
_MOCK_DAYS = 900


def _resolve_run_id(config: Config) -> str | None:
    """`dev` dùng đường dẫn cố định (không cần run_id); `runs` bắt buộc có id trước khi dựng."""
    mode = ArtifactMode(str(config.get("artifacts", {}).get("mode", "dev")))
    if mode == ArtifactMode.DEV:
        return None
    return f"run_{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}"


def _tickers(config: Config) -> list[str]:
    return [entry["ticker"] for entry in config["tickers"]]


def _load_inputs(config: Config, *, mock: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Dữ liệu thật từ `data/processed/`, hoặc fixture giả khi `--mock` (IN-CTR-08 chưa về)."""
    if mock:
        return synthetic_dataset(
            tickers=_tickers(config), n_days=_MOCK_DAYS, seed=int(config["seed"])
        )
    processed = Path(config["paths"]["data_root"]) / "processed"
    return (
        pd.read_parquet(processed / "returns.parquet"),
        pd.read_parquet(processed / "market_features.parquet"),
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


@app.command()
def regime(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Đường dẫn config"
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Sinh dữ liệu giả từ qshield_ai.fixtures thay vì đọc nguồn thật",
    ),
) -> None:
    """Huấn luyện/suy luận Gaussian HMM → regime_daily.parquet (3 xác suất trạng thái/ngày)."""
    cfg = Config.load(Path(config))
    paths = ArtifactPaths(cfg, run_id=_resolve_run_id(cfg))
    context = RunContext(cfg, paths)
    logger = context.logger("regime")
    paths.ensure(Stage.REGIME)
    stage_dir = paths.stage_dir(Stage.REGIME)

    returns, market = _load_inputs(cfg, mock=mock)
    validate_or_raise(returns, ReturnsSchema, context="qshield_ai.regime:input.returns")
    validate_or_raise(
        market, MarketFeaturesSchema, context="qshield_ai.regime:input.market_features"
    )

    market_columns = list(cfg["features"]["market_columns"])
    feature_names = [*market_columns, CORR_FEATURE]
    raw_frame = build_feature_frame(
        market,
        returns,
        tickers=_tickers(cfg),
        market_columns=market_columns,
        corr_window=int(cfg["features"]["corr_window"]),
    )
    logger.info(
        "Feature frame: %d dòng, %s → %s",
        len(raw_frame),
        raw_frame["date"].min().date(),
        raw_frame["date"].max().date(),
    )

    transformed = apply_transforms(raw_frame, cfg["transforms"])
    scaler = fit_scaler(transformed, feature_names)
    matrix = to_matrix(transformed, feature_names, scaler)

    outcome = run_selection(
        matrix,
        transformed,
        raw_frame,
        candidates=cfg["candidates"],
        champion=cfg["champion"],
        seeds=cfg["seeds"]["values"],
        n_iter=int(cfg["n_iter"]),
        min_state_occupancy=float(cfg["gate"]["min_state_occupancy"]),
        min_mean_label_agreement=float(cfg["gate"]["min_mean_label_agreement"]),
        feature_columns=_FEATURE_COLUMNS,
    )
    outcome.report.to_csv(stage_dir / "regime_selection.csv", index=False)

    daily: pd.DataFrame | None = None
    if outcome.gate_status == GATE_OK and outcome.champion is not None:
        model = outcome.champion.model
        daily = build_regime_daily(
            raw_frame,
            filtered=filtered_probabilities(model, matrix),
            smoothed=smoothed_probabilities(model, matrix),
            viterbi=viterbi_states(model, matrix),
            label_map=outcome.label_map or {},
            model_version=(
                f"hmm-{outcome.champion.n_states}s-"
                f"{outcome.champion.covariance_type}-{cfg['feature_contract_version']}"
            ),
            seed=outcome.champion.seed,
            feature_version=str(cfg["feature_contract_version"]),
            run_mode=RUN_MODE_NON_BASELINE,
        )
        validated = validate_or_raise(
            daily, RegimeDailySchema, context="qshield_ai.regime:output"
        )
        check_probabilities_sum_to_one(validated)
        daily.to_parquet(stage_dir / "regime_daily.parquet", index=False)
        logger.info(
            "Champion seed=%s, %d dòng regime đã ghi.",
            outcome.champion.seed,
            len(daily),
        )
    else:
        fallback = rule_based_labels(
            raw_frame,
            volatility_column=_FEATURE_COLUMNS["volatility_column"],
            drawdown_column=_FEATURE_COLUMNS["drawdown_column"],
            vol_quantile=float(cfg["fallback"]["vol_quantile"]),
            drawdown_threshold=float(cfg["fallback"]["drawdown_threshold"]),
        )
        fallback.to_parquet(stage_dir / "regime_daily_rule_based.parquet", index=False)
        logger.warning("Cổng HMM FAIL: %s", "; ".join(outcome.gate_reasons))

    summary = build_regime_summary(
        outcome=outcome,
        daily=daily,
        feature_names=feature_names,
        feature_version=str(cfg["feature_contract_version"]),
        run_mode=RUN_MODE_NON_BASELINE,
        data_version=str(cfg["data"]["data_version"]),
    )
    _write_json(stage_dir / "regime_summary.json", summary)

    context.write_config_snapshot()
    context.write_data_version(str(cfg["data"]["data_version"]))
    context.write_metrics(
        {
            "stage": "regime",
            "gate_status": outcome.gate_status,
            "n_rows": len(daily) if daily is not None else 0,
            "champion_seed": outcome.champion.seed if outcome.champion else None,
            "stability": summary["stability"],
        }
    )

    if outcome.gate_status != GATE_OK:
        print(f"[regime] GATE FAIL: {'; '.join(outcome.gate_reasons)}")
        raise typer.Exit(code=1)
    assert daily is not None, "gate_status == GATE_OK phải đi kèm daily đã dựng."
    print(f"[regime] OK — {len(daily)} dòng → {stage_dir}")


@app.command()
def scenarios(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Đường dẫn config"
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Sinh dữ liệu giả từ qshield_ai.fixtures thay vì đọc nguồn thật",
    ),
) -> None:
    """Sinh kịch bản stress bằng regime-conditioned moving-block bootstrap → stress_scenarios."""
    raise NotImplementedError


if __name__ == "__main__":
    app()
