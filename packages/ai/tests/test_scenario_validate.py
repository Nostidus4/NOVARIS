# Nguyễn Anh Tú - test kiểm định kịch bản: cấu trúc fail cứng, metric có verdict, không im lặng.
import numpy as np
import pandas as pd
import pytest
from qshield_ai.scenarios.bootstrap import BlockPool, ReturnPanel
from qshield_ai.scenarios.validate import (
    GATE_FAIL,
    GATE_PASS,
    build_validation_report,
    distribution_metrics,
    gate_status,
    reference_windows,
    structural_violations,
)

TICKERS = ["AAA", "BBB", "CCC"]
SHAPE = (40, 20, 3)
THRESHOLDS = {
    "mean_abs_diff_max": 0.0010,
    "std_ratio_min": 0.80,
    "std_ratio_max": 1.25,
    "skew_abs_diff_max": 1.0,
    "kurtosis_abs_diff_max": 5.0,
    "quantile_rel_error_max": 0.25,
    "autocorr_abs_diff_max": 0.10,
    "corr_mean_abs_diff_max": 0.10,
    "tail_coverage_ratio_min": 0.5,
    "tail_coverage_ratio_max": 2.0,
}


def _cube(
    seed: int, scale: float = 1.0, shape: tuple[int, int, int] = SHAPE
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, 0.01 * scale, size=shape)


def test_structural_check_passes_a_clean_cube() -> None:
    assert structural_violations(_cube(1), expected_shape=SHAPE, tickers=TICKERS) == []


def test_structural_check_catches_wrong_shape() -> None:
    violations = structural_violations(
        _cube(1, shape=(40, 19, 3)), expected_shape=SHAPE, tickers=TICKERS
    )
    assert len(violations) == 1 and "shape" in violations[0]


def test_structural_check_catches_nan_and_reports_position() -> None:
    cube = _cube(1)
    cube[3, 7, 1] = np.nan
    violations = structural_violations(cube, expected_shape=SHAPE, tickers=TICKERS)
    assert any("NaN" in violation or "Inf" in violation for violation in violations)
    assert any("3" in violation for violation in violations), "phải chỉ ra vị trí lỗi"


def test_structural_check_catches_duplicate_tickers() -> None:
    violations = structural_violations(
        _cube(1), expected_shape=SHAPE, tickers=["AAA", "AAA", "CCC"]
    )
    assert any("ticker" in violation for violation in violations)


def test_distribution_metrics_cover_every_required_family() -> None:
    """AC-SCN-008: moments, volatility, autocorrelation, cross-asset correlation, tail quantiles."""
    metrics = distribution_metrics(_cube(1))
    assert {
        "mean",
        "std",
        "skew",
        "kurtosis",
        "q05",
        "q95",
        "autocorr_lag1",
        "corr_mean",
        "tail_loss_q95",
    } <= set(metrics)


def test_metrics_match_hand_calculation_on_a_constant_cube() -> None:
    """Cube toàn 0.01: mean = 0.01, std = 0, tương quan chéo không xác định ⇒ trả NaN, không nổ."""
    metrics = distribution_metrics(np.full(SHAPE, 0.01))
    assert metrics["mean"] == pytest.approx(0.01)
    assert metrics["std"] == pytest.approx(0.0, abs=1e-12)
    assert np.isnan(metrics["corr_mean"])


def test_matching_distributions_pass_every_metric() -> None:
    report = build_validation_report(
        _cube(1), _cube(2), thresholds=THRESHOLDS, target_regime="stress"
    )
    assert set(report["verdict"]) == {"PASS"}
    assert gate_status(report) == GATE_PASS


def test_inflated_volatility_fails_the_std_ratio() -> None:
    """Cube rộng gấp 3 lần tham chiếu ⇒ std_ratio phải FAIL, không được lọt."""
    report = build_validation_report(
        _cube(1, scale=3.0), _cube(2), thresholds=THRESHOLDS, target_regime="stress"
    )
    failed = report.loc[report["verdict"] == "FAIL", "metric"].tolist()
    assert "std_ratio" in failed
    assert gate_status(report) == GATE_FAIL


def test_report_has_the_columns_the_csv_contract_needs() -> None:
    report = build_validation_report(
        _cube(1), _cube(2), thresholds=THRESHOLDS, target_regime="stress"
    )
    assert {
        "target_regime",
        "metric",
        "scenario_value",
        "reference_value",
        "statistic",
        "threshold_low",
        "threshold_high",
        "verdict",
        "note",
    } <= set(report.columns)
    assert set(report["target_regime"]) == {"stress"}


def test_small_reference_sample_warns_rather_than_silently_passing() -> None:
    report = build_validation_report(
        _cube(1),
        _cube(2, shape=(5, 20, 3)),
        thresholds=THRESHOLDS,
        target_regime="stress",
    )
    assert "WARN" in set(report["verdict"])
    assert gate_status(report) in {"PASS_WITH_WARNINGS", GATE_FAIL}


