# Nguyễn Anh Tú - test gán nhãn theo THỐNG KÊ (quy tắc 7), điểm stress tính tay, cổng nhất quán.
import numpy as np
import pandas as pd
import pytest
from qshield_ai.regime.labeling import (
    StateProfile,
    economic_consistency_violations,
    label_states,
    state_profiles,
)

COLUMNS = {
    "return_column": "market_log_return",
    "volatility_column": "realized_vol_20d",
    "drawdown_column": "drawdown",
    "correlation_column": "mean_pairwise_corr_60d",
}


def _frame(volatility, returns, drawdown, correlation) -> pd.DataFrame:
    """Mỗi state 2 dòng giá trị giống hệt nhau ⇒ trung bình theo state là chính giá trị đó."""
    return pd.DataFrame(
        {
            "realized_vol_20d": np.repeat(volatility, 2),
            "market_log_return": np.repeat(returns, 2),
            "drawdown": np.repeat(drawdown, 2),
            "mean_pairwise_corr_60d": np.repeat(correlation, 2),
        }
    )


def _states() -> np.ndarray:
    return np.array([0, 0, 1, 1, 2, 2])


def test_stress_score_matches_hand_calculation() -> None:
    """Giá trị [1,2,3]: trung bình 2, độ lệch chuẩn tổng thể sqrt(2/3)
    ⇒ z = ∓sqrt(3/2), 0, ±sqrt(3/2).

    vol z  = [-√1.5, 0, +√1.5]; return z = [+√1.5, 0, -√1.5]; |drawdown| z = [-√1.5, 0, +√1.5].
    stress = z(vol) − z(return) + z(|drawdown|) ⇒ [−3√1.5, 0, +3√1.5].
    """
    frame = _frame(
        [1.0, 2.0, 3.0], [3.0, 2.0, 1.0], [-1.0, -2.0, -3.0], [0.1, 0.2, 0.3]
    )
    profiles = state_profiles(frame, _states(), **COLUMNS)

    expected = 3.0 * np.sqrt(1.5)
    assert profiles[0].stress_score == pytest.approx(-expected)
    assert profiles[1].stress_score == pytest.approx(0.0, abs=1e-12)
    assert profiles[2].stress_score == pytest.approx(expected)


def test_profiles_report_means_and_occupancy() -> None:
    frame = _frame(
        [1.0, 2.0, 3.0], [3.0, 2.0, 1.0], [-1.0, -2.0, -3.0], [0.1, 0.2, 0.3]
    )
    profiles = state_profiles(frame, _states(), **COLUMNS)

    assert [profile.state_id for profile in profiles] == [0, 1, 2]
    assert profiles[1].mean_volatility == pytest.approx(2.0)
    assert profiles[1].mean_return == pytest.approx(2.0)
    assert profiles[1].mean_drawdown == pytest.approx(-2.0)
    assert profiles[1].mean_correlation == pytest.approx(0.2)
    assert sum(profile.occupancy for profile in profiles) == pytest.approx(1.0)


def test_labels_follow_the_statistical_ranking_not_the_state_id() -> None:
    """State id 0 có volatility THẤP nhất ⇒ phải là 'normal', dù id của nó là 0 (quy tắc 7)."""
    frame = _frame(
        [1.0, 2.0, 3.0], [3.0, 2.0, 1.0], [-1.0, -2.0, -3.0], [0.1, 0.2, 0.3]
    )
    profiles = state_profiles(frame, _states(), **COLUMNS)

    assert label_states(profiles) == {0: "normal", 1: "volatile", 2: "stress"}


def test_labels_flip_when_the_statistics_flip() -> None:
    """Cùng state id, đảo thống kê ⇒ nhãn phải đảo theo. Nếu không, code đang gán theo id."""
    frame = _frame(
        [3.0, 2.0, 1.0], [1.0, 2.0, 3.0], [-3.0, -2.0, -1.0], [0.3, 0.2, 0.1]
    )
    profiles = state_profiles(frame, _states(), **COLUMNS)

    assert label_states(profiles) == {0: "stress", 1: "volatile", 2: "normal"}


def test_ties_break_on_state_id_deterministically() -> None:
    frame = _frame(
        [2.0, 2.0, 2.0], [2.0, 2.0, 2.0], [-2.0, -2.0, -2.0], [0.2, 0.2, 0.2]
    )
    profiles = state_profiles(frame, _states(), **COLUMNS)

    assert label_states(profiles) == {0: "stress", 1: "volatile", 2: "normal"}


def test_label_states_requires_exactly_three_states() -> None:
    frame = _frame([1.0, 2.0], [2.0, 1.0], [-1.0, -2.0], [0.1, 0.2])
    profiles = state_profiles(frame, np.array([0, 0, 1, 1]), **COLUMNS)
    with pytest.raises(ValueError, match="3 trạng thái"):
        label_states(profiles)


def test_consistent_profiles_report_no_violation() -> None:
    frame = _frame(
        [1.0, 2.0, 3.0], [3.0, 2.0, 1.0], [-1.0, -2.0, -3.0], [0.1, 0.2, 0.3]
    )
    profiles = state_profiles(frame, _states(), **COLUMNS)
    label_map = label_states(profiles)
    assert economic_consistency_violations(profiles, label_map) == []


def test_stress_with_lower_volatility_than_normal_is_a_violation() -> None:
    """Điểm tổng hợp có thể xếp một state lên đầu nhờ drawdown trong khi volatility lại thấp hơn
    normal — đó là state vô nghĩa về kinh tế, phải bị bắt chứ không được gán nhãn im lặng."""
    profiles = (
        StateProfile(0, 0.5, 0.01, 5.0, -0.01, 0.2, -1.0),  # normal: volatility 5.0
        StateProfile(1, 0.3, 0.00, 3.0, -0.05, 0.3, 0.0),
        StateProfile(2, 0.2, -0.02, 1.0, -0.40, 0.5, 1.0),  # "stress": volatility 1.0
    )
    label_map = {0: "normal", 1: "volatile", 2: "stress"}
    violations = economic_consistency_violations(profiles, label_map)

    assert len(violations) == 1
    assert "volatility" in violations[0]


def test_stress_with_higher_return_than_normal_is_a_violation() -> None:
    profiles = (
        StateProfile(0, 0.5, -0.02, 1.0, -0.01, 0.2, -1.0),  # normal: return âm
        StateProfile(1, 0.3, 0.00, 2.0, -0.05, 0.3, 0.0),
        StateProfile(
            2, 0.2, 0.05, 3.0, -0.40, 0.5, 1.0
        ),  # "stress": return dương cao hơn
    )
    label_map = {0: "normal", 1: "volatile", 2: "stress"}
    violations = economic_consistency_violations(profiles, label_map)

    assert len(violations) == 1
    assert "return" in violations[0]


def test_state_profiles_rejects_length_mismatch() -> None:
    frame = _frame(
        [1.0, 2.0, 3.0], [3.0, 2.0, 1.0], [-1.0, -2.0, -3.0], [0.1, 0.2, 0.3]
    )
    with pytest.raises(ValueError, match="độ dài"):
        state_profiles(frame, np.array([0, 1]), **COLUMNS)
