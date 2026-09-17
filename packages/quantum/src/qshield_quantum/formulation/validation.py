# Đỗ Ngọc Tân - CỔNG CHẶN P0-2: chấm surrogate trên validation/holdout trước khi tin bất kỳ solver nào.
"""Cổng chặn surrogate (`gates.surrogate_validation_required_before_solver`).

Surrogate bậc 2 (`formulation/surrogate.py`) xấp xỉ một hàm mục tiêu chứa CVaR — vốn KHÔNG phải
hàm bậc 2 của reductions (CVaR là expected shortfall của một hàm phi tuyến của weights). Fit trên
211 mẫu structured cho `p(d) = 1 + d + d(d-1)/2 = 211` hệ số là NỘI SUY ĐÚNG theo cấu trúc:
residual gần 0 không nói lên điều gì về khả năng khái quát hoá.

Vì vậy `exact` duyệt đủ 2^20 chỉ cho ra "nghiệm tối ưu CỦA MỘT MÔ HÌNH" — nếu mô hình đó sai thì
mọi thứ phía sau (exact, QAOA, benchmark) đều là tối ưu hoá một thứ không phải bài toán thật.
Module này chấm surrogate trên hai split KHÔNG dùng để fit:

- `validation` — dùng để CHỌN encoding/hyperparameter (docs/decisions/2026-08-31-phan-hoi-bao-cao-15-08.md D8/E2).
- `holdout`    — chỉ XÁC NHẬN một lần, không được dùng để chọn bất cứ thứ gì.

Ngưỡng đọc từ `configs/*.yaml` khoá `surrogate_validation.thresholds`; không hard-code (CLAUDE.md
quy tắc 8). Thiếu ngưỡng ⇒ báo `NOT_CONFIGURED_PENDING_OWNER`, KHÔNG tự đoán một con số.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from qshield_quantum.formulation.surrogate import QuadraticSurrogate

# Ngưỡng nào so theo chiều "càng nhỏ càng tốt" — phần còn lại là "càng lớn càng tốt".
_LOWER_IS_BETTER = frozenset({"mae_max", "rmse_max"})

_METRIC_FOR_THRESHOLD = {
    "mae_max": "mae",
    "rmse_max": "rmse",
    "spearman_min": "spearman",
    "top_k_recall_min": "top_k_recall",
}


@dataclass(frozen=True)
class SplitMetrics:
    """Sai số và độ bảo toàn thứ hạng của surrogate trên MỘT split."""

    split: str
    sample_count: int
    mae: float
    rmse: float
    spearman: float
    top_k: int
    top_k_recall: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SurrogateValidationReport:
    """Kết quả cổng chặn: metric từng split + verdict + lý do fail cụ thể."""

    status: str
    metrics: dict[str, SplitMetrics]
    thresholds: dict[str, float]
    failures: tuple[str, ...]
    threshold_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "threshold_status": self.threshold_status,
            "thresholds": dict(self.thresholds),
            "failures": list(self.failures),
            "metrics": {name: item.to_dict() for name, item in self.metrics.items()},
        }


def _spearman(predicted: np.ndarray, actual: np.ndarray) -> float:
    """Spearman ρ = Pearson trên hạng. Trả `nan` khi một phía hằng số (hạng không xác định)."""
    if len(predicted) < 2:
        return float("nan")
    predicted_rank = np.argsort(np.argsort(predicted)).astype(float)
    actual_rank = np.argsort(np.argsort(actual)).astype(float)
    if predicted_rank.std() == 0.0 or actual_rank.std() == 0.0:
        return float("nan")
    return float(np.corrcoef(predicted_rank, actual_rank)[0, 1])


def _top_k_recall(predicted: np.ndarray, actual: np.ndarray, k: int) -> float:
    """Tỷ lệ top-k thật sự tốt nhất (theo `actual`) được surrogate xếp vào top-k của nó.

    Đây là metric quan trọng nhất cho mục đích dùng surrogate: solver chỉ trả về một pool ứng
    viên rồi Risk rerank lại bằng true objective, nên điều thật sự cần là surrogate KHÔNG ĐÁNH
    RƠI nghiệm tốt — sai số tuyệt đối lệch đều một hằng số thì vô hại.
    """
    take = int(min(k, len(actual)))
    if take < 1:
        return float("nan")
    best_actual = set(np.argsort(actual)[:take].tolist())
    best_predicted = set(np.argsort(predicted)[:take].tolist())
    return len(best_actual & best_predicted) / take


def evaluate_split(
    model: QuadraticSurrogate,
    bit_matrix: np.ndarray,
    targets: np.ndarray,
    *,
    split: str,
    top_k: int,
) -> SplitMetrics:
    """Chấm surrogate trên một split đã decode sẵn thành `(Z, y)`."""
    Z = np.asarray(bit_matrix, dtype=float)
    y = np.asarray(targets, dtype=float)
    if Z.ndim != 2 or Z.shape[1] != model.dimension:
        raise ValueError(
            f"[surrogate.validate] split={split!r} cần ma trận bit "
            f"({len(y)}, {model.dimension}), nhận {Z.shape}."
        )
    if y.shape != (len(Z),):
        raise ValueError(
            f"[surrogate.validate] split={split!r}: targets shape={y.shape}, "
            f"expected {(len(Z),)}."
        )
    if not len(Z):
        raise ValueError(f"[surrogate.validate] split={split!r} rỗng.")
    if top_k < 1:
        raise ValueError(f"[surrogate.validate] top_k must be positive, got {top_k}.")

    predicted = model.evaluate_batch(Z)
    residual = predicted - y
    return SplitMetrics(
        split=split,
        sample_count=len(Z),
        mae=float(np.mean(np.abs(residual))),
        rmse=float(np.sqrt(np.mean(residual**2))),
        spearman=_spearman(predicted, y),
        top_k=int(min(top_k, len(y))),
        top_k_recall=_top_k_recall(predicted, y, top_k),
    )


def _threshold_failures(
    metrics: SplitMetrics, thresholds: Mapping[str, float]
) -> list[str]:
    failures: list[str] = []
    for name, metric_name in _METRIC_FOR_THRESHOLD.items():
        limit = thresholds.get(name)
        if limit is None:
            continue
        observed = getattr(metrics, metric_name)
        if not np.isfinite(observed):
            failures.append(
                f"{metrics.split}.{metric_name}=NOT_FINITE (ngưỡng {name}={limit})"
            )
            continue
        breached = (
            observed > float(limit)
            if name in _LOWER_IS_BETTER
            else observed < float(limit)
        )
        if breached:
            failures.append(
                f"{metrics.split}.{metric_name}={observed:.6g} vi phạm {name}={limit}"
            )
    return failures


def validate_surrogate(
    model: QuadraticSurrogate,
    splits: Mapping[str, tuple[np.ndarray, np.ndarray]],
    *,
    config: Mapping[str, Any],
    gated_splits: Sequence[str] = ("validation", "holdout"),
) -> SurrogateValidationReport:
    """Chấm surrogate trên mọi split được truyền vào, gate theo `gated_splits`.

    `splits` map tên split -> `(Z, y)`. Split `train` (nếu có) vẫn được CHẤM và báo cáo để đối
    chiếu, nhưng KHÔNG BAO GIỜ được gate: surrogate fit trên chính nó nên metric ở đó luôn đẹp và
    không mang thông tin về khả năng khái quát hoá.

    Trả `status`:
    - `PASS`                        — mọi split được gate đều đạt ngưỡng.
    - `FAIL`                        — có ít nhất một vi phạm ngưỡng.
    - `NOT_CONFIGURED_PENDING_OWNER`— config chưa khoá ngưỡng; metric vẫn được tính và báo cáo,
      nhưng KHÔNG suy ra verdict (ngưỡng là quyết định của owner — `surrogate_validation.status`
      trong profile hiện là `PROVISIONAL_PENDING_OWNER`).
    - `NOT_EVALUATED`               — không có split nào ngoài train để chấm.
    """
    raw = config.get("surrogate_validation")
    raw_thresholds = raw.get("thresholds") if isinstance(raw, Mapping) else None
    thresholds = (
        {
            str(key): float(value)
            for key, value in raw_thresholds.items()
            if key in _METRIC_FOR_THRESHOLD and value is not None
        }
        if isinstance(raw_thresholds, Mapping)
        else {}
    )
    top_k = int(
        (raw_thresholds or {}).get("top_k", 20)
        if isinstance(raw_thresholds, Mapping)
        else 20
    )

    metrics = {
        name: evaluate_split(model, Z, y, split=name, top_k=top_k)
        for name, (Z, y) in splits.items()
    }
    gated = [name for name in gated_splits if name in metrics]
    threshold_status = "CONFIGURED" if thresholds else "NOT_CONFIGURED_PENDING_OWNER"

    if not gated:
        status = "NOT_EVALUATED"
        failures: list[str] = []
    elif not thresholds:
        status = "NOT_CONFIGURED_PENDING_OWNER"
        failures = []
    else:
        failures = [
            failure
            for name in gated
            for failure in _threshold_failures(metrics[name], thresholds)
        ]
        status = "FAIL" if failures else "PASS"

    return SurrogateValidationReport(
        status=status,
        metrics=metrics,
        thresholds=thresholds,
        failures=tuple(failures),
        threshold_status=threshold_status,
    )
