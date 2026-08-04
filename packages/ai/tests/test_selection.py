# Nguyễn Anh Tú - test chọn model: báo cáo đủ mọi candidate, medoid tất định, cổng chặn được.
import numpy as np
import pytest
from qshield_ai.fixtures import synthetic_dataset
from qshield_ai.regime.feature_set import (
    apply_transforms,
    build_feature_frame,
    fit_scaler,
    to_matrix,
)
from qshield_ai.regime.selection import (
    GATE_FAILED,
    GATE_OK,
    label_agreement,
    run_selection,
)

TICKERS = ["AAA", "BBB", "CCC", "DDD"]
MARKET_COLS = ["market_log_return", "realized_vol_20d", "drawdown", "liquidity_20d"]
FEATURES = [*MARKET_COLS, "mean_pairwise_corr_60d"]
FEATURE_COLUMNS = {
    "return_column": "market_log_return",
    "volatility_column": "realized_vol_20d",
    "drawdown_column": "drawdown",
    "correlation_column": "mean_pairwise_corr_60d",
}
CHAMPION = {"n_states": 3, "covariance_type": "diag"}


@pytest.fixture(scope="module")
def prepared():
    returns, market = synthetic_dataset(tickers=TICKERS, n_days=700, seed=11)
    raw_frame = build_feature_frame(
        market, returns, tickers=TICKERS, market_columns=MARKET_COLS, corr_window=60
    )
    frame = apply_transforms(
        raw_frame, {"realized_vol_20d": "log", "mean_pairwise_corr_60d": "fisher_z"}
    )
    scaler = fit_scaler(frame, FEATURES)
    return to_matrix(frame, FEATURES, scaler), frame, raw_frame


def _run(prepared, *, candidates, seeds, min_state_occupancy=0.02):
    matrix, frame, raw_frame = prepared
    return run_selection(
        matrix,
        frame,
        raw_frame,
        candidates=candidates,
        champion=CHAMPION,
        seeds=seeds,
        n_iter=50,
        min_state_occupancy=min_state_occupancy,
        feature_columns=FEATURE_COLUMNS,
    )


def test_label_agreement_matches_hand_calculation() -> None:
    left = np.array(["normal", "stress", "normal", "volatile"])
    right = np.array(["normal", "stress", "volatile", "volatile"])
    assert label_agreement(left, right) == pytest.approx(0.75)  # khớp 3/4


def test_label_agreement_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="độ dài"):
        label_agreement(np.array(["a"]), np.array(["a", "b"]))


def test_label_agreement_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="Không có ngày"):
        label_agreement(np.array([]), np.array([]))


def test_report_has_one_row_per_candidate_and_seed(prepared) -> None:
    """Mọi seed đã đăng ký đều phải xuất hiện — không cherry-pick seed đẹp nhất (DR §5)."""
    outcome = _run(
        prepared,
        candidates={"n_states": [2, 3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    assert len(outcome.report) == 6
    assert sorted(outcome.report["seed"].unique()) == [101, 202, 303]
    assert sorted(outcome.report["n_states"].unique()) == [2, 3]


def test_champion_comes_from_the_pinned_family(prepared) -> None:
    outcome = _run(
        prepared,
        candidates={"n_states": [2, 3, 4], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    assert outcome.gate_status == GATE_OK
    assert outcome.champion is not None
    assert outcome.champion.n_states == 3
    assert outcome.champion.covariance_type == "diag"
    assert outcome.report["is_champion"].sum() == 1


def test_champion_choice_is_deterministic(prepared) -> None:
    first = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    second = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    assert first.gate_status == GATE_OK, f"cổng fail: {first.gate_reasons}"
    assert second.gate_status == GATE_OK, f"cổng fail: {second.gate_reasons}"
    assert first.champion.seed == second.champion.seed
    assert first.label_map == second.label_map


def test_agreement_matrix_is_symmetric_with_unit_diagonal(prepared) -> None:
    outcome = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    matrix = outcome.agreement.to_numpy()
    np.testing.assert_allclose(matrix, matrix.T)
    np.testing.assert_allclose(np.diag(matrix), 1.0)


def test_label_map_covers_all_three_states(prepared) -> None:
    outcome = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202],
    )
    assert set(outcome.label_map) == {0, 1, 2}
    assert set(outcome.label_map.values()) == {"normal", "volatile", "stress"}
    assert outcome.profiles is not None and len(outcome.profiles) == 3


def test_impossible_occupancy_threshold_fails_the_gate(prepared) -> None:
    """Không fit nào hợp lệ ⇒ cổng phải FAIL và champion phải là None, không được chọn bừa."""
    outcome = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202],
        min_state_occupancy=0.99,
    )
    assert outcome.gate_status == GATE_FAILED
    assert outcome.champion is None
    assert outcome.gate_reasons, "fail phải kèm lý do đọc được"
    assert len(outcome.report) == 2, "fit vẫn phải được báo cáo dù bị loại"


def test_mean_label_agreement_matches_hand_calculation(prepared) -> None:
    """Với đúng 2 seed hợp lệ, trung bình đồng thuận của một seed suy giảm còn đúng điểm đồng
    thuận với seed còn lại (không có đường chéo 1.0 nào để pha vào mean). Nếu diagonal lọt vào
    công thức mean, giá trị báo cáo sẽ lệch khỏi con số tính tay này — bắt được bug đó."""
    outcome = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 505],
    )
    assert outcome.gate_status == GATE_OK, f"cổng fail: {outcome.gate_reasons}"
    pairwise = float(outcome.agreement.loc[101, 505])
    champion_rows = outcome.report.loc[
        (outcome.report["n_states"] == 3)
        & (outcome.report["covariance_type"] == "diag")
    ]
    for seed in (101, 505):
        actual = champion_rows.loc[
            champion_rows["seed"] == seed, "mean_label_agreement"
        ]
        assert actual.iloc[0] == pytest.approx(pairwise)


