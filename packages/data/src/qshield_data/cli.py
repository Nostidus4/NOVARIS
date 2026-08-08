# Nguyễn Đỗ Minh Anh - CLI `uv run qshield-data build` → data/processed/*.parquet.
"""CLI orchestration cho `qshield_data` — port từ `CLEAN.ipynb` (8 bước).

Đây là nơi DUY NHẤT trong package được phép `print()`/`typer.echo()` (CLAUDE.md: "print chỉ trong
cli.py") và gọi `qshield_contracts.config.Config.load` (mọi hàm logic khác nhận tham số tường minh).

Lệnh chính là `build` — khớp với những gì `docs/architecture/pipeline.md`, `docs/runbook/setup.md`
và scaffold gốc của file này đã ghi (`uv run qshield-data build`), CHỨ KHÔNG theo tên lệnh
`fetch/clean/features/.../all` mà `plan.md` §5 đề xuất ban đầu — plan.md được viết trước khi đối
chiếu với các doc đã commit khác, nên ở đây ưu tiên cái đã có tài liệu tham chiếu. `build` chạy
tuần tự đúng 7 bước plan.md mô tả; các bước đó cũng được expose thành subcommand riêng
(`fetch/clean/features/eligibility/split/quality/manifest`) để chạy/debug từng bước lúc phát triển.
"""

from __future__ import annotations

import importlib.metadata
import json
import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import typer
import yfinance as yf
from qshield_contracts.config import Config

from qshield_data import eligibility as eligibility_mod
from qshield_data import features as features_mod
from qshield_data import returns as returns_mod
from qshield_data import split as split_mod
from qshield_data.clean import corporate_actions, normalize, validate_prices
from qshield_data.manifest import build_manifest, write_manifest
from qshield_data.quality import checks as checks_mod
from qshield_data.quality import evidence as evidence_mod
from qshield_data.quality import report as report_mod
from qshield_data.quality.price_limits import find_price_limit_violations
from qshield_data.sources import fetch as fetch_mod
from qshield_data.sources import registry

app = typer.Typer(help="Q-SHIELD Data Pipeline CLI.")
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=FutureWarning)

_CONFIG_OPTION = typer.Option(
    "configs/base.yaml", "--config", help="Đường dẫn configs/base.yaml"
)
_PROFILE_OPTION = typer.Option(
    None,
    "--profile",
    help="Optional profile YAML; with --override uses Config.load_profiled",
)
_OVERRIDE_OPTION = typer.Option(
    None,
    "--override",
    help="Optional Decision-package / provisional override YAML",
)


class _Paths:
    """Đường dẫn suy ra từ `configs/base.yaml['paths']` — glue code của CLI, không phải
    `ArtifactPaths` (đó là cho `artifacts/runs/...`, xem CLAUDE.md quy tắc 8)."""

    def __init__(self, config: dict[str, Any]) -> None:
        paths_cfg = config.get("paths", {}) or {}
        self.data_root = Path(paths_cfg.get("data_root", "data"))
        self.reports_root = Path(paths_cfg.get("reports_root", "reports"))
        self.raw_dir = self.data_root / "raw"
        self.processed_dir = self.data_root / "processed"
        self.metadata_dir = self.data_root / "metadata"

    def ensure(self) -> None:
        for d in [
            self.raw_dir / "prices",
            self.raw_dir / "vn_index",
            self.processed_dir,
            self.metadata_dir,
            self.reports_root,
        ]:
            d.mkdir(parents=True, exist_ok=True)


def _run_id() -> str:
    return f"data_run_{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}"


def _load_config(
    config: Path,
    profile: Path | None = None,
    override: Path | None = None,
) -> dict[str, Any]:
    if profile is not None or override is not None:
        cfg = Config.load_profiled(
            config,
            profile or Path("configs/workflow_update.yaml"),
            Path(override) if override else None,
        )
    else:
        cfg = Config.load(config)
    level = ((cfg.get("logging") or {}).get("level")) or "INFO"
    logging.basicConfig(level=getattr(logging, str(level).upper(), logging.INFO))
    return cfg


