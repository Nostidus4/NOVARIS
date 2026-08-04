# Nguyễn Anh Tú - test bootstrap: block liền mạch, đủ N mã, GIỮ ĐƯỢC tương quan chéo, tất định.
import numpy as np
import pandas as pd
import pytest
from qshield_ai.fixtures import synthetic_dataset
from qshield_ai.scenarios.bootstrap import (
    build_block_pool,
    build_return_panel,
    generate_cube,
    resolve_evaluation_date,
)

TICKERS = ["AAA", "BBB", "CCC", "DDD"]
BLOCK = 5
HORIZON = 20


def _setup(*, missing_positions=(), n_days=400, seed=9):
    """Panel + nhãn regime giả lập (nửa đầu normal, nửa sau stress) trên lịch của chính returns."""
    returns, _ = synthetic_dataset(
        tickers=TICKERS, n_days=n_days, seed=seed, missing_positions=missing_positions
    )
    calendar = sorted(returns["date"].unique())
    panel = build_return_panel(returns, calendar, tickers=TICKERS)
    regime_daily = pd.DataFrame(
        {
            "date": calendar,
            "regime": ["normal"] * (len(calendar) // 2)
            + ["stress"] * (len(calendar) - len(calendar) // 2),
            "split": ["train"] * (len(calendar) // 2)
            + ["test"] * (len(calendar) - len(calendar) // 2),
        }
    )
    return panel, regime_daily, calendar


def test_panel_marks_incomplete_days() -> None:
    """Ngày 0 luôn NaN ở mọi mã (không có giá trước đó để tính log return — thuộc tính cấu trúc
    của `synthetic_returns`, không phải lỗi), cộng 2 ngày bị xóa mã qua `missing_positions`."""
    panel, _, calendar = _setup(missing_positions=(50, 51))
    assert panel.log_returns.shape == (len(calendar), len(TICKERS))
    incomplete_positions = {0, 50, 51}
    assert panel.complete.sum() == len(calendar) - len(incomplete_positions)
    for position in incomplete_positions:
        assert not panel.complete[position]
    assert panel.complete[1:50].all() and panel.complete[52:].all()


def test_panel_rejects_missing_ticker() -> None:
    returns, _ = synthetic_dataset(tickers=TICKERS, n_days=50, seed=1)
    calendar = sorted(returns["date"].unique())
    with pytest.raises(ValueError, match="thiếu ticker"):
        build_return_panel(returns, calendar, tickers=[*TICKERS, "ZZZ"])


def test_pool_only_contains_anchors_of_the_target_regime() -> None:
    panel, regime_daily, calendar = _setup()
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    stress_dates = set(regime_daily.loc[regime_daily["regime"] == "stress", "date"])
    assert set(pool.anchor_dates) <= stress_dates
    assert pool.eligible_block_count == len(pool.block_starts) > 0


def test_blocks_start_the_day_after_the_anchor() -> None:
    """DR: nhãn tại `d`, block là `[d+1 .. d+5]` — không điều kiện hóa lên chính quan sát tại d."""
    panel, regime_daily, calendar = _setup()
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    positions = {date: index for index, date in enumerate(panel.dates)}
    for anchor, start in zip(pool.anchor_dates, pool.block_starts, strict=True):
        assert start == positions[anchor] + 1


def test_blocks_touching_an_incomplete_day_are_rejected_whole() -> None:
    """AD-11: thiếu một mã ⇒ loại CẢ block, không rút ngắn, không bỏ mã."""
    panel, regime_daily, calendar = _setup(missing_positions=(300,))
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    for start in pool.block_starts:
        assert panel.complete[start : start + BLOCK].all()
    assert pool.rejected["incomplete_panel"] > 0


def test_blocks_beyond_the_evaluation_date_are_rejected() -> None:
    panel, regime_daily, calendar = _setup()
    cutoff = calendar[-30]
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=cutoff,
    )
    last_allowed = list(panel.dates).index(cutoff)
    assert (pool.block_starts + BLOCK - 1 <= last_allowed).all()
    assert pool.rejected["beyond_evaluation_date"] > 0


def test_cube_shape_and_finiteness() -> None:
    panel, regime_daily, calendar = _setup()
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    simple, log_cube, metadata = generate_cube(
        panel, pool, num_scenarios=50, horizon_days=HORIZON, block_length=BLOCK, seed=7
    )
    assert simple.shape == (50, HORIZON, len(TICKERS))
    assert log_cube.shape == simple.shape
    assert np.isfinite(simple).all() and np.isfinite(log_cube).all()
    assert metadata["blocks_per_path"] == 4
    assert 0.0 <= metadata["reuse_rate"] <= 1.0


def test_simple_and_log_arrays_are_exactly_consistent() -> None:
    """AD-08: simple = expm1(log) đúng tới sai số máy — hai mảng không được lệch nhau."""
    panel, regime_daily, calendar = _setup()
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    simple, log_cube, _ = generate_cube(
        panel, pool, num_scenarios=20, horizon_days=HORIZON, block_length=BLOCK, seed=7
    )
    np.testing.assert_allclose(simple, np.expm1(log_cube), rtol=0, atol=1e-15)


def test_every_segment_is_a_real_contiguous_historical_block() -> None:
    """Chốt chặn chống bootstrap từng mã độc lập: mỗi 5 ngày phải là một block lịch sử NGUYÊN
    VẸN."""
    panel, regime_daily, calendar = _setup()
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    _, log_cube, _ = generate_cube(
        panel, pool, num_scenarios=30, horizon_days=HORIZON, block_length=BLOCK, seed=7
    )
    known = {
        panel.log_returns[start : start + BLOCK].tobytes()
        for start in pool.block_starts
    }
    for scenario in range(log_cube.shape[0]):
        for block in range(HORIZON // BLOCK):
            segment = log_cube[scenario, block * BLOCK : (block + 1) * BLOCK, :]
            assert segment.tobytes() in known


def test_cross_asset_correlation_is_preserved() -> None:
    """Tương quan chéo của cube phải bám tương quan lịch sử cùng regime (troubleshooting §4)."""
    panel, regime_daily, calendar = _setup(n_days=600)
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    _, log_cube, _ = generate_cube(
        panel, pool, num_scenarios=400, horizon_days=HORIZON, block_length=BLOCK, seed=7
    )
    historical = np.vstack(
        [panel.log_returns[start : start + BLOCK] for start in pool.block_starts]
    )
    cube_corr = np.corrcoef(log_cube.reshape(-1, len(TICKERS)), rowvar=False)
    historical_corr = np.corrcoef(historical, rowvar=False)
    assert np.abs(cube_corr - historical_corr).max() < 0.10


def test_same_seed_reproduces_the_cube() -> None:
    panel, regime_daily, calendar = _setup()
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    kwargs = {"num_scenarios": 25, "horizon_days": HORIZON, "block_length": BLOCK}
    first, _, _ = generate_cube(panel, pool, seed=7, **kwargs)
    second, _, _ = generate_cube(panel, pool, seed=7, **kwargs)
    third, _, _ = generate_cube(panel, pool, seed=8, **kwargs)
    np.testing.assert_array_equal(first, second)
    assert not np.array_equal(first, third)


def test_horizon_must_divide_into_whole_blocks() -> None:
    panel, regime_daily, calendar = _setup()
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    with pytest.raises(ValueError, match="chia hết"):
        generate_cube(
            panel, pool, num_scenarios=10, horizon_days=22, block_length=BLOCK, seed=7
        )


def test_empty_pool_raises_instead_of_returning_garbage() -> None:
    panel, regime_daily, calendar = _setup()
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="volatile",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    assert pool.eligible_block_count == 0
    with pytest.raises(ValueError, match="rỗng"):
        generate_cube(
            panel,
            pool,
            num_scenarios=10,
            horizon_days=HORIZON,
            block_length=BLOCK,
            seed=7,
        )


def test_resolve_evaluation_date_defaults_to_last_usable_day() -> None:
    panel, regime_daily, calendar = _setup()
    assert resolve_evaluation_date(regime_daily, panel, configured=None) == calendar[-1]


def test_resolve_evaluation_date_honours_config() -> None:
    panel, regime_daily, calendar = _setup()
    chosen = calendar[100]
    assert (
        resolve_evaluation_date(regime_daily, panel, configured=str(chosen.date()))
        == chosen
    )


def test_resolve_evaluation_date_rejects_a_date_without_a_label() -> None:
    panel, regime_daily, _ = _setup()
    with pytest.raises(ValueError, match="không có nhãn"):
        resolve_evaluation_date(regime_daily, panel, configured="1999-01-04")


def test_build_return_panel_rejects_unsorted_calendar() -> None:
    """Vị trí panel = thứ tự phiên. Calendar lộn xộn phải fail fast, không âm thầm nối sai."""
    returns, _ = synthetic_dataset(tickers=TICKERS, n_days=50, seed=1)
    calendar = sorted(returns["date"].unique())
    unsorted_calendar = [calendar[1], calendar[0], *calendar[2:]]
    with pytest.raises(ValueError, match="tăng dần"):
        build_return_panel(returns, unsorted_calendar, tickers=TICKERS)


def test_build_return_panel_rejects_duplicated_calendar() -> None:
    """Reindex trên calendar trùng nhân bản dòng, position_of chỉ giữ vị trí cuối — phải fail."""
    returns, _ = synthetic_dataset(tickers=TICKERS, n_days=50, seed=1)
    calendar = sorted(returns["date"].unique())
    duplicated_calendar = [*calendar[:10], calendar[9], *calendar[10:]]
    with pytest.raises(ValueError, match="trùng"):
        build_return_panel(returns, duplicated_calendar, tickers=TICKERS)


def test_ticker_order_survives_into_panel_and_cube_metadata() -> None:
    """Cột panel phải đúng THỨ TỰ ticker yêu cầu, không phải alphabet mặc định của `pivot`. Dùng
    thứ tự không-alphabet để một hoán vị cột làm test này fail."""
    requested_order = ["DDD", "AAA", "CCC", "BBB"]
    returns, _ = synthetic_dataset(tickers=TICKERS, n_days=400, seed=9)
    calendar = sorted(returns["date"].unique())
    panel = build_return_panel(returns, calendar, tickers=requested_order)
    assert panel.tickers == tuple(requested_order)

    wide = returns.pivot(index="date", columns="ticker", values="log_return")
    index = pd.DatetimeIndex(calendar)
    for position, ticker in enumerate(requested_order):
        expected = wide[ticker].reindex(index).to_numpy(dtype=float)
        np.testing.assert_array_equal(panel.log_returns[:, position], expected)

    regime_daily = pd.DataFrame(
        {
            "date": calendar,
            "regime": ["normal"] * (len(calendar) // 2)
            + ["stress"] * (len(calendar) - len(calendar) // 2),
        }
    )
    pool = build_block_pool(
        panel,
        regime_daily,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar[-1],
    )
    _, _, metadata = generate_cube(
        panel, pool, num_scenarios=10, horizon_days=HORIZON, block_length=BLOCK, seed=7
    )
    assert metadata["ticker_order"] == requested_order


def test_generate_cube_rejects_pool_built_from_a_different_panel() -> None:
    """Pool mang vị trí trên panel gốc. Panel khác (số ngày khác) phải bị chặn, không IndexError
    hoặc index sai âm thầm."""
    panel_a, regime_daily_a, calendar_a = _setup(n_days=400, seed=9)
    pool_a = build_block_pool(
        panel_a,
        regime_daily_a,
        target_regime="stress",
        block_length=BLOCK,
        evaluation_date=calendar_a[-1],
    )
    panel_b, _, _ = _setup(n_days=300, seed=9)
    with pytest.raises(ValueError, match="lệch nhau"):
        generate_cube(
            panel_b,
            pool_a,
            num_scenarios=10,
            horizon_days=HORIZON,
            block_length=BLOCK,
            seed=7,
        )
