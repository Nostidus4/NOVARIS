# Đỗ Ngọc Tân - chọn portfolio-date instance theo luật khóa trước và dựng input point-in-time.
"""Instance = (portfolio archetype, as-of date t) + regime filtered tại t + scenario cube bootstrap.

Luật chọn ngày (khóa trong config, không nhìn kết quả): trong mỗi regime và split đã đăng ký, lấy
các ngày có nhãn filtered = regime và ``prob_<regime> >= min_regime_probability``; tham lam giữ
ngày cách ngày đã giữ trước ít nhất ``min_gap_sessions`` phiên; nếu dư, lấy đều theo
``linspace``. Thiếu ngày ⇒ ghi shortfall, cho phép tối đa ``max_portfolios_per_date`` portfolio
trên cùng ngày (cờ ``shared_date``) — không bao giờ tự hạ ngưỡng.

Point-in-time: universe = mã VN30 snapshot có dữ liệu từ ``universe_lookback_start``; eligibility,
volatility, turnover đều chỉ dùng dữ liệu ``<= t``; block bootstrap chỉ nối các phiên ``<= t``.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from qshield_ai.scenarios.bootstrap import (
    build_block_pool,
    build_return_panel,
    generate_cube,
    resolve_evaluation_date,
)
from qshield_ai.scenarios.validate import (
    build_validation_report,
    gate_status,
    reference_windows,
)
from qshield_contracts.enums import ArtifactMode, Stage
from qshield_contracts.hashing import array_hash, stable_hash
from qshield_contracts.paths import ArtifactPaths
from qshield_contracts.schemas.hybrid import (
    manifest_instances_hash,
    validate_hybrid_manifest,
)

from qshield_pipeline.hybrid.settings import HybridSettings


class InstanceSkipped(RuntimeError):
    """Instance không dựng được theo luật đã đăng ký (ghi vào attempts, không âm thầm bỏ)."""


@dataclass(frozen=True)
class HybridData:
    returns: pd.DataFrame
    calendar: tuple[pd.Timestamp, ...]
    regime_daily: pd.DataFrame
    eligibility: pd.DataFrame
    snapshot_tickers: tuple[str, ...]
    data_version: str


@dataclass(frozen=True)
class InstanceInputs:
    instance: dict[str, Any]
    scenarios: np.ndarray
    tickers: tuple[str, ...]
    weights: dict[str, float]
    cash_weight: float
    eligibility: dict[str, bool]
    ineligible_reasons: dict[str, str]
    config: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


def load_hybrid_data(config: Mapping[str, Any], settings: HybridSettings) -> HybridData:
    processed = Path(str(config["paths"]["data_root"])) / "processed"
    returns = pd.read_parquet(processed / "returns.parquet")
    market = pd.read_parquet(processed / "market_features.parquet")
    eligibility = pd.read_parquet(processed / "eligibility_daily.parquet")
    mode = ArtifactMode(
        str((settings.raw.get("inputs") or {}).get("regime_artifact_mode", "dev"))
    )
    regime_paths = ArtifactPaths(
        {"artifacts": {"mode": str(mode), "root": config["artifacts"]["root"]}},
        run_id=(settings.raw.get("inputs") or {}).get("regime_run_id"),
    )
    regime_daily = pd.read_parquet(
        regime_paths.for_stage(Stage.REGIME, "regime_daily.parquet")
    )
    regime_daily = regime_daily.assign(date=pd.to_datetime(regime_daily["date"]))
    calendar = tuple(
        sorted(
            pd.to_datetime(
                market.loc[market["split"] != "out_of_scope", "date"]
            ).unique()
        )
    )
    returns = returns.assign(date=pd.to_datetime(returns["date"]))
    eligibility = eligibility.assign(date=pd.to_datetime(eligibility["date"]))
    tickers = tuple(str(entry["ticker"]) for entry in config["tickers"])
    version = (
        str(returns["data_version"].iloc[0]) if "data_version" in returns else "unknown"
    )
    return HybridData(returns, calendar, regime_daily, eligibility, tickers, version)


# --------------------------------------------------------------------------- manifest


def select_dates(
    regime_daily: pd.DataFrame,
    calendar: Sequence[pd.Timestamp],
    *,
    splits: Sequence[str],
    regime: str,
    count: int,
    min_gap_sessions: int,
    min_probability: float,
) -> list[pd.Timestamp]:
    position = {pd.Timestamp(date): index for index, date in enumerate(calendar)}
    rows = regime_daily.loc[
        regime_daily["split"].isin(list(splits))
        & (regime_daily["regime"] == regime)
        & (regime_daily[f"prob_{regime}"] >= min_probability)
    ].sort_values("date")
    picks: list[pd.Timestamp] = []
    for date in pd.to_datetime(rows["date"]):
        if date not in position:
            continue
        if not picks or position[date] - position[picks[-1]] >= min_gap_sessions:
            picks.append(pd.Timestamp(date))
    if len(picks) <= count:
        return picks
    chosen = np.unique(np.linspace(0, len(picks) - 1, count).round().astype(int))
    return [picks[index] for index in chosen]


def build_manifest(
    config: Mapping[str, Any], settings: HybridSettings, data: HybridData, set_name: str
) -> dict[str, Any]:
    selection_all = settings.raw["instance_selection"]
    selection = selection_all[set_name]
    archetypes = list(settings.raw["portfolios"])
    base_seed = int(selection_all["scenario_seed_base"])
    per_regime: dict[str, list[pd.Timestamp]] = {}
    shortfalls: dict[str, int] = {}
    for regime in selection["regimes"]:
        dates = select_dates(
            data.regime_daily,
            data.calendar,
            splits=selection["splits"],
            regime=str(regime),
            count=int(selection["dates_per_regime"]),
            min_gap_sessions=int(selection["min_gap_sessions"]),
            min_probability=float(selection["min_regime_probability"]),
        )
        per_regime[str(regime)] = dates
        shortfalls[str(regime)] = max(
            0, int(selection["dates_per_regime"]) - len(dates)
        )

    # Round-robin theo regime để max_instances cắt công bằng giữa các regime.
    slots: list[tuple[str, pd.Timestamp, int]] = []
    max_per_date = int(selection.get("max_portfolios_per_date", 1))
    target = int(selection["dates_per_regime"])
    queues: dict[str, list[tuple[pd.Timestamp, int]]] = {}
    for regime, dates in per_regime.items():
        queue = [(date, 0) for date in dates]
        layer = 1
        while len(queue) < target and dates and layer < max_per_date:
            queue.extend((date, layer) for date in dates[: target - len(queue)])
            layer += 1
        queues[regime] = queue
    while any(queues.values()):
        for regime in selection["regimes"]:
            if queues[str(regime)]:
                date, layer = queues[str(regime)].pop(0)
                slots.append((str(regime), date, layer))
    slots = slots[: int(selection["max_instances"])]

    offset = 0 if set_name == "exploratory" else 7
    instances = []
    for number, (regime, date, layer) in enumerate(slots, start=1):
        portfolio = archetypes[(number - 1 + offset + layer) % len(archetypes)]
        prefix = "x" if set_name == "exploratory" else "c"
        instances.append(
            {
                "instance_id": f"{prefix}{number:02d}_{regime}_{date:%Y%m%d}_{portfolio}",
                "set": set_name,
                "as_of_date": f"{date:%Y-%m-%d}",
                "target_regime": regime,
                "portfolio_id": portfolio,
                "shared_date": layer > 0,
                "scenario_seed": base_seed
                + (0 if set_name == "exploratory" else 1000)
                + number,
            }
        )
    manifest = {
        "experiment_id": settings.experiment_id,
        "protocol_version": settings.raw.get("protocol_version"),
        "status": selection["status"],
        "set": set_name,
        "selection_rule": dict(selection),
        "regime_label_source": "filtered posterior (regime column), HMM fit on train split",
        "data_version": data.data_version,
        "regime_daily_hash": stable_hash(
            data.regime_daily[["date", "regime", "split"]].astype(str).values.tolist()
        ),
        "date_shortfall_by_regime": shortfalls,
        "unique_dates": len({item["as_of_date"] for item in instances}),
        "instances": instances,
        "instances_hash": manifest_instances_hash(instances),
    }
    validate_hybrid_manifest(manifest)
    return manifest


# --------------------------------------------------------------------------- instance inputs


def _eligibility_at(data: HybridData, tickers: Sequence[str], date: pd.Timestamp):
    frame = data.eligibility.loc[
        (data.eligibility["date"] <= date)
        & data.eligibility["ticker"].isin(list(tickers))
    ]
    if frame.empty:
        raise InstanceSkipped(f"no eligibility rows on or before {date.date()}.")
    snapshot = frame.loc[frame["date"] == frame["date"].max()].set_index("ticker")
    eligible = {
        t: bool(snapshot.loc[t, "eligible_flag"]) if t in snapshot.index else False
        for t in tickers
    }
    reasons = {
        t: str(snapshot.loc[t, "reason_code"])
        if t in snapshot.index
        else "MISSING_ELIGIBILITY"
        for t in tickers
    }
    turnover = {
        t: float(snapshot.loc[t, "avg_turnover_20d"])
        if t in snapshot.index
        else float("nan")
        for t in tickers
    }
    return eligible, reasons, turnover, str(frame["date"].max().date())


def portfolio_weights(
    spec: Mapping[str, Any],
    tickers: Sequence[str],
    eligible: Mapping[str, bool],
    returns: pd.DataFrame,
    as_of: pd.Timestamp,
) -> tuple[dict[str, float], float]:
    held = [t for t in tickers if eligible[t]]
    if not held:
        raise InstanceSkipped("no eligible tickers to hold.")
    cash = float(spec["cash_weight"])
    invest = 1.0 - cash
    kind = str(spec["kind"])
    raw: dict[str, float]
    if kind == "equal_weight":
        raw = {t: 1.0 for t in held}
    elif kind == "sector_tilt":
        tilt = [t for t in held if t in set(spec["tilt_tickers"])]
        rest = [t for t in held if t not in set(tilt)]
        share = float(spec["tilt_share"]) if tilt and rest else (1.0 if tilt else 0.0)
        raw = {t: share / len(tilt) for t in tilt} | {
            t: (1 - share) / len(rest) for t in rest
        }
    elif kind == "volatility_weighted":
        lookback = int(spec["lookback_sessions"])
        window = returns.loc[(returns["date"] <= as_of) & returns["ticker"].isin(held)]
        wide = window.pivot(index="date", columns="ticker", values="log_return").tail(
            lookback
        )
        vol = wide.std(ddof=1)
        if vol.isna().any() or (vol <= 0).any():
            raise InstanceSkipped(
                f"volatility undefined for {vol[vol.isna()].index.tolist()}."
            )
        raw = {t: float(vol[t]) for t in held}
    else:
        raise ValueError(
            f"[pipeline.hybrid.instances] unknown portfolio kind {kind!r}."
        )
    total = sum(raw.values())
    weights = {t: 0.0 for t in tickers} | {
        t: invest * v / total for t, v in raw.items()
    }
    return weights, cash


def instance_policy(
    spec: Mapping[str, Any],
    template: Mapping[str, Any],
    config: Mapping[str, Any],
    weights: Mapping[str, float],
    cash: float,
    turnover: Mapping[str, float],
) -> dict[str, Any] | None:
    rules = spec.get("policy")
    if not rules:
        return None
    # Protocol v2: cash_min = tiền mặt hiện có (không ép tăng). v1 dùng cash + target_cash_increment
    # và KHÔNG khả thi: 8 candidate × tối đa 30% chỉ nâng được ~7–8% NAV tiền mặt, nên x05 (v1) có 0
    # trạng thái feasible. Hệ quả ghi rõ: với policy, thành phần cash_budget_deviation = 0 khi
    # không bán tháo tiền mặt (khác archetype không policy dùng target_cash_increment).
    policy = dict(template) | {
        "cash_min": min(1.0, cash),
        "per_asset_reduction_caps": {},
        "do_not_sell": [],
    }
    held = sorted(
        (t for t, w in weights.items() if w > 0), key=lambda t: (-weights[t], t)
    )
    if rules.get("do_not_sell_top_weight_count"):
        policy["do_not_sell"] = held[: int(rules["do_not_sell_top_weight_count"])]
    if rules.get("lowest_turnover_cap_count"):
        ranked = sorted(
            (t for t in held if np.isfinite(turnover.get(t, np.nan))),
            key=lambda t: (turnover[t], t),
        )
        cap = float(rules["lowest_turnover_cap_value"])
        policy["per_asset_reduction_caps"] = {
            t: cap for t in ranked[: int(rules["lowest_turnover_cap_count"])]
        }
    return policy


def build_instance_inputs(
    instance: Mapping[str, Any],
    config: Mapping[str, Any],
    settings: HybridSettings,
    data: HybridData,
) -> InstanceInputs:
    as_of = pd.Timestamp(instance["as_of_date"])
    regime = str(instance["target_regime"])
    lookback = pd.Timestamp(settings.universe_lookback_start)
    first_valid = (
        data.returns.dropna(subset=["log_return"])
        .groupby("ticker")["date"]
        .min()
        .to_dict()
    )
    universe = tuple(
        t
        for t in data.snapshot_tickers
        if t in first_valid and first_valid[t] <= lookback
    )
    dropped = sorted(set(data.snapshot_tickers) - set(universe))
    panel = build_return_panel(
        data.returns.loc[data.returns["ticker"].isin(list(universe))],
        data.calendar,
        tickers=universe,
    )
    try:
        resolve_evaluation_date(data.regime_daily, panel, configured=as_of)
    except ValueError as exc:
        raise InstanceSkipped(str(exc)) from exc
    horizon = int(config["horizon_days"])
    block_length = int(config["block_length"])
    pool = build_block_pool(
        panel,
        data.regime_daily,
        target_regime=regime,
        block_length=block_length,
        evaluation_date=as_of,
    )
    if pool.eligible_block_count < settings.min_eligible_blocks:
        raise InstanceSkipped(
            f"regime={regime} has {pool.eligible_block_count} eligible blocks by {as_of.date()} "
            f"(< min_eligible_blocks={settings.min_eligible_blocks}); rejected={pool.rejected}."
        )
    cube, cube_log, scenario_meta = generate_cube(
        panel,
        pool,
        num_scenarios=settings.num_scenarios,
        horizon_days=horizon,
        block_length=block_length,
        seed=int(instance["scenario_seed"]),
    )
    last_position = list(panel.dates).index(as_of)
    reference = reference_windows(
        panel, pool, horizon_days=horizon, last_position=last_position
    )
    if reference.size:
        report = build_validation_report(
            cube_log,
            reference,
            thresholds=config["validation"]["thresholds"],
            target_regime=regime,
            min_reference_windows=int(config["validation"]["min_reference_windows"]),
        )
        scenario_gate = gate_status(report)
        failed_metrics = report.loc[report["verdict"] == "FAIL", "metric"].tolist()
    else:
        scenario_gate, failed_metrics = "NO_REFERENCE_WINDOWS", []

    eligible, reasons, turnover, eligibility_date = _eligibility_at(
        data, universe, as_of
    )
    spec = settings.raw["portfolios"][str(instance["portfolio_id"])]
    weights, cash = portfolio_weights(spec, universe, eligible, data.returns, as_of)
    instance_config = copy.deepcopy(dict(config))
    instance_config["num_scenarios"] = settings.num_scenarios
    policy = instance_policy(
        spec, settings.raw["policy_template"], config, weights, cash, turnover
    )
    if policy is None:
        instance_config.pop("risk_policy", None)
    else:
        instance_config["risk_policy"] = policy
    # Mã cấm bán vẫn nằm trong danh mục (weights tính ở trên) nhưng KHÔNG được làm candidate:
    # sản phẩm không đề xuất lệnh bán mã nhà đầu tư đã khóa (protocol v2, xem config).
    candidate_eligible = dict(eligible)
    for ticker in (policy or {}).get("do_not_sell", []):
        if candidate_eligible.get(ticker):
            candidate_eligible[ticker] = False
            reasons[ticker] = "DO_NOT_SELL_POLICY"
    return InstanceInputs(
        instance=dict(instance),
        scenarios=cube,
        tickers=universe,
        weights=weights,
        cash_weight=cash,
        eligibility=candidate_eligible,
        ineligible_reasons={
            t: reasons[t] for t in universe if not candidate_eligible[t]
        },
        config=instance_config,
        metadata={
            "universe_size": len(universe),
            "universe_dropped_not_listed_since_lookback": dropped,
            "eligibility_snapshot_date": eligibility_date,
            "eligible_count": int(sum(eligible.values())),
            "scenario": scenario_meta,
            "scenario_gate": scenario_gate,
            "scenario_gate_failed_metrics": failed_metrics,
            "reference_windows": int(reference.shape[0]) if reference.size else 0,
            "scenario_hash": array_hash(cube),
            "portfolio_hash": stable_hash(
                {"weights": weights, "cash": cash, "policy": policy}
            ),
            "policy": policy,
            "portfolio_label": "SYNTHETIC_ON_REAL_DATA",
        },
    )
