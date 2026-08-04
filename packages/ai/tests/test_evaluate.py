# Nguyễn Anh Tú - test chẩn đoán regime: duration, ma trận chuyển, occupancy, ổn định qua seed.
import numpy as np
import pandas as pd
import pytest
from qshield_ai.regime.evaluate import (
    mean_durations,
    occupancy,
    stability_summary,
    transition_matrix,
)

ORDER = ["normal", "volatile", "stress"]
# n n s n s s s — 7 ngày, dùng chung cho ba test tính tay bên dưới.
LABELS = ["normal", "normal", "stress", "normal", "stress", "stress", "stress"]


def test_occupancy_matches_hand_calculation() -> None:
    result = occupancy(LABELS, order=ORDER)
    assert result["normal"] == pytest.approx(3 / 7)
    assert result["volatile"] == pytest.approx(0.0)
    assert result["stress"] == pytest.approx(4 / 7)
    assert sum(result.values()) == pytest.approx(1.0)


def test_mean_durations_match_hand_calculation() -> None:
    """Chuỗi n n | s | n | s s s ⇒ normal có run [2, 1] → 1.5; stress có run [1, 3] → 2.0."""
    result = mean_durations(LABELS, order=ORDER)
    assert result["normal"] == pytest.approx(1.5)
    assert result["stress"] == pytest.approx(2.0)
    assert result["volatile"] == pytest.approx(0.0), "nhãn không xuất hiện ⇒ duration 0"


def test_transition_matrix_matches_hand_calculation() -> None:
    """6 cặp liền kề: n→n, n→s, s→n, n→s, s→s, s→s.

    Hàng normal: n→n 1, n→s 2 trên tổng 3. Hàng stress: s→n 1, s→s 2 trên tổng 3.
    """
    matrix = transition_matrix(LABELS, order=ORDER)

    assert list(matrix.index) == ORDER and list(matrix.columns) == ORDER
    assert matrix.loc["normal", "normal"] == pytest.approx(1 / 3)
    assert matrix.loc["normal", "stress"] == pytest.approx(2 / 3)
    assert matrix.loc["stress", "normal"] == pytest.approx(1 / 3)
    assert matrix.loc["stress", "stress"] == pytest.approx(2 / 3)
    assert matrix.loc["volatile"].sum() == pytest.approx(0.0), (
        "không có chuyển đi ⇒ hàng 0"
    )


def test_transition_rows_sum_to_one_when_the_state_occurs() -> None:
    matrix = transition_matrix(LABELS, order=ORDER)
    for label in ("normal", "stress"):
        assert matrix.loc[label].sum() == pytest.approx(1.0)


def test_stability_summary_matches_hand_calculation() -> None:
    agreement = pd.DataFrame(
        [[1.0, 0.8, 0.6], [0.8, 1.0, 0.7], [0.6, 0.7, 1.0]],
        index=[101, 202, 303],
        columns=[101, 202, 303],
    )
    summary = stability_summary(agreement)

    assert summary["n_seeds"] == 3
    assert summary["mean_agreement"] == pytest.approx(0.7)  # (0.8 + 0.6 + 0.7) / 3
    assert summary["min_agreement"] == pytest.approx(0.6)
    assert summary["max_agreement"] == pytest.approx(0.8)


def test_stability_summary_handles_single_seed() -> None:
    agreement = pd.DataFrame([[1.0]], index=[101], columns=[101])
    summary = stability_summary(agreement)
    assert summary["n_seeds"] == 1
    assert np.isnan(summary["mean_agreement"])


def test_empty_labels_are_rejected() -> None:
    with pytest.raises(ValueError, match="rỗng"):
        occupancy([], order=ORDER)
