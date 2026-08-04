# Nguyễn Anh Tú - test fixture giả: đúng schema thật, tất định theo seed, có cấu trúc regime.
import numpy as np
from qshield_ai.fixtures import synthetic_dataset
from qshield_contracts.schemas.features import MarketFeaturesSchema
from qshield_contracts.schemas.returns import ReturnsSchema
from qshield_contracts.validate import validate_or_raise

TICKERS = ["AAA", "BBB", "CCC", "DDD"]


def test_returns_conform_to_real_schema() -> None:
    returns, _ = synthetic_dataset(tickers=TICKERS, n_days=400, seed=1)
    validate_or_raise(returns, ReturnsSchema, context="qshield_ai.fixtures")


def test_market_features_conform_to_real_schema() -> None:
    _, market = synthetic_dataset(tickers=TICKERS, n_days=400, seed=1)
    validate_or_raise(market, MarketFeaturesSchema, context="qshield_ai.fixtures")


def test_same_seed_gives_identical_data() -> None:
    first, _ = synthetic_dataset(tickers=TICKERS, n_days=200, seed=42)
    second, _ = synthetic_dataset(tickers=TICKERS, n_days=200, seed=42)
    assert first.equals(second)


def test_different_seed_gives_different_data() -> None:
    first, _ = synthetic_dataset(tickers=TICKERS, n_days=200, seed=42)
    second, _ = synthetic_dataset(tickers=TICKERS, n_days=200, seed=43)
    assert not first["log_return"].equals(second["log_return"])


def test_first_day_per_ticker_has_no_return() -> None:
    """Quy tắc 3: không forward-fill — ngày đầu mỗi mã phải là NaN, không phải 0."""
    returns, _ = synthetic_dataset(tickers=TICKERS, n_days=100, seed=1)
    first_day = returns["date"].min()
    assert returns.loc[returns["date"] == first_day, "log_return"].isna().all()


def test_cross_asset_correlation_is_material() -> None:
    """Có nhân tố chung ⇒ tương quan chéo đáng kể. Không có thì test bootstrap sau vô nghĩa."""
    returns, _ = synthetic_dataset(tickers=TICKERS, n_days=600, seed=1)
    wide = returns.pivot(index="date", columns="ticker", values="log_return").dropna()
    corr = wide.corr().to_numpy()
    off_diagonal = corr[~np.eye(len(TICKERS), dtype=bool)]
    assert off_diagonal.min() > 0.3


def test_volatility_varies_across_the_series() -> None:
    """Có chuyển trạng thái thật ⇒ volatility 20 phiên phải biến thiên rõ rệt."""
    _, market = synthetic_dataset(tickers=TICKERS, n_days=600, seed=1)
    vol = market["realized_vol_20d"].dropna()
    assert vol.max() / vol.min() > 2.0
    assert (vol > 0).all(), "log-transform ở feature_set yêu cầu volatility dương"


def test_missing_positions_drop_exactly_one_ticker() -> None:
    """Dùng ở Task 10 để dựng ngày panel thiếu mã — phải thiếu đúng 1 mã, không phải cả ngày."""
    returns, _ = synthetic_dataset(
        tickers=TICKERS, n_days=100, seed=1, missing_positions=(30, 31)
    )
    counts = returns.groupby("date")["ticker"].nunique()
    assert (counts == len(TICKERS) - 1).sum() == 2
    assert (counts == len(TICKERS)).sum() == 98


def test_splits_are_contiguous_and_ordered() -> None:
    returns, market = synthetic_dataset(tickers=TICKERS, n_days=400, seed=1)
    for frame in (returns, market):
        by_split = frame.groupby("split")["date"].agg(["min", "max"])
        assert by_split.loc["train", "max"] < by_split.loc["validation", "min"]
        assert by_split.loc["validation", "max"] < by_split.loc["test", "min"]
