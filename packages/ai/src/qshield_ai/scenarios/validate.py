# Nguyễn Anh Tú - kiểm định kịch bản: mean, std, quantile, skew, kurtosis, corr, tail coverage.
"""Kiểm định cube so với phân phối tham chiếu cùng regime.

Phân phối tham chiếu (SCN-OD-04): các cửa sổ `horizon_days` ngày THỰC SỰ XẢY RA sau mỗi anchor cùng
regime, cắt tại `t`. Không có mẫu tham chiếu thì "validation" chỉ là thống kê mô tả, không phải
kiểm định.

Cấu trúc (shape/NaN/Inf/ticker) FAIL CỨNG theo AC-SCN-007. Metric phân phối chấm theo ngưỡng
PROVISIONAL trong `configs/scenarios.yaml` — AI đề xuất, Phúc sở hữu quyết định (IN-RISK-03). Không
metric nào được bỏ qua im lặng (AC-SCN-010): mọi metric đều có một dòng và một verdict.

`tail_loss_q95` dùng danh mục ĐỀU (equal-weight) giữa các tài sản: tỷ trọng thật là việc của
`packages/risk`, đưa vào đây là đặt công thức tài chính sai chỗ.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from qshield_ai.scenarios.bootstrap import BlockPool, ReturnPanel

GATE_PASS = "PASS"
GATE_WARN = "PASS_WITH_WARNINGS"
GATE_FAIL = "FAIL"

_MIN_REFERENCE_WINDOWS = 30
# Sai số dấu phẩy động: cube hằng số (mọi phần tử BẰNG NHAU tuyệt đối) vẫn cho std ~1e-16 chứ
# không phải 0.0 chính xác, vì tổng độ lệch bình phương trên hàng trăm phần tử tích lũy sai số
# làm tròn. So `== 0` sẽ bỏ lọt trường hợp này và cho ra tương quan giả (0/0 → NaN bị che bởi
# nhiễu). Đây là epsilon số học, không phải ngưỡng nghiệp vụ — không đọc từ config.
_ZERO_VARIANCE_EPS = 1e-12


def structural_violations(
    cube: np.ndarray, *, expected_shape: tuple[int, int, int], tickers: Sequence[str]
) -> list[str]:
    """Kiểm tra cứng — vi phạm ở đây chặn cube sang Risk, không thương lượng (AC-SCN-007)."""
    violations: list[str] = []
    if cube.shape != expected_shape:
        violations.append(f"shape {cube.shape} != kỳ vọng {expected_shape}")
    if not np.isfinite(cube).all():
        bad = np.argwhere(~np.isfinite(cube))
        first = bad[0]
        violations.append(
            f"cube chứa NaN/Inf: {len(bad)} phần tử, đầu tiên tại "
            f"(scenario={first[0]}, day={first[1]}, asset={first[2]})"
        )
    if len(set(tickers)) != len(tickers):
        violations.append(f"ticker order có mã trùng: {list(tickers)}")
    if cube.ndim == 3 and len(tickers) != cube.shape[2]:
        violations.append(
            f"ticker order dài {len(tickers)} nhưng cube có {cube.shape[2]} tài sản"
        )
    return violations


def reference_windows(
    panel: ReturnPanel, pool: BlockPool, *, horizon_days: int, last_position: int
) -> np.ndarray:
    """Cửa sổ `horizon_days` ngày thực tế sau mỗi anchor hợp lệ — mẫu để so sánh."""
    windows = [
        panel.log_returns[start : start + horizon_days]
        for start in pool.block_starts
        if start + horizon_days - 1 <= last_position
        and panel.complete[start : start + horizon_days].all()
    ]
    if not windows:
        return np.empty((0, horizon_days, panel.log_returns.shape[1]))
    return np.stack(windows)


def _autocorrelation_lag1(cube: np.ndarray) -> float:
    """Tự tương quan lag-1 TRONG từng đường đi, trung bình trên mọi đường và mọi tài sản."""
    if cube.shape[1] < 2:
        return float("nan")
    current = cube[:, :-1, :].reshape(-1)
    following = cube[:, 1:, :].reshape(-1)
    if current.std() <= _ZERO_VARIANCE_EPS or following.std() <= _ZERO_VARIANCE_EPS:
        return float("nan")
    return float(np.corrcoef(current, following)[0, 1])


def _mean_cross_asset_correlation(cube: np.ndarray) -> float:
    n_assets = cube.shape[2]
    if n_assets < 2:
        return float("nan")
    flat = cube.reshape(-1, n_assets)
    if (flat.std(axis=0) <= _ZERO_VARIANCE_EPS).any():
        return float("nan")
    correlation = np.corrcoef(flat, rowvar=False)
    return float(correlation[~np.eye(n_assets, dtype=bool)].mean())


def _tail_loss_q95(cube: np.ndarray) -> float:
    """Phân vị 95 của LOSS trên horizon, danh mục đều. Quy ước `L = -R` (CLAUDE.md quy tắc 1)."""
    horizon_return = np.expm1(cube.sum(axis=1)).mean(axis=1)
    return float(np.quantile(-horizon_return, 0.95))


def distribution_metrics(cube_log: np.ndarray) -> dict[str, float]:
    """Thống kê mô tả trên return NGÀY gộp toàn cube, cộng hai chỉ số cấu trúc và một chỉ số
    đuôi."""
    flat = pd.Series(cube_log.reshape(-1))
    return {
        "mean": float(flat.mean()),
        "std": float(flat.std(ddof=0)),
        "skew": float(flat.skew()),
        "kurtosis": float(flat.kurt()),
        "q05": float(np.quantile(flat, 0.05)),
        "q95": float(np.quantile(flat, 0.95)),
        "autocorr_lag1": _autocorrelation_lag1(cube_log),
        "corr_mean": _mean_cross_asset_correlation(cube_log),
        "tail_loss_q95": _tail_loss_q95(cube_log),
    }


def _row(
    metric: str,
    scenario_value: float,
    reference_value: float,
    statistic: float,
    low: float | None,
    high: float | None,
    note: str,
) -> dict[str, Any]:
    if np.isnan(statistic):
        verdict = "WARN"
    elif (low is not None and statistic < low) or (
        high is not None and statistic > high
    ):
        verdict = "FAIL"
    else:
        verdict = "PASS"
    return {
        "metric": metric,
        "scenario_value": scenario_value,
        "reference_value": reference_value,
        "statistic": statistic,
        "threshold_low": low,
        "threshold_high": high,
        "verdict": verdict,
        "note": note,
    }


def _relative_error(scenario: float, reference: float) -> float:
    if reference == 0 or np.isnan(reference):
        return float("nan")
    return abs(scenario - reference) / abs(reference)


def build_validation_report(
    cube_log: np.ndarray,
    reference: np.ndarray,
    *,
    thresholds: Mapping[str, float],
    target_regime: str,
) -> pd.DataFrame:
    """Một dòng cho MỖI metric, kèm ngưỡng và verdict — không metric nào bị bỏ qua im lặng."""
    if reference.size == 0:
        raise ValueError(
            f"Không có cửa sổ tham chiếu nào cho regime {target_regime!r} — "
            "không kiểm định được, chỉ mô tả được."
        )
    scenario = distribution_metrics(cube_log)
    baseline = distribution_metrics(reference)
    note = (
        f"mẫu tham chiếu chỉ có {len(reference)} cửa sổ (< {_MIN_REFERENCE_WINDOWS})"
        if len(reference) < _MIN_REFERENCE_WINDOWS
        else ""
    )
    small_sample = bool(note)

    def statistic(value: float) -> float:
        return float("nan") if small_sample else value

    std_ratio = (
        scenario["std"] / baseline["std"] if baseline["std"] > 0 else float("nan")
    )
    rows = [
        _row(
            "mean_abs_diff",
            scenario["mean"],
            baseline["mean"],
            statistic(abs(scenario["mean"] - baseline["mean"])),
            None,
            thresholds["mean_abs_diff_max"],
            note,
        ),
        _row(
            "std_ratio",
            scenario["std"],
            baseline["std"],
            statistic(std_ratio),
            thresholds["std_ratio_min"],
            thresholds["std_ratio_max"],
            note,
        ),
        _row(
            "skew_abs_diff",
            scenario["skew"],
            baseline["skew"],
            statistic(abs(scenario["skew"] - baseline["skew"])),
            None,
            thresholds["skew_abs_diff_max"],
            note,
        ),
        _row(
            "kurtosis_abs_diff",
            scenario["kurtosis"],
            baseline["kurtosis"],
            statistic(abs(scenario["kurtosis"] - baseline["kurtosis"])),
            None,
            thresholds["kurtosis_abs_diff_max"],
            note,
        ),
        _row(
            "q05_rel_error",
            scenario["q05"],
            baseline["q05"],
            statistic(_relative_error(scenario["q05"], baseline["q05"])),
            None,
            thresholds["quantile_rel_error_max"],
            note,
        ),
        _row(
            "q95_rel_error",
            scenario["q95"],
            baseline["q95"],
            statistic(_relative_error(scenario["q95"], baseline["q95"])),
            None,
            thresholds["quantile_rel_error_max"],
            note,
        ),
        _row(
            "autocorr_abs_diff",
            scenario["autocorr_lag1"],
            baseline["autocorr_lag1"],
            statistic(abs(scenario["autocorr_lag1"] - baseline["autocorr_lag1"])),
            None,
            thresholds["autocorr_abs_diff_max"],
            note,
        ),
        _row(
            "corr_mean_abs_diff",
            scenario["corr_mean"],
            baseline["corr_mean"],
            statistic(abs(scenario["corr_mean"] - baseline["corr_mean"])),
            None,
            thresholds["corr_mean_abs_diff_max"],
            note,
        ),
        _row(
            "tail_coverage_ratio",
            scenario["tail_loss_q95"],
            baseline["tail_loss_q95"],
            statistic(
                scenario["tail_loss_q95"] / baseline["tail_loss_q95"]
                if baseline["tail_loss_q95"] != 0
                else float("nan")
            ),
            thresholds["tail_coverage_ratio_min"],
            thresholds["tail_coverage_ratio_max"],
            note,
        ),
    ]
    report = pd.DataFrame(rows)
    report.insert(0, "target_regime", target_regime)
    report.insert(1, "n_reference_windows", len(reference))
    return report


def gate_status(report: pd.DataFrame) -> str:
    """FAIL thắng WARN, WARN thắng PASS — không bao giờ báo đạt khi còn một metric fail."""
    verdicts = set(report["verdict"])
    if GATE_FAIL in verdicts:
        return GATE_FAIL
    if "WARN" in verdicts:
        return GATE_WARN
    return GATE_PASS
