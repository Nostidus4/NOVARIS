# Nguyễn Anh Tú - CLI `uv run qshield-ai regime` / `uv run qshield-ai scenarios`.
"""CLI chặng AI — nơi DUY NHẤT trong `packages/ai` chạm vào đĩa.

Mọi module dưới `qshield_ai/` là hàm thuần: nhận mảng/DataFrame/tham số, trả dữ liệu. File này
phân giải đường dẫn qua `ArtifactPaths` (quy tắc 8), ghi artifact của chặng, và giao 4 file metadata
chuẩn cho `RunContext` (quy tắc 13). `print` chỉ được dùng ở đây.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import typer
from qshield_contracts.config import Config
from qshield_contracts.enums import ArtifactMode, RegimeName, Stage
from qshield_contracts.paths import ArtifactPaths
from qshield_contracts.runs import RunContext
from qshield_contracts.schemas.features import MarketFeaturesSchema
from qshield_contracts.schemas.regime import (
    RegimeDailySchema,
    check_probabilities_sum_to_one,
)
from qshield_contracts.schemas.returns import ReturnsSchema
from qshield_contracts.schemas.scenarios import ScenarioMetadata, validate_scenarios
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
    INPUT_SOURCE_MOCK,
    INPUT_SOURCE_REAL,
    RUN_MODE_NON_BASELINE,
    UNRESOLVED_DECISIONS,
    build_regime_daily,
    build_regime_summary,
)
from qshield_ai.regime.selection import GATE_OK, run_selection
from qshield_ai.regime.train import (
    filtered_probabilities,
    smoothed_probabilities,
    viterbi_states,
)
from qshield_ai.scenarios.bootstrap import (
    build_block_pool,
    build_return_panel,
    generate_cube,
    resolve_evaluation_date,
)
from qshield_ai.scenarios.validate import GATE_FAIL as SCENARIO_GATE_FAIL
from qshield_ai.scenarios.validate import (
    build_validation_report,
    distribution_metrics,
    gate_status,
    reference_windows,
    structural_violations,
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


app = typer.Typer(
    help="Q-SHIELD AI CLI: market regime detection & scenario generation."
)


@app.callback()
def _main() -> None:
    """Chạy trước mọi subcommand — chỉ khi gọi qua CLI, không khi `import qshield_ai.cli`.

    Mutating `sys.stdout`/`sys.stderr` là side effect toàn tiến trình; đặt ở đây thay vì module
    level để một orchestrator (vd. `qshield_pipeline`) import module này mà không tự nhiên bị đổi
    encoding console của nó.
    """
    _tolerate_legacy_console_encoding()


_FEATURE_COLUMNS = {
    "return_column": "market_log_return",
    "volatility_column": "realized_vol_20d",
    "drawdown_column": "drawdown",
    "correlation_column": CORR_FEATURE,
}
_MOCK_DAYS = 900
_DEFAULT_PROFILE = Path("configs/profiles/workflow_update.yaml")
_DEFAULT_OVERRIDE = Path("configs/provisional/workflow_update_downstream.yaml")
# Thứ tự cố định ⇒ mỗi regime nhận một seed lệch xác định, tái lập được giữa các lần chạy: đổi
# thứ tự là đổi cube sinh ra, nên tuple này được viết tường minh chứ không lấy theo thứ tự khai
# báo của enum. Dựng từ thành viên `RegimeName` (không phải literal chuỗi) để đổi tên nhãn ở
# `qshield_contracts` vỡ ngay lúc import, thay vì âm thầm cho ra ba pool block rỗng.
_REGIME_ORDER = (
    RegimeName.NORMAL.value,
    RegimeName.VOLATILE.value,
    RegimeName.STRESS.value,
)


def _load_cli_config(
    config: str,
    profile: str | None = None,
    override: str | None = None,
) -> Config:
    """Load base config, or deep-merge profile + Decision override when flags are set."""
    base = Path(config)
    if profile is not None or override is not None:
        return Config.load_profiled(
            base,
            Path(profile) if profile else _DEFAULT_PROFILE,
            Path(override) if override else _DEFAULT_OVERRIDE,
        )
    return Config.load(base)


def _resolve_run_id(config: Config) -> str | None:
    """`dev` dùng đường dẫn cố định (không cần run_id); `runs` bắt buộc có id trước khi dựng.

    Nếu config có khóa `run_id` (do `packages/pipeline` tiêm vào khi chạy cả chuỗi — xem
    `qshield_pipeline/run_context.py`), dùng NGUYÊN giá trị đó thay vì tự sinh — để mọi chặng
    trong cùng một lần chạy pipeline chia sẻ đúng một run_id (docs/perf/2026-08-04-pipeline-
    timing.md §6)."""
    if config.get("run_id"):
        return str(config["run_id"])
    mode = ArtifactMode(str(config.get("artifacts", {}).get("mode", "dev")))
    if mode == ArtifactMode.DEV:
        return None
    return f"run_{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}"


def _tickers(config: Config) -> list[str]:
    return [entry["ticker"] for entry in config["tickers"]]


def _regime_corr_tickers(config: Config, returns: pd.DataFrame) -> list[str]:
    """Tickers dùng cho ``mean_pairwise_corr_60d`` — phải có dữ liệu trong cửa sổ train.

    Universe 30 mã có cold-start (vd. VPL từ 2026-03) làm panel đủ N chỉ còn vài chục ngày
    ``test``, khiến scaler không fit được (CLAUDE.md quy tắc 4). Corr feature chỉ dùng các mã đã
    xuất hiện trong ``split==train``; cube scenarios vẫn giữ đủ universe qua ``_tickers``.
    """
    universe = _tickers(config)
    if "split" not in returns.columns:
        return universe
    train = returns.loc[returns["split"] == "train"]
    present = set(train["ticker"].astype(str))
    selected = [ticker for ticker in universe if ticker in present]
    excluded = [ticker for ticker in universe if ticker not in present]
    if len(selected) < 2:
        raise ValueError(
            "Không đủ ticker có dữ liệu train để tính mean_pairwise_corr_60d "
            f"(giữ={selected}, loại={excluded})."
        )
    if excluded:
        logging.getLogger(__name__).warning(
            "Regime corr panel loại %d ticker cold-start/không có train: %s. "
            "Scenarios vẫn dùng đủ %d mã universe.",
            len(excluded),
            excluded,
            len(universe),
        )
    return selected


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
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Optional profile YAML; with --override uses Config.load_profiled",
    ),
    override: str | None = typer.Option(
        None,
        "--override",
        help="Optional Decision-package / provisional override YAML",
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Sinh dữ liệu giả từ qshield_ai.fixtures thay vì đọc nguồn thật",
    ),
) -> None:
    """Huấn luyện/suy luận Gaussian HMM → regime_daily.parquet (3 xác suất trạng thái/ngày)."""
    cfg = _load_cli_config(config, profile, override)
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
    corr_tickers = _regime_corr_tickers(cfg, returns)
    raw_frame = build_feature_frame(
        market,
        returns,
        tickers=corr_tickers,
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
        # `validate_or_raise` có `coerce=True` (RegimeDailySchema) nên frame trả về có thể lệch
        # dtype so với `daily` gốc — ghi frame ĐÃ validate, không phải bản trước khi coerce, để
        # dtype drift trong tương lai được sửa thay vì âm thầm trôi ra artifact.
        daily = validate_or_raise(
            daily, RegimeDailySchema, context="qshield_ai.regime:output"
        )
        check_probabilities_sum_to_one(daily)
        # `dev` mode ghi vào đường dẫn cố định (paths.ensure() chỉ mkdir -p, không dọn file cũ).
        # Run trước có thể đã fail cổng và để lại fallback rule-based ở đây — nếu không xóa,
        # downstream (packages/risk, backend) vẫn thấy cả hai file cùng lúc, nhập nhằng file nào
        # là champion hiện hành. Xóa TRƯỚC khi ghi validated để hai nhánh luôn loại trừ nhau.
        (stage_dir / "regime_daily_rule_based.parquet").unlink(missing_ok=True)
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
        # Đối xứng với nhánh OK: run trước có thể đã qua cổng và để lại champion thật ở đây.
        # Không xóa thì `regime_daily.parquet` của run FAIL hôm nay là artifact "ma" của một
        # run cũ đã pass cổng — đúng cái outcome fallback này phải ngăn (xem docstring module).
        (stage_dir / "regime_daily.parquet").unlink(missing_ok=True)
        fallback.to_parquet(stage_dir / "regime_daily_rule_based.parquet", index=False)
        logger.warning("Cổng HMM FAIL: %s", "; ".join(outcome.gate_reasons))

    summary = build_regime_summary(
        outcome=outcome,
        daily=daily,
        feature_names=feature_names,
        feature_version=str(cfg["feature_contract_version"]),
        run_mode=RUN_MODE_NON_BASELINE,
        data_version=str(cfg["data"]["data_version"]),
        input_source=INPUT_SOURCE_MOCK if mock else INPUT_SOURCE_REAL,
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
    if daily is None:
        # Bất biến của SelectionOutcome: champion is None ⇔ gate_status == GATE_FAILED
        # (packages/ai/src/qshield_ai/regime/selection.py). Đã loại nhánh GATE_FAILED ở trên,
        # nên tới đây `daily` luôn được build_regime_daily() dựng — None chỉ có thể là bug
        # phá vỡ bất biến đó, không phải trạng thái vận hành bình thường.
        raise RuntimeError(
            "Bất biến vỡ: gate_status == GATE_OK nhưng daily vẫn None — "
            "kiểm tra SelectionOutcome/run_selection."
        )
    print(f"[regime] OK — {len(daily)} dòng → {stage_dir}")


_INPUT_SOURCE_UNKNOWN = "unknown"


def _regime_input_source(paths: ArtifactPaths) -> str:
    """Đọc `input_source` từ `regime_summary.json` — sidecar provenance của chặng regime.

    Trả `"unknown"` khi thiếu file hoặc thiếu khóa: đó là artifact do bản CLI cũ ghi (trước khi
    có dấu vết mock/thật), và "không biết" phải được xử lý như "có thể là mock" chứ không phải
    "chắc là thật" — chính giả định lạc quan đó tạo ra lỗi này.
    """
    summary_path = paths.for_stage(Stage.REGIME, "regime_summary.json")
    if not summary_path.exists():
        return _INPUT_SOURCE_UNKNOWN
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Không đọc được {summary_path} để xác định nguồn dữ liệu của chặng regime: {exc}"
        ) from exc
    source = summary.get("input_source", _INPUT_SOURCE_UNKNOWN)
    return str(source)


def _load_regime_daily(
    paths: ArtifactPaths, *, force: bool, logger: Any, mock: bool
) -> tuple[pd.DataFrame, str, str]:
    """Đọc `regime_daily.parquet` (champion HMM); nếu cổng HMM đã FAIL thì chỉ còn
    `regime_daily_rule_based.parquet` — PR-REG-015 chặn chặng scenarios trên nhãn đó trừ khi
    `--force`. Fallback KHÔNG có `state_id`/`prob_*`/`model_version`/`seed` theo thiết kế
    (`qshield_ai.baseline.rule_based_regime`), nên không validate được bằng `RegimeDailySchema`
    — chỉ kiểm tra tối thiểu hai cột `build_block_pool`/`resolve_evaluation_date` thực sự cần.

    Trả về `(regime_daily, source, regime_input_source)` với `source` ∈ {"hmm_champion",
    "rule_based_fallback"} để ghi vào manifest — công cụ downstream cần biết run này có posterior
    HMM hay không — và `regime_input_source` ∈ {"mock", "real", "unknown"} là nguồn dữ liệu mà
    chặng regime đã dùng.
    """
    champion_path = paths.for_stage(Stage.REGIME, "regime_daily.parquet")
    fallback_path = paths.for_stage(Stage.REGIME, "regime_daily_rule_based.parquet")

    # Kiểm tra TRƯỚC khi đọc parquet, và cho cả hai nhánh champion/fallback: `--mock` ghi đè đúng
    # những đường dẫn này nên nhãn giả và nhãn thật không phân biệt được bằng tên file. Đối xứng
    # hai chiều — chạy `--mock` trên nhãn thật cũng sai như chiều ngược lại, chỉ khác là vô hại
    # hơn; cả hai đều là trộn nguồn dữ liệu trong một pipeline.
    wanted = INPUT_SOURCE_MOCK if mock else INPUT_SOURCE_REAL
    found = _regime_input_source(paths)
    if found != wanted and (champion_path.exists() or fallback_path.exists()):
        detail = (
            f"artifact regime tại {paths.stage_dir(Stage.REGIME)} có input_source={found!r} "
            f"nhưng chặng scenarios đang chạy với input_source={wanted!r}"
        )
        if found == _INPUT_SOURCE_UNKNOWN:
            detail += (
                " (artifact do bản CLI cũ ghi, không có dấu vết nguồn — chạy lại "
                "`qshield-ai regime` để đóng dấu)"
            )
        if not force:
            raise typer.BadParameter(
                f"{detail}. Trộn nguồn dữ liệu giữa hai chặng cho ra cube trông hợp lệ nhưng "
                f"vô nghĩa. Chạy lại `qshield-ai regime`"
                f"{' --mock' if mock else ''} trước, hoặc dùng --force để chạy có chủ ý."
            )
        logger.warning(
            "%s — tiếp tục vì --force. Kết quả KHÔNG dùng làm bằng chứng.", detail
        )

    if champion_path.exists():
        regime_daily = pd.read_parquet(champion_path)
        regime_daily = validate_or_raise(
            regime_daily, RegimeDailySchema, context="qshield_ai.scenarios:input.regime"
        )
        return regime_daily, "hmm_champion", found

    if fallback_path.exists():
        if not force:
            raise typer.BadParameter(
                f"Chưa có {champion_path} — cổng HMM đã FAIL ở chặng regime, chỉ còn "
                f"{fallback_path.name} (rule-based, KHÔNG có posterior). PR-REG-015 chặn "
                "scenarios điều kiện hóa trên nhãn đó. Dùng --force để chạy có chủ ý."
            )
        logger.warning(
            "Dùng regime fallback rule-based (%s) vì --force — nhãn này KHÔNG có posterior HMM.",
            fallback_path.name,
        )
        regime_daily = pd.read_parquet(fallback_path)
        missing = {"date", "regime"} - set(regime_daily.columns)
        if missing:
            raise ValueError(
                f"{fallback_path} thiếu cột {sorted(missing)} — không đủ để điều kiện hóa."
            )
        return regime_daily, "rule_based_fallback", found

    raise typer.BadParameter(
        f"Chưa có {champion_path} lẫn {fallback_path} — chạy `qshield-ai regime` trước "
        "(PR-REG-015: không có model hợp lệ thì chặn scenario conditioning)."
    )


@app.command()
def scenarios(
    config: str = typer.Option(
        "configs/base.yaml", "--config", help="Đường dẫn config"
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Optional profile YAML; with --override uses Config.load_profiled",
    ),
    override: str | None = typer.Option(
        None,
        "--override",
        help="Optional Decision-package / provisional override YAML",
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Sinh dữ liệu giả từ qshield_ai.fixtures thay vì đọc nguồn thật",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Ghi cube kể cả khi quality gate FAIL, hoặc chạy trên regime fallback rule-based "
        "— run vẫn bị đánh dấu NON_BASELINE",
    ),
) -> None:
    """Sinh kịch bản stress bằng regime-conditioned moving-block bootstrap → stress_scenarios."""
    cfg = _load_cli_config(config, profile, override)
    paths = ArtifactPaths(cfg, run_id=_resolve_run_id(cfg))
    context = RunContext(cfg, paths)
    logger = context.logger("scenarios")
    paths.ensure(Stage.SCENARIOS)
    stage_dir = paths.stage_dir(Stage.SCENARIOS)

    # Dọn artifact của CHÍNH chặng này TRƯỚC mọi thứ có thể raise (đọc regime, pool rỗng, cổng
    # FAIL). `dev` mode ghi vào đường dẫn cố định và `paths.ensure()` chỉ mkdir -p, nên nếu thoát
    # sớm mà không dọn, cả bộ artifact của run TRƯỚC vẫn nằm nguyên: cube + manifest ghi
    # `gate_status: PASS` + validation.csv, trông y hệt kết quả của hôm nay. Một artifact cũ còn
    # sót nguy hiểm hơn hẳn không có artifact nào — Risk phía sau đọc phải cube chưa từng qua
    # chặng này mà không có cách nào biết. Sau lệnh này, mọi đường thoát đều để lại thư mục sạch.
    for stale in (
        "stress_scenarios.npz",
        "scenario_manifest.json",
        "scenario_validation.csv",
        "scenarios_by_regime.npz",
    ):
        (stage_dir / stale).unlink(missing_ok=True)

    regime_daily, regime_source, regime_input_source = _load_regime_daily(
        paths, force=force, logger=logger, mock=mock
    )

    returns, market = _load_inputs(cfg, mock=mock)
    validate_or_raise(
        returns, ReturnsSchema, context="qshield_ai.scenarios:input.returns"
    )
    validate_or_raise(
        market,
        MarketFeaturesSchema,
        context="qshield_ai.scenarios:input.market_features",
    )
    tickers = _tickers(cfg)
    # Lịch phiên VN-Index thật (market_features), KHÔNG suy từ union ngày trong returns: một mã
    # thiếu phiên do returns không được phép làm "khoảng trống" biến mất khỏi lịch — nếu vậy luật
    # "block không thể nối qua khoảng trống" (bootstrap.py) trở thành vô nghĩa với đúng những
    # ngày cần bắt.
    calendar = sorted(
        pd.to_datetime(market.loc[market["split"] != "out_of_scope", "date"]).unique()
    )
    panel = build_return_panel(returns, calendar, tickers=tickers)

    evaluation_date = resolve_evaluation_date(
        regime_daily, panel, configured=cfg.get("evaluation_date")
    )
    last_position = list(panel.dates).index(evaluation_date)
    target_regime = str(
        regime_daily.loc[
            pd.to_datetime(regime_daily["date"]) == evaluation_date, "regime"
        ].iloc[0]
    )
    logger.info(
        "Ngày đánh giá t=%s, regime mục tiêu=%s", evaluation_date.date(), target_regime
    )

    num_scenarios = int(cfg["num_scenarios"])
    horizon_days = int(cfg["horizon_days"])
    block_length = int(cfg["block_length"])
    thresholds = cfg["validation"]["thresholds"]
    min_reference_windows = int(cfg["validation"]["min_reference_windows"])
    base_seed = int(cfg["scenario_seed"])

    cubes: dict[str, np.ndarray] = {}
    reports: list[pd.DataFrame] = []
    metadata_by_regime: dict[str, dict[str, Any]] = {}
    skipped: dict[str, str] = {}

    for offset, regime_name in enumerate(_REGIME_ORDER):
        pool = build_block_pool(
            panel,
            regime_daily,
            target_regime=regime_name,
            block_length=block_length,
            evaluation_date=evaluation_date,
        )
        if pool.eligible_block_count == 0:
            skipped[regime_name] = f"pool rỗng, lý do loại: {pool.rejected}"
            logger.warning("Bỏ qua regime %s: %s", regime_name, skipped[regime_name])
            continue

        simple, log_cube, meta = generate_cube(
            panel,
            pool,
            num_scenarios=num_scenarios,
            horizon_days=horizon_days,
            block_length=block_length,
            seed=base_seed + offset,
        )
        reference = reference_windows(
            panel, pool, horizon_days=horizon_days, last_position=last_position
        )
        if reference.size == 0:
            skipped[regime_name] = "không có cửa sổ tham chiếu để kiểm định"
            logger.warning("Bỏ qua regime %s: %s", regime_name, skipped[regime_name])
            continue

        cubes[regime_name] = simple
        cubes[f"{regime_name}_log"] = log_cube
        metadata_by_regime[regime_name] = meta
        reports.append(
            build_validation_report(
                log_cube,
                reference,
                thresholds=thresholds,
                target_regime=regime_name,
                min_reference_windows=min_reference_windows,
            )
        )

    if target_regime not in metadata_by_regime:
        raise typer.BadParameter(
            f"Không sinh được cube cho regime mục tiêu {target_regime!r}: "
            f"{skipped.get(target_regime, 'lý do không xác định')}"
        )

    report = pd.concat(reports, ignore_index=True)
    report.to_csv(stage_dir / "scenario_validation.csv", index=False)

    primary_simple = cubes[target_regime]
    primary_log = cubes[f"{target_regime}_log"]
    structural = structural_violations(
        primary_simple,
        expected_shape=(num_scenarios, horizon_days, len(tickers)),
        tickers=tickers,
    )
    distribution_gate = gate_status(
        report.loc[report["target_regime"] == target_regime]
    )
    status = SCENARIO_GATE_FAIL if structural else distribution_gate

    # `dict[str, Any]` (không phải `dict[str, np.ndarray]`) trước khi splat: numpy-stubs khớp sai
    # overload của `savez_compressed(file, *args, allow_pickle=..., **kwds)` khi `**kwds` mang kiểu
    # `ndarray` cụ thể, báo "expected bool" — false positive đã xác minh, không phải lỗi thật.
    by_regime_arrays: dict[str, Any] = {"ticker_order": np.array(tickers), **cubes}
    np.savez_compressed(stage_dir / "scenarios_by_regime.npz", **by_regime_arrays)

    # Fallback rule-based (regime_source == "rule_based_fallback") không có posterior HMM để lọc —
    # "hard_filtered_label" chỉ đúng cho nhãn Viterbi/filtered của champion. Gán cứng một chuỗi cho
    # cả hai nhánh khiến manifest tự mâu thuẫn: vừa nói "lọc theo posterior" vừa nói "fallback"
    # trong cùng một file. Suy ra chuỗi từ `regime_source` để hai trường không bao giờ lệch nhau.
    conditioning_method = (
        "rule_based_threshold_label"
        if regime_source == "rule_based_fallback"
        else "hard_filtered_label"
    )

    manifest: dict[str, Any] = {
        "run_mode": RUN_MODE_NON_BASELINE,
        "run_id": context.run_id,
        "gate_status": status,
        "forced": bool(force),
        # Hai trường tách nhau vì `--force` cho phép chúng lệch: `input_source` là nguồn của
        # chính run scenarios này, `regime_input_source` là nguồn của nhãn regime nó đã tiêu thụ.
        # Gộp thành một trường sẽ giấu mất đúng trường hợp cần điều tra.
        "input_source": INPUT_SOURCE_MOCK if mock else INPUT_SOURCE_REAL,
        "regime_input_source": regime_input_source,
        "regime_source": regime_source,
        "structural_violations": structural,
        "evaluation_date": str(evaluation_date.date()),
        "target_regime": target_regime,
        "return_type": "simple",
        "return_type_note": (
            "scenarios = simple daily returns; scenarios_log = log daily returns; "
            "simple = expm1(log). R^(H) mỗi tài sản = prod(1+r) - 1 trên 20 ngày."
        ),
        "ticker_order": list(tickers),
        "num_scenarios": num_scenarios,
        "horizon_days": horizon_days,
        "block_length": block_length,
        "seed": base_seed,
        "conditioning_method": conditioning_method,
        "data_version": str(cfg["data"]["data_version"]),
        "feature_version": str(cfg["feature_contract_version"]),
        "primary": metadata_by_regime[target_regime],
        "by_regime": metadata_by_regime,
        "skipped_regimes": skipped,
        "validation_reference": str(cfg["validation"]["reference"]),
        "unresolved_decisions": list(UNRESOLVED_DECISIONS),
    }
    _write_json(stage_dir / "scenario_manifest.json", manifest)

    context.write_config_snapshot()
    context.write_data_version(str(cfg["data"]["data_version"]))
    context.write_metrics(
        {
            "stage": "scenarios",
            "gate_status": status,
            "forced": bool(force),
            "regime_source": regime_source,
            "target_regime": target_regime,
            "evaluation_date": str(evaluation_date.date()),
            "eligible_block_count": metadata_by_regime[target_regime][
                "eligible_block_count"
            ],
            "reuse_rate": metadata_by_regime[target_regime]["reuse_rate"],
        }
    )

    if status == SCENARIO_GATE_FAIL and not force:
        # Không cần xóa `stress_scenarios.npz` ở đây: nhánh này chưa từng ghi nó, và bản của run
        # trước đã bị dọn ngay đầu lệnh. Bằng chứng của lần FAIL này (manifest + validation.csv)
        # vẫn ở lại vì chúng vừa được ghi phía trên.
        print(
            f"[scenarios] GATE FAIL — cube KHÔNG được ghi. "
            f"Xem {stage_dir / 'scenario_validation.csv'}. Dùng --force để ghi có chủ ý."
        )
        raise typer.Exit(code=1)

    validate_scenarios(
        primary_simple,
        ScenarioMetadata(
            seed=base_seed,
            regime_conditioned_on=target_regime,
            block_length=block_length,
            num_scenarios=num_scenarios,
            horizon_days=horizon_days,
            n_assets=len(tickers),
            validation=distribution_metrics(primary_log),
        ),
    )
    np.savez_compressed(
        stage_dir / "stress_scenarios.npz",
        scenarios=primary_simple,
        scenarios_log=primary_log,
        ticker_order=np.array(tickers),
    )
    print(
        f"[scenarios] {status} — cube {primary_simple.shape} regime={target_regime} "
        f"t={evaluation_date.date()} → {stage_dir}"
    )


if __name__ == "__main__":
    app()