def _raw_manifest_path(paths: _Paths) -> Path:
    # File cố định (không version theo run_id) — data/ chỉ giữ MỘT bộ "chính thức" tại một thời
    # điểm, khác artifacts/runs/ (xem comment trong configs/base.yaml).
    return paths.metadata_dir / "raw_manifest.csv"


def _vn_index_meta_path(paths: _Paths) -> Path:
    return paths.raw_dir / "vn_index" / "vn_index_meta.json"


def _load_latest_vn_index(paths: _Paths) -> pd.DataFrame | None:
    """Đọc lại VN-Index đã tải (CSV mới nhất trong `raw_dir/vn_index/`), hoặc `None` nếu chưa có."""
    candidates = sorted((paths.raw_dir / "vn_index").glob("*_vnindex.csv"))
    if not candidates:
        return None
    df = pd.read_csv(candidates[-1], parse_dates=["date"])
    return df.set_index("date")


def _load_vn_index_source_tag(paths: _Paths) -> str | None:
    meta_path = _vn_index_meta_path(paths)
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    symbol, source = meta.get("symbol_used"), meta.get("source_used")
    if not symbol or not source:
        return None
    return f"{source}_{symbol}"


def _vnstock_version() -> str:
    try:
        return importlib.metadata.version("vnstock")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