def test_gate_status_prefers_fail_over_warn() -> None:
    report = pd.DataFrame({"verdict": ["PASS", "WARN", "FAIL"]})
    assert gate_status(report) == GATE_FAIL


# --- Hand-computed metric checks -------------------------------------------------------------
# Mỗi test dưới đây dùng mảng nhỏ mà giá trị kỳ vọng tính được bằng tay (hoặc bằng công thức
# tường minh), không chỉ kiểm tra "có giá trị" hay "không NaN".


def test_autocorr_lag1_hand_computed_perfectly_linear_path() -> None:
    """Một đường đi [1,2,3,4]: current=[1,2,3], following=[2,3,4] — lệch nhau đúng hằng số nên
    tương quan Pearson = 1.0 tuyệt đối."""
    cube = np.array([1.0, 2.0, 3.0, 4.0]).reshape(1, 4, 1)
    metrics = distribution_metrics(cube)
    assert metrics["autocorr_lag1"] == pytest.approx(1.0)


def test_corr_mean_hand_computed_perfectly_correlated_assets() -> None:
    """Tài sản B = 2 × tài sản A tại mọi ngày/kịch bản ⇒ tương quan chéo = 1.0 tuyệt đối
    (hệ số Pearson bất biến theo tỷ lệ tuyến tính)."""
    asset_a = np.arange(8, dtype=float).reshape(4, 2, 1)
    cube = np.concatenate([asset_a, 2.0 * asset_a], axis=2)
    metrics = distribution_metrics(cube)
    assert metrics["corr_mean"] == pytest.approx(1.0)


def test_tail_loss_q95_hand_computed_single_asset() -> None:
    """4 kịch bản, 1 tài sản, return horizon xây bằng tay = [-0.1, 0.0, 0.05, 0.2] (ngày 2 = 0 lợi
    suất log để expm1(tổng) đúng bằng return horizon). Loss = -return =
    [0.1, 0.0, -0.05, -0.2]; numpy.quantile(., 0.95, method='linear') nội suy giữa phần tử thứ 2
    (0.0) và thứ 3 (0.1) tại vị trí 2.85 ⇒ 0.0 + 0.85*(0.1-0.0) = 0.085."""
    horizon_return = np.array([-0.1, 0.0, 0.05, 0.2])
    day1 = np.log1p(horizon_return)
    day2 = np.zeros(4)
    cube = np.stack([day1, day2], axis=1).reshape(4, 2, 1)
    metrics = distribution_metrics(cube)
    assert metrics["tail_loss_q95"] == pytest.approx(0.085)


def test_tail_loss_q95_averages_assets_with_equal_weight() -> None:
    """2 tài sản, 1 ngày, 2 kịch bản. Kịch bản 0: return [+0.1, -0.1] ⇒ trung bình đều = 0.0.
    Kịch bản 1: return [+0.2, 0.0] ⇒ trung bình đều = 0.1. Loss = [-0.0, -0.1]; quantile 0.95
    nội suy giữa -0.1 (vị trí 0) và -0.0 (vị trí 1) tại 0.95 ⇒ -0.1 + 0.95*0.1 = -0.005.
    Nếu module dùng tỷ trọng khác-đều hoặc chỉ lấy 1 tài sản, kết quả sẽ lệch khỏi giá trị này."""
    cube = np.array(
        [
            [[np.log1p(0.1), np.log1p(-0.1)]],
            [[np.log1p(0.2), np.log1p(0.0)]],
        ]
    )
    assert cube.shape == (2, 1, 2)
    metrics = distribution_metrics(cube)
    assert metrics["tail_loss_q95"] == pytest.approx(-0.005, abs=1e-9)


def test_skew_and_kurtosis_hand_computed_on_symmetric_array() -> None:
    """Cube toàn bộ chỉ chứa [1,2,3,4,5] (đối xứng quanh 3): skew = 0 theo định nghĩa (mọi mô-men
    lẻ bằng 0 với phân phối đối xứng). Kurtosis (excess, công thức G2 hiệu chỉnh mẫu, giống
    `pandas.Series.kurt`): n=5, m4=sum((x-mean)^4)=34, s^2 (ddof=1)=2.5 ⇒
    G2 = [n(n+1)/((n-1)(n-2)(n-3))]*m4/s^4 - 3(n-1)^2/((n-2)(n-3))
       = [30/24]*34/6.25 - 3*16/6 = 6.8 - 8 = -1.2."""
    cube = np.array([1.0, 2.0, 3.0, 4.0, 5.0]).reshape(5, 1, 1)
    metrics = distribution_metrics(cube)
    assert metrics["skew"] == pytest.approx(0.0, abs=1e-12)
    assert metrics["kurtosis"] == pytest.approx(-1.2)


# --- Verdict failure paths for metric families beyond std_ratio ------------------------------


