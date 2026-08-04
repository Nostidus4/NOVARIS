# Nguyễn Anh Tú - dữ liệu giả TẠM THỜI cho test và --mock; xóa khi qshield_contracts.mocks có thật.
"""Sinh dữ liệu giả đúng `ReturnsSchema` và `MarketFeaturesSchema`.

TẠM THỜI (IN-CTR-08): `qshield_contracts.mocks/` chưa tồn tại, nên giả định "cả 5 người bắt đầu từ
ngày 1 trên mock" của CLAUDE.md chưa thành lập. Module này thay thế trong lúc chờ — XÓA CẢ FILE khi
`mocks/` có thật, đừng để hai nguồn dữ liệu giả song song.

Chuỗi sinh ra có chuyển trạng thái Markov 3 trạng thái với volatility khác nhau (để HMM có cái mà
tìm) và một nhân tố chung (để tương quan chéo khác 0 — không có thì test "bootstrap giữ được tương
quan" pass một cách vô nghĩa).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

_REGIME_VOLATILITY = (0.008, 0.016, 0.032)
_REGIME_DRIFT = (0.0006, 0.0, -0.0015)
_STICKINESS = 0.97


def _regime_path(n_days: int, rng: np.random.Generator) -> np.ndarray:
    """Đường trạng thái Markov 3 trạng thái, xác suất ở lại cao nên regime có độ dài thực."""
    off_diagonal = (1.0 - _STICKINESS) / 2.0
    transition = np.full((3, 3), off_diagonal)
    np.fill_diagonal(transition, _STICKINESS)
    states = np.zeros(n_days, dtype=int)
    for day in range(1, n_days):
        states[day] = rng.choice(3, p=transition[states[day - 1]])
    return states


def _assign_split(
    dates: pd.DatetimeIndex, train_frac: float, validation_frac: float
) -> pd.Series:
    n_days = len(dates)
    train_end = dates[int(n_days * train_frac) - 1]
    validation_end = dates[int(n_days * (train_frac + validation_frac)) - 1]
    labels = np.where(
        dates <= train_end,
        "train",
        np.where(dates <= validation_end, "validation", "test"),
    )
    return pd.Series(labels, index=dates, name="split")


def synthetic_returns(
    *,
    tickers: Sequence[str],
    n_days: int,
    seed: int,
    start: str = "2018-01-02",
    train_frac: float = 0.6,
    validation_frac: float = 0.15,
    missing_positions: Sequence[int] = (),
) -> pd.DataFrame:
    """Long format `(date, ticker)` đúng `ReturnsSchema`.

    `missing_positions` là vị trí ngày (0-based) sẽ bị xóa mã ĐẦU TIÊN — dùng để dựng ngày panel
    thiếu mã cho test luật eligibility của block.
    """
    if n_days < 2:
        raise ValueError(f"n_days phải >= 2 để có return, nhận {n_days}.")
    rng = np.random.default_rng(seed)
    n_assets = len(tickers)
    dates = pd.bdate_range(start=start, periods=n_days)

    states = _regime_path(n_days, rng)
    volatility = np.asarray(_REGIME_VOLATILITY)[states]
    drift = np.asarray(_REGIME_DRIFT)[states]

    common_factor = rng.normal(drift, volatility)
    loadings = np.linspace(0.8, 1.2, n_assets)
    idiosyncratic = rng.normal(0.0, volatility[:, None] * 0.5, size=(n_days, n_assets))
    log_return = common_factor[:, None] * loadings[None, :] + idiosyncratic

    prices = 20_000.0 * np.exp(np.cumsum(log_return, axis=0))
    volume = rng.lognormal(13.0, 0.4, size=(n_days, n_assets)) * (
        1.0 + 2.0 * volatility[:, None]
    )
    split = _assign_split(dates, train_frac, validation_frac)

    frames = []
    for column, ticker in enumerate(tickers):
        adjusted = prices[:, column]
        previous = np.concatenate([[np.nan], adjusted[:-1]])
        frames.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "ticker": ticker,
                    "open": adjusted * 0.999,
                    "high": adjusted * 1.004,
                    "low": adjusted * 0.996,
                    "close": adjusted,
                    "adjusted_close": adjusted,
                    "volume": volume[:, column].astype(np.int64),
                    "source_id": "fixture",
                    "data_version": "fixture-v1",
                    "quality_flag": "ok",
                    "turnover_value": adjusted * volume[:, column],
                    "prev_adj": previous,
                    "simple_return": adjusted / previous - 1.0,
                    "log_return": np.log(adjusted / previous),
                    "split": split.to_numpy(),
                }
            )
        )

    out = pd.concat(frames, ignore_index=True)
    if missing_positions:
        dropped = {dates[position] for position in missing_positions}
        out = out.loc[~(out["date"].isin(dropped) & (out["ticker"] == tickers[0]))]
    return out.sort_values(["ticker", "date"]).reset_index(drop=True)


def synthetic_market_features(
    returns: pd.DataFrame, *, index_start: float = 1000.0
) -> pd.DataFrame:
    """Market feature từ composite equal-weight của chính `returns` — đúng `MarketFeaturesSchema`.

    Công thức khớp `qshield_data.features.build_market_features` (nhánh custom composite) nhưng
    hiện thực lại tại chỗ: `qshield_ai` KHÔNG được import `qshield_data` (CLAUDE.md quy tắc 11).
    """
    wide = returns.pivot(index="date", columns="ticker", values="log_return")
    market_log_return = wide.mean(axis=1, skipna=True)
    close = index_start * np.exp(market_log_return.fillna(0.0).cumsum())
    volume = returns.groupby("date")["volume"].sum().reindex(close.index)

    frame = pd.DataFrame(
        {
            "date": close.index,
            "close": close.to_numpy(dtype=float),
            "volume": volume.to_numpy(dtype=float),
            "source": "fixture_composite_ew",
        }
    )
    frame["market_log_return"] = np.log(frame["close"] / frame["close"].shift(1))
    frame["market_simple_return"] = frame["close"] / frame["close"].shift(1) - 1.0
    frame["realized_vol_20d"] = (
        frame["market_log_return"].rolling(20, min_periods=20).std()
    )
    frame["rolling_max_252"] = frame["close"].rolling(252, min_periods=60).max()
    frame["drawdown"] = frame["close"] / frame["rolling_max_252"] - 1.0
    frame["liquidity_20d"] = (
        np.log(frame["volume"].replace(0, np.nan)).rolling(20, min_periods=10).mean()
    )
    split_by_date = returns.drop_duplicates("date").set_index("date")["split"]
    frame["split"] = frame["date"].map(split_by_date)
    return frame


def synthetic_dataset(
    *,
    tickers: Sequence[str],
    n_days: int = 900,
    seed: int = 7,
    missing_positions: Sequence[int] = (),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`(returns, market_features)` nhất quán với nhau — điểm vào duy nhất cho test và `--mock`."""
    returns = synthetic_returns(
        tickers=tickers, n_days=n_days, seed=seed, missing_positions=missing_positions
    )
    return returns, synthetic_market_features(returns)
