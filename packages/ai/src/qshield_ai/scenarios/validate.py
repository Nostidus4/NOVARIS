# Nguyễn Anh Tú - kiểm định kịch bản: mean, std, quantile, skew, kurtosis, corr, tail coverage.
"""Kiểm định cube so với phân phối tham chiếu cùng regime.

Phân phối tham chiếu (SCN-OD-04): các cửa sổ `horizon_days` ngày THỰC SỰ XẢY RA sau mỗi anchor cùng
regime, cắt tại `t`. Không có mẫu tham chiếu thì "validation" chỉ là thống kê mô tả, không phải
kiểm định.

Cấu trúc (shape/NaN/Inf/ticker) FAIL CỨNG theo AC-SCN-007. Metric phân phối chấm theo ngưỡng
PROVISIONAL trong `configs/base.yaml` — AI đề xuất, Phúc sở hữu quyết định (IN-RISK-03). Không
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
        # Cube sai chiều (đã bị bắt ở kiểm tra shape phía trên) có thể có ít hơn 3 trục — đây
        # chính là cube mà hàm này tồn tại để MÔ TẢ, nên không được index cứng first[2] mà nổ.
        position = (
            f"(scenario={first[0]}, day={first[1]}, asset={first[2]})"
            if cube.ndim == 3
            else f"vị trí {tuple(int(i) for i in first)} (cube không phải 3 chiều)"
        )
        violations.append(
            f"cube chứa NaN/Inf: {len(bad)} phần tử, đầu tiên tại {position}"
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
    """Cửa sổ `horizon_days` ngày thực tế sau mỗi anchor hợp lệ — mẫu để so sánh.

    `pool.block_starts` là chỉ số nguyên vào panel DÙNG ĐỂ DỰNG pool đó (xem
    `bootstrap.generate_cube`, cùng guard). Panel truyền vào đây khác panel gốc — dù cùng hình
    dạng — sẽ khiến hàm cắt đúng vị trí nhưng SAI phiên, hỏng im lặng toàn bộ phân phối tham
    chiếu và mọi verdict phía sau tính trên nền sai.
    """
    if pool.panel_dates != panel.dates or pool.ticker_order != panel.tickers:
        mismatch = next(
            (
                f"ngày đầu lệch tại vị trí {i}: pool={a.date()} vs panel={b.date()}"
                for i, (a, b) in enumerate(
                    zip(pool.panel_dates, panel.dates, strict=False)
                )
                if a != b
            ),
            f"độ dài lệch: pool {len(pool.panel_dates)} vs panel {len(panel.dates)}",
        )
        raise ValueError(
            f"reference_windows: pool dựng từ panel khác với panel truyền vào — {mismatch}; "
            f"ticker pool={pool.ticker_order} vs panel={panel.tickers}. "
            f"`block_starts` là chỉ số vào panel gốc nên dùng nhầm panel sẽ lấy sai phiên."
        )
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
    *,
    small_sample: bool,
) -> dict[str, Any]:
    """Verdict cho một metric. Mẫu tham chiếu nhỏ chỉ được phép HẠ một PASS xuống WARN (không đủ
    mẫu để chứng nhận) — không bao giờ được che một FAIL. `statistic` luôn là giá trị THẬT đã
    tính, không bao giờ bị thay bằng NaN chỉ vì mẫu nhỏ (AC-SCN-010: không bằng chứng nào bị
    xoá)."""
    if np.isnan(statistic):
        verdict = "WARN"
    elif (low is not None and statistic < low) or (
        high is not None and statistic > high
    ):
        verdict = "FAIL"
    elif small_sample:
        verdict = "WARN"
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


def _threshold(thresholds: Mapping[str, float], key: str) -> float:
    """Đọc một ngưỡng, báo lỗi có ngữ cảnh thay vì `KeyError` trơ trụi khi thiếu key."""
    try:
        return thresholds[key]
    except KeyError as exc:
        raise ValueError(
            f"Thiếu ngưỡng {key!r} trong configs/base.yaml (validation.thresholds) — "
            "không kiểm định được metric này."
        ) from exc


def build_validation_report(
    cube_log: np.ndarray,
    reference: np.ndarray,
    *,
    thresholds: Mapping[str, float],
    target_regime: str,
    min_reference_windows: int,
) -> pd.DataFrame:
    """Một dòng cho MỖI metric, kèm ngưỡng và verdict — không metric nào bị bỏ qua im lặng.

    Mẫu tham chiếu ít hơn `min_reference_windows` cửa sổ chỉ được phép hạ THẤP ĐỘ TIN CẬY, không
    được xoá bằng chứng: `statistic` luôn là giá trị thật đã tính (không bao giờ ép về NaN), một
    metric PASS bị hạ xuống WARN vì mẫu mỏng, nhưng một metric VI PHẠM ngưỡng vẫn FAIL — mẫu nhỏ
    không làm vi phạm biến mất. `min_reference_windows` phải được truyền vào tường minh từ
    `configs/base.yaml` (`validation.min_reference_windows`); không có giá trị mặc định ngầm
    trong module để tránh áp dụng một ngưỡng không ai chọn khi caller quên truyền.
    """
    if reference.size == 0:
        raise ValueError(
            f"Không có cửa sổ tham chiếu nào cho regime {target_regime!r} — "
            "không kiểm định được, chỉ mô tả được."
        )
    scenario = distribution_metrics(cube_log)
    baseline = distribution_metrics(reference)
    n_reference = len(reference)
    small_sample = n_reference < min_reference_windows
    note = (
        f"mẫu tham chiếu chỉ có {n_reference} cửa sổ (< {min_reference_windows}) — "
        "PASS bị hạ xuống WARN, FAIL vẫn giữ nguyên"
        if small_sample
        else ""
    )

    std_ratio = (
        scenario["std"] / baseline["std"] if baseline["std"] > 0 else float("nan")
    )
    rows = [
        _row(
            "mean_abs_diff",
            scenario["mean"],
            baseline["mean"],
            abs(scenario["mean"] - baseline["mean"]),
            None,
            _threshold(thresholds, "mean_abs_diff_max"),
            note,
            small_sample=small_sample,
        ),
        _row(
            "std_ratio",
            scenario["std"],
            baseline["std"],
            std_ratio,
            _threshold(thresholds, "std_ratio_min"),
            _threshold(thresholds, "std_ratio_max"),
            note,
            small_sample=small_sample,
        ),
        _row(
            "skew_abs_diff",
            scenario["skew"],
            baseline["skew"],
            abs(scenario["skew"] - baseline["skew"]),
            None,
            _threshold(thresholds, "skew_abs_diff_max"),
            note,
            small_sample=small_sample,
        ),
        _row(
            "kurtosis_abs_diff",
            scenario["kurtosis"],
            baseline["kurtosis"],
            abs(scenario["kurtosis"] - baseline["kurtosis"]),
            None,
            _threshold(thresholds, "kurtosis_abs_diff_max"),
            note,
            small_sample=small_sample,
        ),
        _row(
            "q05_rel_error",
            scenario["q05"],
            baseline["q05"],
            _relative_error(scenario["q05"], baseline["q05"]),
            None,
            _threshold(thresholds, "quantile_rel_error_max"),
            note,
            small_sample=small_sample,
        ),
        _row(
            "q95_rel_error",
            scenario["q95"],
            baseline["q95"],
            _relative_error(scenario["q95"], baseline["q95"]),
            None,
            _threshold(thresholds, "quantile_rel_error_max"),
            note,
            small_sample=small_sample,
        ),
        _row(
            "autocorr_abs_diff",
            scenario["autocorr_lag1"],
            baseline["autocorr_lag1"],
            abs(scenario["autocorr_lag1"] - baseline["autocorr_lag1"]),
            None,
            _threshold(thresholds, "autocorr_abs_diff_max"),
            note,
            small_sample=small_sample,
        ),
        _row(
            "corr_mean_abs_diff",
            scenario["corr_mean"],
            baseline["corr_mean"],
            abs(scenario["corr_mean"] - baseline["corr_mean"]),
            None,
            _threshold(thresholds, "corr_mean_abs_diff_max"),
            note,
            small_sample=small_sample,
        ),
        _row(
            "tail_coverage_ratio",
            scenario["tail_loss_q95"],
            baseline["tail_loss_q95"],
            (
                scenario["tail_loss_q95"] / baseline["tail_loss_q95"]
                if baseline["tail_loss_q95"] != 0
                else float("nan")
            ),
            _threshold(thresholds, "tail_coverage_ratio_min"),
            _threshold(thresholds, "tail_coverage_ratio_max"),
            note,
            small_sample=small_sample,
        ),
    ]
    report = pd.DataFrame(rows)
    report.insert(0, "target_regime", target_regime)
    report.insert(1, "reference_windows", n_reference)
    report.insert(2, "small_sample", small_sample)
    return report


def gate_status(report: pd.DataFrame) -> str:
    """FAIL thắng WARN, WARN thắng PASS — không bao giờ báo đạt khi còn một metric fail."""
    verdicts = set(report["verdict"])
    if GATE_FAIL in verdicts:
        return GATE_FAIL
    if "WARN" in verdicts:
        return GATE_WARN
    return GATE_PASS
