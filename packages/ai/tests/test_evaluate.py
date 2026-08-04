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


def test_single_element_sequence_matches_hand_calculation() -> None:
    """Một phần tử ["normal"]: occupancy normal=1.0, còn lại 0.0.

    Một run duy nhất dài 1 ⇒ mean duration normal=1.0. Không có cặp liền kề nào (pairwise của
    chuỗi 1 phần tử rỗng) ⇒ mọi hàng của transition matrix đều toàn 0.
    """
    labels = ["normal"]

    occ = occupancy(labels, order=ORDER)
    assert occ["normal"] == pytest.approx(1.0)
    assert occ["volatile"] == pytest.approx(0.0)
    assert occ["stress"] == pytest.approx(0.0)

    durations = mean_durations(labels, order=ORDER)
    assert durations["normal"] == pytest.approx(1.0)
    assert durations["volatile"] == pytest.approx(0.0)
    assert durations["stress"] == pytest.approx(0.0)

    matrix = transition_matrix(labels, order=ORDER)
    for label in ORDER:
        assert matrix.loc[label].sum() == pytest.approx(0.0), (
            "không cặp liền kề ⇒ hàng 0"
        )


def test_all_one_regime_sequence_matches_hand_calculation() -> None:
    """["stress"] * 5: occupancy stress=1.0, còn lại 0.0.

    Một run duy nhất dài 5 ⇒ mean duration stress=5.0, còn lại 0.0. 4 cặp liền kề đều
    stress→stress ⇒ hàng stress có xác suất tự chuyển 1.0, các hàng khác toàn 0.
    """
    labels = ["stress"] * 5

    occ = occupancy(labels, order=ORDER)
    assert occ["stress"] == pytest.approx(1.0)
    assert occ["normal"] == pytest.approx(0.0)
    assert occ["volatile"] == pytest.approx(0.0)

    durations = mean_durations(labels, order=ORDER)
    assert durations["stress"] == pytest.approx(5.0)
    assert durations["normal"] == pytest.approx(0.0)
    assert durations["volatile"] == pytest.approx(0.0)

    matrix = transition_matrix(labels, order=ORDER)
    assert matrix.loc["stress", "stress"] == pytest.approx(1.0)
    assert matrix.loc["stress", "normal"] == pytest.approx(0.0)
    assert matrix.loc["stress", "volatile"] == pytest.approx(0.0)
    for label in ("normal", "volatile"):
        assert matrix.loc[label].sum() == pytest.approx(0.0), "không xuất hiện ⇒ hàng 0"


def test_label_outside_order_raises_value_error_with_context() -> None:
    """Nhãn "unknown" không có trong ORDER phải nổ ngay, kèm tên hàm và nhãn lạ trong message."""
    labels_with_unknown = [*LABELS, "unknown"]

    with pytest.raises(ValueError, match="unknown") as occ_err:
        occupancy(labels_with_unknown, order=ORDER)
    assert "occupancy" in str(occ_err.value)

    with pytest.raises(ValueError, match="unknown") as dur_err:
        mean_durations(labels_with_unknown, order=ORDER)
    assert "mean_durations" in str(dur_err.value)

    with pytest.raises(ValueError, match="unknown") as trans_err:
        transition_matrix(labels_with_unknown, order=ORDER)
    assert "transition_matrix" in str(trans_err.value)
