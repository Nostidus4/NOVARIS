# Đỗ Ngọc Tân - P0-2: cổng chặn surrogate phải chặn thật, không chỉ tồn tại trong config.
"""`gates.surrogate_validation_required_before_solver: true` từng là khoá config KHÔNG có code nào
đọc — exact/QAOA chạy trên một surrogate chưa ai kiểm định. Các test dưới đây chứng minh cổng chặn
bây giờ: (a) tính đúng metric, (b) FAIL khi surrogate không khái quát hoá, (c) không bao giờ báo
PASS khi thiếu split để chấm, (d) không tự bịa ngưỡng khi config chưa khoá.
"""

from __future__ import annotations

import numpy as np
import pytest
from qshield_quantum.formulation.surrogate import (
    QuadraticSurrogate,
    fit_quadratic_surrogate,
    quadratic_feature_count,
)
from qshield_quantum.formulation.validation import (
    evaluate_split,
    validate_surrogate,
)

_THRESHOLDS = {
    "mae_max": 0.02,
    "rmse_max": 0.03,
    "spearman_min": 0.7,
    "top_k": 20,
    "top_k_recall_min": 0.6,
}
_CONFIG = {"surrogate_validation": {"thresholds": _THRESHOLDS}}


def _linear_model(n: int) -> QuadraticSurrogate:
    return QuadraticSurrogate(
        Q=np.zeros((n, n)),
        linear=-np.arange(1, n + 1, dtype=float),
        constant=0.0,
        residual_sum_squares=0.0,
        rank=quadratic_feature_count(n),
        sample_count=quadratic_feature_count(n),
    )


def _random_bits(rows: int, n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 2, size=(rows, n)).astype(np.int8)


def test_perfect_surrogate_passes_every_threshold() -> None:
    n = 8
    model = _linear_model(n)
    Z = _random_bits(200, n, seed=1)
    y = model.evaluate_batch(Z)  # target = chính surrogate → sai số bằng 0

    report = validate_surrogate(
        model, {"validation": (Z, y), "holdout": (Z, y)}, config=_CONFIG
    )

    assert report.status == "PASS"
    assert report.failures == ()
    assert report.metrics["holdout"].mae == pytest.approx(0.0, abs=1e-12)
    assert report.metrics["holdout"].spearman == pytest.approx(1.0)


def test_surrogate_that_does_not_generalise_fails_the_gate() -> None:
    """Fit trên train nhưng holdout đến từ một hàm KHÁC ⇒ phải FAIL, không được im lặng pass."""
    n = 6
    rng = np.random.default_rng(7)
    required = quadratic_feature_count(n)
    Z_train = rng.integers(0, 2, size=(required * 3, n)).astype(np.int8)
    y_train = Z_train @ np.arange(1, n + 1, dtype=float)
    model = fit_quadratic_surrogate(Z_train, y_train)

    Z_holdout = rng.integers(0, 2, size=(150, n)).astype(np.int8)
    # Mục tiêu holdout đảo dấu: surrogate xếp hạng ngược hoàn toàn.
    y_holdout = -(Z_holdout @ np.arange(1, n + 1, dtype=float)) - 5.0

    report = validate_surrogate(
        model, {"holdout": (Z_holdout, y_holdout)}, config=_CONFIG
    )

    assert report.status == "FAIL"
    assert any("holdout" in failure for failure in report.failures)


def test_train_split_is_reported_but_never_gates() -> None:
    """Surrogate fit trên train nên metric ở đó luôn đẹp — không được dùng nó để kết luận PASS."""
    n = 6
    model = _linear_model(n)
    Z = _random_bits(80, n, seed=3)
    y_good = model.evaluate_batch(Z)
    y_bad = -y_good - 100.0

    report = validate_surrogate(
        model, {"train": (Z, y_good), "holdout": (Z, y_bad)}, config=_CONFIG
    )

    assert "train" in report.metrics, "train vẫn phải được báo cáo để đối chiếu"
    assert report.status == "FAIL", "holdout xấu phải thắng train đẹp"

    only_train = validate_surrogate(model, {"train": (Z, y_good)}, config=_CONFIG)
    assert only_train.status == "NOT_EVALUATED", (
        "chỉ có train thì không có bằng chứng khái quát hoá — không được PASS"
    )


def test_missing_thresholds_reports_pending_owner_instead_of_guessing() -> None:
    n = 5
    model = _linear_model(n)
    Z = _random_bits(50, n, seed=5)
    y = model.evaluate_batch(Z)

    report = validate_surrogate(model, {"holdout": (Z, y)}, config={})

    assert report.status == "NOT_CONFIGURED_PENDING_OWNER"
    assert report.threshold_status == "NOT_CONFIGURED_PENDING_OWNER"
    assert report.thresholds == {}
    # Metric vẫn phải được tính để owner có số mà chốt ngưỡng.
    assert report.metrics["holdout"].sample_count == 50


def test_top_k_recall_counts_overlap_of_best_solutions() -> None:
    """Metric quan trọng nhất: surrogate có đánh rơi nghiệm tốt không (solver chỉ trả pool)."""
    n = 4
    model = _linear_model(n)
    Z = _random_bits(40, n, seed=11)
    y = model.evaluate_batch(Z)

    perfect = evaluate_split(model, Z, y, split="holdout", top_k=10)
    assert perfect.top_k_recall == pytest.approx(1.0)

    shuffled = np.random.default_rng(0).permutation(y)
    scrambled = evaluate_split(model, Z, shuffled, split="holdout", top_k=10)
    assert scrambled.top_k_recall < 1.0


def test_empty_split_is_rejected_rather_than_scored_as_perfect() -> None:
    n = 4
    model = _linear_model(n)
    with pytest.raises(ValueError, match="rỗng"):
        evaluate_split(
            model,
            np.empty((0, n), dtype=np.int8),
            np.empty((0,), dtype=float),
            split="holdout",
            top_k=5,
        )