# ---------------------------------------------------------------------------
# Bước 1-2: fetch
# ---------------------------------------------------------------------------
@app.command()
def fetch(
    config: Path = _CONFIG_OPTION,
    profile: Path | None = _PROFILE_OPTION,
    override: Path | None = _OVERRIDE_OPTION,
) -> None:
    """Bước 1-2: đọc universe, tải giá từ Yahoo/DNSE/vnstock vào data/raw/."""
    cfg = _load_config(config, profile, override)
    paths = _Paths(cfg)
    paths.ensure()

    universe = registry.load_universe(cfg)
    date_range = cfg["date_range"]
    start = date_range[
        "market_train_start"
    ]  # sớm nhất trong 2 đồng hồ — dùng chung cho fetch
    end = date_range["test_end"]

    typer.echo(f"Downloading {len(universe)} tickers from {start} to {end}...")
    raw_manifest = fetch_mod.fetch_all_prices(
        universe, start=start, end=end, raw_dir=paths.raw_dir
    )
    typer.echo(raw_manifest["status"].value_counts().to_string())
    raw_manifest.to_csv(_raw_manifest_path(paths), index=False, encoding="utf-8-sig")

    index_df, symbol_used, source_used = fetch_mod.fetch_vn_index(
        start=start, end=end, raw_dir=paths.raw_dir
    )
    _vn_index_meta_path(paths).write_text(
        json.dumps(
            {"symbol_used": symbol_used, "source_used": source_used}, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    if index_df is None:
        typer.echo(
            "⚠ VN-Index unavailable — features step sẽ tự tính custom composite."
        )

    data_cfg = cfg.get("data", {})
    sources_df = registry.build_source_register(
        access_date=datetime.now().astimezone().strftime("%Y-%m-%d"),
        yfinance_version=yf.__version__,
        vnstock_version=_vnstock_version(),
        test_end=end,
    )
    universe_path, sources_path = registry.save_universe_and_sources(
        universe,
        sources_df,
        paths.metadata_dir,
        universe_as_of=data_cfg.get("universe_as_of", ""),
    )
    typer.echo(f"✓ Saved universe: {universe_path}")
    typer.echo(f"✓ Saved source register: {sources_path}")


# ---------------------------------------------------------------------------
# Bước 3: clean
# ---------------------------------------------------------------------------
@app.command()
def clean(
    config: Path = _CONFIG_OPTION,
    profile: Path | None = _PROFILE_OPTION,
    override: Path | None = _OVERRIDE_OPTION,
) -> None:
    """Bước 3: normalize + dedup + phantom-day + pre-listing → data/processed/prices_adjusted.parquet."""
    cfg = _load_config(config, profile, override)
    paths = _Paths(cfg)
    paths.ensure()

    raw_manifest_path = _raw_manifest_path(paths)
    if not raw_manifest_path.exists():
        typer.echo(
            f"✗ Chưa có {raw_manifest_path} — chạy `qshield-data fetch` trước.",
            err=True,
        )
        raise typer.Exit(code=1)
    raw_manifest = pd.read_csv(raw_manifest_path)

    universe = registry.load_universe(cfg)
    data_version = cfg.get("data", {}).get("data_version", "v0.0.0")

    prices = normalize.load_and_normalize(raw_manifest, data_version=data_version)
    typer.echo(
        f"Loaded raw: {len(prices):,} rows, {prices['ticker'].nunique()} tickers"
    )

    registered_actions = cfg.get("corporate_actions") or []
    if registered_actions:
        prices = corporate_actions.apply_registered_adjustments(
            prices, registered_actions
        )
        typer.echo(
            f"Corporate action back-adjustment: {len(registered_actions)} entry đã đăng ký "
            "(configs/base.yaml) — xem logs.txt để biết đúng bao nhiêu phiên bị đổi."
        )

    prices, n_dup = validate_prices.dedup_prices(prices)
    typer.echo(f"Duplicates removed: {n_dup}")

    vn_index = _load_latest_vn_index(paths)
    prices, n_phantom = validate_prices.remove_yahoo_phantom_days(prices, vn_index)
    typer.echo(f"Phantom Yahoo days removed: {n_phantom}")

    prices = validate_prices.flag_price_quality(prices)
    typer.echo(prices["quality_flag"].value_counts().to_string())

    prices = corporate_actions.remove_pre_listing(prices, universe)
    prices = prices.sort_values(["ticker", "date"]).reset_index(drop=True)

    out_path = paths.processed_dir / "prices_adjusted.parquet"
    prices.to_parquet(out_path, index=False)
    typer.echo(
        f"✓ Saved: {out_path} — {len(prices):,} rows | {prices['ticker'].nunique()} tickers | "
        f"{prices['date'].min().date()} → {prices['date'].max().date()}"
    )


# ---------------------------------------------------------------------------
# Bước 4: features
# ---------------------------------------------------------------------------
@app.command()
def features(
    config: Path = _CONFIG_OPTION,
    profile: Path | None = _PROFILE_OPTION,
    override: Path | None = _OVERRIDE_OPTION,
) -> None:
    """Bước 4: tính returns + market features → data/processed/{returns,market_features}.parquet."""
    cfg = _load_config(config, profile, override)
    paths = _Paths(cfg)
    paths.ensure()

    prices_path = paths.processed_dir / "prices_adjusted.parquet"
    if not prices_path.exists():
        typer.echo(
            f"✗ Chưa có {prices_path} — chạy `qshield-data clean` trước.", err=True
        )
        raise typer.Exit(code=1)
    prices = pd.read_parquet(prices_path)

    returns = returns_mod.compute_asset_returns(prices)
    returns_out = paths.processed_dir / "returns.parquet"
    returns.to_parquet(returns_out, index=False)
    typer.echo(f"✓ Saved returns: {returns_out} — {len(returns):,} rows")

    index_df = _load_latest_vn_index(paths)
    index_source_tag = _load_vn_index_source_tag(paths)
    market = features_mod.build_market_features(index_df, returns, index_source_tag)

    market_out = paths.processed_dir / "market_features.parquet"
    market.to_parquet(market_out, index=False)
    typer.echo(f"✓ Saved market features: {market_out} — {len(market):,} rows")


# ---------------------------------------------------------------------------
# Bước 5: eligibility
# ---------------------------------------------------------------------------
@app.command()
def eligibility(
    config: Path = _CONFIG_OPTION,
    profile: Path | None = _PROFILE_OPTION,
    override: Path | None = _OVERRIDE_OPTION,
) -> None:
    """Bước 5: build eligibility_daily.parquet."""
    cfg = _load_config(config, profile, override)
    paths = _Paths(cfg)
    paths.ensure()

    prices_path = paths.processed_dir / "prices_adjusted.parquet"
    if not prices_path.exists():
        typer.echo(
            f"✗ Chưa có {prices_path} — chạy `qshield-data clean` trước.", err=True
        )
        raise typer.Exit(code=1)
    prices = pd.read_parquet(prices_path)
    universe = registry.load_universe(cfg)
    elig_cfg = cfg.get("eligibility", {})

    elig_df = eligibility_mod.build_eligibility(
        prices,
        universe,
        min_history_sessions=cfg["min_history_sessions"],
        min_coverage_pct=elig_cfg["min_coverage_pct"],
        min_turnover_20d_vnd=elig_cfg["min_turnover_20d_vnd"],
    )
    typer.echo(f"Eligibility rows: {len(elig_df):,}")
    typer.echo(elig_df["reason_code"].value_counts().to_string())

    out_path = paths.processed_dir / "eligibility_daily.parquet"
    elig_df.to_parquet(out_path, index=False)
    typer.echo(f"✓ Saved: {out_path}")


# ---------------------------------------------------------------------------
# Bước 6: split
# ---------------------------------------------------------------------------
@app.command()
def split(
    config: Path = _CONFIG_OPTION,
    profile: Path | None = _PROFILE_OPTION,
    override: Path | None = _OVERRIDE_OPTION,
) -> None:
    """Bước 6: gán cột split (train/validation/test) cho returns & market_features."""
    cfg = _load_config(config, profile, override)
    paths = _Paths(cfg)
    paths.ensure()
    date_range = cfg["date_range"]

    returns_path = paths.processed_dir / "returns.parquet"
    market_path = paths.processed_dir / "market_features.parquet"
    for p in (returns_path, market_path):
        if not p.exists():
            typer.echo(f"✗ Chưa có {p} — chạy `qshield-data features` trước.", err=True)
            raise typer.Exit(code=1)

    returns = pd.read_parquet(returns_path)
    returns["date"] = pd.to_datetime(returns["date"])
    returns = split_mod.apply_splits(returns, level="asset", splits_config=date_range)
    returns.to_parquet(returns_path, index=False)
    typer.echo("Asset-level split:\n" + returns["split"].value_counts().to_string())

    market = pd.read_parquet(market_path)
    market["date"] = pd.to_datetime(market["date"])
    market = split_mod.apply_splits(market, level="market", splits_config=date_range)
    market.to_parquet(market_path, index=False)
    typer.echo("\nMarket-level split:\n" + market["split"].value_counts().to_string())


# ---------------------------------------------------------------------------
# Bước 7: quality
# ---------------------------------------------------------------------------
@app.command()
def quality(
    config: Path = _CONFIG_OPTION,
    profile: Path | None = _PROFILE_OPTION,
    override: Path | None = _OVERRIDE_OPTION,
) -> bool:
    """Bước 7: chạy Data Quality Gate → reports/data_quality_report.csv."""
    cfg = _load_config(config, profile, override)
    paths = _Paths(cfg)
    paths.ensure()

    prices_path = paths.processed_dir / "prices_adjusted.parquet"
    returns_path = paths.processed_dir / "returns.parquet"
    for p in (prices_path, returns_path):
        if not p.exists():
            typer.echo(f"✗ Chưa có {p} — chạy các bước trước đó.", err=True)
            raise typer.Exit(code=1)

    prices = pd.read_parquet(prices_path)
    returns = pd.read_parquet(returns_path)
    universe = registry.load_universe(cfg)
    expected_count = cfg.get("expected_ticker_count", len(universe))

    try:
        price_limits_cfg = cfg["price_limits"]
        bands = price_limits_cfg["bands_by_exchange"]
        tolerance = price_limits_cfg["tolerance_pct"]
    except (KeyError, TypeError) as exc:
        # KeyError: thiếu hẳn khóa (vd. không có `price_limits` hoặc không có `bands_by_exchange`).
        # TypeError: khóa có mặt nhưng không phải mapping (vd. `price_limits: 0.07` — một số vô
        # tình được viết ở chỗ lẽ ra phải là section — thì `price_limits_cfg["bands_by_exchange"]`
        # không raise KeyError mà raise TypeError vì không subscript được bằng chuỗi).
        typer.echo(
            f"✗ configs/base.yaml (price_limits) thiếu khóa hoặc sai kiểu: {exc} — "
            "không chạy được DQ-007. Cần price_limits.bands_by_exchange (mapping) và "
            "price_limits.tolerance_pct (số).",
            err=True,
        )
        raise typer.Exit(code=1) from exc

    violations = find_price_limit_violations(
        returns,
        universe,
        bands_by_exchange=bands,
        tolerance_pct=tolerance,
    )

    report_df, all_pass = checks_mod.run_all_checks(
        prices, universe, returns, expected_count, violations
    )
    typer.echo(report_df.to_string(index=False))
    typer.echo(
        "✅ DATA QUALITY GATE: PASS" if all_pass else "❌ DATA QUALITY GATE: FAIL"
    )

    out_path = paths.reports_root / "data_quality_report.csv"
    report_mod.write_quality_report(report_df, out_path)
    typer.echo(f"✓ DQ report: {out_path}")

    evidence_frame = evidence_mod.build_adjusted_close_evidence_report(
        universe, cfg.get("corporate_actions") or []
    )
    evidence_path = paths.reports_root / "adjusted_close_evidence_report.csv"
    evidence_mod.write_adjusted_close_evidence_report(evidence_frame, evidence_path)
    verified = int(evidence_frame["evidence_flag"].eq("ADJ_REGISTERED").sum())
    typer.echo(
        f"✓ Adjusted-close evidence: {evidence_path} — "
        f"{verified}/{len(evidence_frame)} ADJ_REGISTERED; "
        "baseline_ok=False until Data Gate sign-off (TL-002)."
    )

    violations_path = paths.reports_root / "price_limit_violations.csv"
    report_mod.write_violations(violations, violations_path)
    if len(violations):
        typer.echo(
            f"⚠️  DQ-007: {len(violations)} phiên vượt biên độ sàn — xem {violations_path}"
        )
        typer.echo(violations.head(5).to_string(index=False))
    else:
        typer.echo(f"✓ DQ-007: không có phiên nào vượt biên độ — {violations_path}")
    return all_pass


# ---------------------------------------------------------------------------
# Bước 8: manifest
# ---------------------------------------------------------------------------
@app.command()
def manifest(
    config: Path = _CONFIG_OPTION,
    profile: Path | None = _PROFILE_OPTION,
    override: Path | None = _OVERRIDE_OPTION,
) -> None:
    """Bước 8: build data_dictionary.xlsx + data_manifest.json."""
    cfg = _load_config(config, profile, override)
    paths = _Paths(cfg)
    paths.ensure()
    data_cfg = cfg.get("data", {})
    date_range = cfg["date_range"]

    dict_out = paths.metadata_dir / "data_dictionary.xlsx"
    report_mod.build_data_dictionary(dict_out)
    typer.echo(f"✓ Data Dictionary: {dict_out}")

    universe_files = sorted(paths.metadata_dir.glob("universe_30_asof_*.csv"))
    if not universe_files:
        universe_files = sorted(paths.metadata_dir.glob("universe_asof_*.csv"))
    universe_register_path = (
        universe_files[-1]
        if universe_files
        else paths.metadata_dir / "universe_30_asof_MISSING.csv"
    )
    files = {
        "universe_register": universe_register_path,
        "source_register": paths.metadata_dir / "source_register.csv",
        "prices_adjusted": paths.processed_dir / "prices_adjusted.parquet",
        "returns": paths.processed_dir / "returns.parquet",
        "market_features": paths.processed_dir / "market_features.parquet",
        "eligibility_daily": paths.processed_dir / "eligibility_daily.parquet",
        "data_dictionary": dict_out,
        "data_quality_report": paths.reports_root / "data_quality_report.csv",
        "adjusted_close_evidence_report": paths.reports_root
        / "adjusted_close_evidence_report.csv",
        "price_limit_violations": paths.reports_root / "price_limit_violations.csv",
    }

    row_counts = {}
    for name in ("prices_adjusted", "returns", "market_features", "eligibility_daily"):
        p = files[name]
        row_counts[name] = len(pd.read_parquet(p)) if p.exists() else 0
    universe = registry.load_universe(cfg)
    row_counts["universe"] = len(universe)

    dq_path = files["data_quality_report"]
    quality_gate_pass = False
    if dq_path.exists():
        dq_df = pd.read_csv(dq_path)
        must_pass = dq_df[dq_df["type"] == "MUST_PASS"]
        quality_gate_pass = bool((must_pass["status"] == "PASS").all())

    manifest_dict = build_manifest(
        run_id=_run_id(),
        data_version=data_cfg.get("data_version", "v0.0.0"),
        universe_version=data_cfg.get("universe_version", "v0.0"),
        universe_as_of=data_cfg.get("universe_as_of", ""),
        files=files,
        row_counts=row_counts,
        splits_config={
            "market": {
                "train": [
                    date_range["market_train_start"],
                    date_range["market_train_end"],
                ],
                "validation": [
                    date_range["validation_start"],
                    date_range["validation_end"],
                ],
                "test": [date_range["test_start"], date_range["test_end"]],
            },
            "asset": {
                "train": [
                    date_range["asset_train_start"],
                    date_range["asset_train_end"],
                ],
                "validation": [
                    date_range["validation_start"],
                    date_range["validation_end"],
                ],
                "test": [date_range["test_start"], date_range["test_end"]],
            },
        },
        eligibility_config={
            "min_history_sessions": cfg.get("min_history_sessions"),
            **cfg.get("eligibility", {}),
        },
        quality_gate_pass=quality_gate_pass,
        index_symbol_used=None,
        index_source_used=None,
        data_root=paths.data_root,
    )
    manifest_out = paths.metadata_dir / "data_manifest.json"
    write_manifest(manifest_dict, manifest_out)
    typer.echo(f"✓ Data Manifest: {manifest_out}")


# ---------------------------------------------------------------------------
# `build` — lệnh chính, khớp docs/architecture/pipeline.md + docs/runbook/setup.md
# ---------------------------------------------------------------------------
@app.command()
def build(
    config: Path = _CONFIG_OPTION,
    profile: Path | None = _PROFILE_OPTION,
    override: Path | None = _OVERRIDE_OPTION,
) -> None:
    """Thu thập, làm sạch dữ liệu, tạo feature và ghi returns.parquet / features.parquet.

    Chạy tuần tự 7 bước: fetch → clean → features → eligibility → split → quality → manifest.
    """
    fetch(config, profile=profile, override=override)
    clean(config, profile=profile, override=override)
    features(config, profile=profile, override=override)
    eligibility(config, profile=profile, override=override)
    split(config, profile=profile, override=override)
    all_pass = quality(config, profile=profile, override=override)
    manifest(config, profile=profile, override=override)

    if not all_pass:
        typer.echo(
            "⚠ Data Quality Gate FAIL — xem reports/data_quality_report.csv trước khi bàn giao "
            "cho Tú/Phúc (CLAUDE.md quy tắc BR-020: không phát hành khi quality gate fail).",
            err=True,
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
