# Nguyễn Anh Tú - test lắp artifact regime: đúng schema hợp đồng + cột chẩn đoán đi kèm.
import numpy as np
import pandas as pd
import pytest
from qshield_ai.regime.output import build_regime_daily
from qshield_contracts.schemas.regime import (
    RegimeDailySchema,
    check_probabilities_sum_to_one,
)
from qshield_contracts.validate import validate_or_raise

LABEL_MAP = {0: "stress", 1: "normal", 2: "volatile"}  # cố tình KHÔNG theo thứ tự id


def _inputs() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    frame = pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=3),
            "split": ["train", "train", "test"],
        }
    )
    filtered = np.array([[0.7, 0.2, 0.1], [0.1, 0.8, 0.1], [0.2, 0.3, 0.5]])
    smoothed = np.array([[0.6, 0.3, 0.1], [0.1, 0.7, 0.2], [0.3, 0.3, 0.4]])
    viterbi = np.array([0, 1, 2])
    return frame, filtered, smoothed, viterbi


def _daily() -> pd.DataFrame:
    frame, filtered, smoothed, viterbi = _inputs()
    return build_regime_daily(
        frame,
        filtered=filtered,
        smoothed=smoothed,
        viterbi=viterbi,
        label_map=LABEL_MAP,
        model_version="hmm-3s-diag-v0.2",
        seed=101,
        feature_version="v0.2",
        run_mode="NON_BASELINE_RUN",
    )


def test_output_passes_the_real_contract_schema() -> None:
    daily = _daily()
    validated = validate_or_raise(daily, RegimeDailySchema, context="test")
    check_probabilities_sum_to_one(validated)


def test_probability_columns_follow_the_label_map_not_the_state_id() -> None:
    """state 0 = 'stress' ⇒ prob_stress ngày đầu phải là 0.7, không phải prob_normal."""
    daily = _daily()
    assert daily.loc[0, "prob_stress"] == pytest.approx(0.7)
    assert daily.loc[0, "prob_normal"] == pytest.approx(0.2)
    assert daily.loc[0, "prob_volatile"] == pytest.approx(0.1)


def test_regime_equals_argmax_of_the_probability_columns() -> None:
    daily = _daily()
    probabilities = daily[["prob_normal", "prob_volatile", "prob_stress"]]
    expected = probabilities.idxmax(axis=1).str.removeprefix("prob_")
    assert daily["regime"].tolist() == expected.tolist()


def test_state_id_is_the_raw_filtered_argmax() -> None:
    daily = _daily()
    assert daily["state_id"].tolist() == [0, 1, 2]


def test_diagnostic_columns_are_present_and_named_apart() -> None:
    daily = _daily()
    for column in (
        "method",
        "inference_status",
        "split",
        "feature_version",
        "run_mode",
        "viterbi_state_id",
        "viterbi_label",
        "prob_normal_smoothed",
        "prob_volatile_smoothed",
        "prob_stress_smoothed",
    ):
        assert column in daily.columns
    assert set(daily["method"]) == {"hmm"}
    assert set(daily["inference_status"]) == {"ok"}


def test_viterbi_label_uses_the_same_map() -> None:
    daily = _daily()
    assert daily["viterbi_label"].tolist() == ["stress", "normal", "volatile"]


def test_no_nulls_anywhere() -> None:
    """Ngày warm-up phải đã bị loại từ build_feature_frame — tới đây không được còn null nào."""
    assert not _daily().isna().to_numpy().any()


def test_length_mismatch_is_rejected() -> None:
    frame, filtered, smoothed, viterbi = _inputs()
    with pytest.raises(ValueError, match="độ dài"):
        build_regime_daily(
            frame,
            filtered=filtered[:2],
            smoothed=smoothed,
            viterbi=viterbi,
            label_map=LABEL_MAP,
            model_version="m",
            seed=1,
            feature_version="v0.2",
            run_mode="NON_BASELINE_RUN",
        )


def test_incomplete_label_map_is_rejected() -> None:
    frame, filtered, smoothed, viterbi = _inputs()
    with pytest.raises(ValueError, match="nhãn"):
        build_regime_daily(
            frame,
            filtered=filtered,
            smoothed=smoothed,
            viterbi=viterbi,
            label_map={0: "stress", 1: "normal", 2: "normal"},
            model_version="m",
            seed=1,
            feature_version="v0.2",
            run_mode="NON_BASELINE_RUN",
        )