def test_mean_label_agreement_is_nan_outside_champion_family(prepared) -> None:
    """Fix 1 regression: hàng n_states=2 không được mượn điểm đồng thuận của họ champion
    (3/diag) chỉ vì trùng seed — nó chưa từng được chấm đồng thuận, phải giữ NaN."""
    outcome = _run(
        prepared,
        candidates={"n_states": [2, 3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    assert outcome.gate_status == GATE_OK, f"cổng fail: {outcome.gate_reasons}"
    non_champion_rows = outcome.report.loc[outcome.report["n_states"] == 2]
    assert not non_champion_rows.empty
    assert non_champion_rows["mean_label_agreement"].isna().all()


def test_crashed_champion_family_reports_exception_not_convergence(prepared) -> None:
    """Fix 2 regression: ghim champion ở 4 state khiến `label_states` raise cho MỌI fit trong họ
    (chỉ nhận đúng 3 profile). Lý do fail phải nêu tên exception, KHÔNG được nói 'Không seed nào
    hội tụ.' — đó là chẩn đoán sai vì các fit chết trước khi kịp thất bại hội tụ."""
    matrix, frame, raw_frame = prepared
    outcome = run_selection(
        matrix,
        frame,
        raw_frame,
        candidates={"n_states": [4], "covariance_type": ["diag"]},
        champion={"n_states": 4, "covariance_type": "diag"},
        seeds=[101, 202],
        n_iter=50,
        min_state_occupancy=0.02,
        feature_columns=FEATURE_COLUMNS,
    )
    assert outcome.gate_status == GATE_FAILED
    assert outcome.champion is None
    reasons_text = " ".join(outcome.gate_reasons)
    assert "ValueError" in reasons_text
    assert "Không seed nào hội tụ." not in outcome.gate_reasons


def test_report_columns_cover_the_acceptance_criteria(prepared) -> None:
    """AC-REG-002: log-likelihood, AIC, BIC, convergence, occupancy, stability."""
    outcome = _run(
        prepared, candidates={"n_states": [3], "covariance_type": ["diag"]}, seeds=[101]
    )
    required = {
        "n_states",
        "covariance_type",
        "seed",
        "converged",
        "log_likelihood_train",
        "log_likelihood_validation",
        "n_parameters",
        "aic",
        "bic",
        "min_state_occupancy",
        "economic_consistent",
        "violations",
        "mean_label_agreement",
        "is_champion",
    }
    assert required <= set(outcome.report.columns)


@pytest.mark.slow
def test_full_grid_runs(prepared) -> None:
    outcome = _run(
        prepared,
        candidates={"n_states": [2, 3, 4, 5], "covariance_type": ["diag", "full"]},
        seeds=[101, 202, 303, 404, 505, 606, 707, 808, 909, 1001],
    )
    assert len(outcome.report) == 80
    assert outcome.champion is None or outcome.champion.n_states == 3