def test_quantiles_hand_computed_on_evenly_spaced_array() -> None:
    """Cube toàn bộ chỉ chứa 0..20 (21 phần tử, cách đều). numpy.quantile phương pháp mặc định
    'linear' tại phân vị p trên mảng đã sắp xếp dùng vị trí p*(n-1): 0.05*20=1.0 (đúng chỉ số,
    không cần nội suy) ⇒ q05=1.0; 0.95*20=19.0 ⇒ q95=19.0."""
    cube = np.arange(21, dtype=float).reshape(21, 1, 1)
    metrics = distribution_metrics(cube)
    assert metrics["q05"] == pytest.approx(1.0)
    assert metrics["q95"] == pytest.approx(19.0)


def test_shifted_mean_fails_the_mean_abs_diff_metric() -> None:
    """Scenario dịch mean thêm 0.01 so với reference (ngưỡng mean_abs_diff_max=0.0010) ⇒ FAIL."""
    rng = np.random.default_rng(3)
    reference = rng.normal(0.0, 0.01, size=SHAPE)
    scenario = reference.copy() + 0.01
    report = build_validation_report(
        scenario, reference, thresholds=THRESHOLDS, target_regime="stress"
    )
    failed = report.loc[report["verdict"] == "FAIL", "metric"].tolist()
    assert "mean_abs_diff" in failed
    assert gate_status(report) == GATE_FAIL


def test_decorrelated_scenario_fails_corr_mean_abs_diff() -> None:
    """Reference có 2 tài sản tương quan hoàn hảo (corr_mean=1.0); scenario độc lập ngẫu nhiên
    (corr_mean ~ 0) ⇒ lệch > ngưỡng corr_mean_abs_diff_max=0.10 ⇒ FAIL."""
    rng = np.random.default_rng(11)
    base = rng.normal(0.0, 0.01, size=(200, 20, 1))
    reference = np.concatenate([base, base], axis=2)  # tương quan = 1.0 tuyệt đối
    scenario = rng.normal(0.0, 0.01, size=(200, 20, 2))  # hai tài sản độc lập
    report = build_validation_report(
        scenario, reference, thresholds=THRESHOLDS, target_regime="stress"
    )
    failed = report.loc[report["verdict"] == "FAIL", "metric"].tolist()
    assert "corr_mean_abs_diff" in failed
    assert gate_status(report) == GATE_FAIL


# --- reference_windows: no-future-data and incompleteness guarantees -------------------------


def _panel(values: np.ndarray, complete: np.ndarray) -> ReturnPanel:
    dates = tuple(
        pd.Timestamp("2024-01-01") + pd.Timedelta(days=i) for i in range(len(values))
    )
    return ReturnPanel(
        dates=dates, log_returns=values, complete=complete, tickers=("AAA",)
    )


def _pool(starts: list[int]) -> BlockPool:
    return BlockPool(
        target_regime="stress",
        block_starts=np.asarray(starts, dtype=int),
        anchor_dates=tuple(
            pd.Timestamp("2024-01-01") + pd.Timedelta(days=s - 1) for s in starts
        ),
        eligible_block_count=len(starts),
        rejected={},
        anchor_split_counts={},
        panel_dates=(),
        ticker_order=(),
    )


def test_reference_windows_excludes_future_and_incomplete_windows() -> None:
    """12 ngày, 1 tài sản, giá trị = chỉ số ngày (0..11). Ngày 7 thiếu dữ liệu. horizon_days=3,
    last_position=10 (mô phỏng t=10).

    - start=0 -> ngày [0,1,2] đủ dữ liệu, không vượt t ⇒ GIỮ, giá trị [[0],[1],[2]].
    - start=2 -> ngày [2,3,4] đủ dữ liệu, không vượt t ⇒ GIỮ, giá trị [[2],[3],[4]].
    - start=5 -> ngày [5,6,7] chạm ngày 7 thiếu dữ liệu ⇒ LOẠI (không phải lỗi tương lai).
    - start=9 -> ngày [9,10,11]; 11 > last_position=10 ⇒ LOẠI (đúng là dữ liệu tương lai so với t).
    """
    values = np.arange(12, dtype=float).reshape(12, 1)
    complete = np.ones(12, dtype=bool)
    complete[7] = False
    panel = _panel(values, complete)
    pool = _pool([0, 2, 5, 9])

    windows = reference_windows(panel, pool, horizon_days=3, last_position=10)

    assert windows.shape == (2, 3, 1)
    np.testing.assert_array_equal(windows[0], [[0.0], [1.0], [2.0]])
    np.testing.assert_array_equal(windows[1], [[2.0], [3.0], [4.0]])


def test_reference_windows_empty_when_nothing_qualifies() -> None:
    """Mọi start đều vượt quá `t` ⇒ trả mảng rỗng đúng shape `(0, H, N)`, không lỗi, không None."""
    values = np.arange(6, dtype=float).reshape(6, 1)
    complete = np.ones(6, dtype=bool)
    panel = _panel(values, complete)
    pool = _pool([4, 5])

    windows = reference_windows(panel, pool, horizon_days=3, last_position=5)

    assert windows.shape == (0, 3, 1)
