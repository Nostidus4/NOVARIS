# Nguyễn Anh Tú - test chọn model: báo cáo đủ mọi candidate, medoid tất định, cổng chặn được.
import numpy as np
import pytest
import qshield_ai.regime.selection as selection_module
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
MIN_MEAN_LABEL_AGREEMENT = (
    0.60  # khớp configs/regime.yaml gate.min_mean_label_agreement
)


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


@pytest.fixture(scope="module")
def prepared_agreeing():
    """Bộ dữ liệu tổng hợp thứ hai (seed sinh dữ liệu khác `prepared`), nơi regime tách bạch đủ
    để nhiều seed HMM đồng thuận nhãn vượt ngưỡng `min_mean_label_agreement`.

    `prepared` (data seed=11) KHÔNG đạt cổng đồng thuận dù dùng đủ 10 seed đã đăng ký — xem
    `test_champion_family_agreement_stays_below_gate_even_with_all_registered_seeds`, đó là phát
    hiện thật về fixture mặc định. Các test dưới đây cần cổng mở để kiểm logic chọn champion nên
    dùng bộ dữ liệu riêng này thay vì hạ ngưỡng cổng để ép `prepared` đi qua.
    """
    returns, market = synthetic_dataset(tickers=TICKERS, n_days=700, seed=5)
    raw_frame = build_feature_frame(
        market, returns, tickers=TICKERS, market_columns=MARKET_COLS, corr_window=60
    )
    frame = apply_transforms(
        raw_frame, {"realized_vol_20d": "log", "mean_pairwise_corr_60d": "fisher_z"}
    )
    scaler = fit_scaler(frame, FEATURES)
    return to_matrix(frame, FEATURES, scaler), frame, raw_frame


def _run(
    prepared,
    *,
    candidates,
    seeds,
    min_state_occupancy=0.02,
    min_mean_label_agreement=MIN_MEAN_LABEL_AGREEMENT,
):
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
        min_mean_label_agreement=min_mean_label_agreement,
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


def test_champion_comes_from_the_pinned_family(prepared_agreeing) -> None:
    outcome = _run(
        prepared_agreeing,
        candidates={"n_states": [2, 3, 4], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    assert outcome.gate_status == GATE_OK, f"cổng fail: {outcome.gate_reasons}"
    assert outcome.champion is not None
    assert outcome.champion.n_states == 3
    assert outcome.champion.covariance_type == "diag"
    assert outcome.report["is_champion"].sum() == 1


def test_champion_choice_is_deterministic(prepared_agreeing) -> None:
    first = _run(
        prepared_agreeing,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    second = _run(
        prepared_agreeing,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    assert first.gate_status == GATE_OK, f"cổng fail: {first.gate_reasons}"
    assert second.gate_status == GATE_OK, f"cổng fail: {second.gate_reasons}"
    assert first.champion.seed == second.champion.seed
    assert first.label_map == second.label_map


def test_agreement_matrix_is_symmetric_with_unit_diagonal(prepared) -> None:
    """Hình dạng ma trận đồng thuận không phụ thuộc cổng có mở hay không, nên vẫn dùng `prepared`
    mặc định — kể cả khi cổng đóng (xem test đồng thuận thấp bên dưới), ma trận vẫn phải đối xứng
    với đường chéo 1.0."""
    outcome = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    matrix = outcome.agreement.to_numpy()
    np.testing.assert_allclose(matrix, matrix.T)
    np.testing.assert_allclose(np.diag(matrix), 1.0)


def test_label_map_covers_all_three_states(prepared_agreeing) -> None:
    outcome = _run(
        prepared_agreeing,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202],
    )
    assert outcome.gate_status == GATE_OK, f"cổng fail: {outcome.gate_reasons}"
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


def test_mean_label_agreement_reduces_to_the_single_pairwise_score(
    prepared_agreeing,
) -> None:
    """Với đúng 2 seed hợp lệ, trung bình đồng thuận của một seed suy giảm còn đúng điểm đồng
    thuận với seed còn lại (không có đường chéo 1.0 nào để pha vào mean). Đây là kiểm tra tự nhất
    quán giữa `report` và `agreement` — KHÔNG phải một ví dụ tính tay độc lập. Nếu diagonal lọt
    vào công thức mean, giá trị báo cáo sẽ lệch khỏi con số này — bắt được bug đó."""
    outcome = _run(
        prepared_agreeing,
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
    (3/diag) chỉ vì trùng seed — nó chưa từng được chấm đồng thuận, phải giữ NaN.

    Fixture `prepared` (data seed=11) chỉ có 1 seed hợp lệ trong họ champion trên 3 seed này ⇒
    mean agreement NaN ⇒ cổng đóng theo AD-04. Cổng đóng không ảnh hưởng gì đến khẳng định ở đây:
    cột `mean_label_agreement` vẫn được điền trước khi trả về (kể cả khi fail), nên hàng n_states=2
    vẫn phải NaN bất kể cổng mở hay đóng."""
    outcome = _run(
        prepared,
        candidates={"n_states": [2, 3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    assert outcome.gate_status == GATE_FAILED, (
        "chỉ 1 seed hợp lệ ⇒ NaN agreement ⇒ cổng đóng"
    )
    non_champion_rows = outcome.report.loc[outcome.report["n_states"] == 2]
    assert not non_champion_rows.empty
    assert non_champion_rows["mean_label_agreement"].isna().all()


def test_low_label_agreement_fails_the_gate(prepared) -> None:
    """Phát hiện gốc của review: seed 101 và 505 trên fixture mặc định chỉ đồng thuận nhãn ~13%
    số ngày — dưới cả mức ngẫu nhiên ~33% cho 3 nhãn. Trước Change 1, đồng thuận chỉ được BÁO CÁO
    chứ không hề bị chặn cổng, nên GATE_OK vẫn được trả về. Giờ phải fail."""
    outcome = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 505],
    )
    assert outcome.gate_status == GATE_FAILED
    assert outcome.champion is None
    assert outcome.label_map is None
    assert outcome.profiles is None
    pairwise = float(outcome.agreement.loc[101, 505])
    assert pairwise < 1 / 3, (
        "đúng bằng chứng review nêu: đồng thuận dưới mức ngẫu nhiên"
    )
    reasons_text = " ".join(outcome.gate_reasons)
    assert "seed 101" in reasons_text
    assert f"min_mean_label_agreement={MIN_MEAN_LABEL_AGREEMENT}" in reasons_text
    assert "2 seed hợp lệ" in reasons_text
    # evidence table vẫn đầy đủ dù cổng đóng
    champion_rows = outcome.report.loc[
        (outcome.report["n_states"] == 3)
        & (outcome.report["covariance_type"] == "diag")
    ]
    assert champion_rows["mean_label_agreement"].notna().all()
    assert champion_rows["is_champion"].sum() == 1


def test_single_eligible_seed_reports_nan_agreement_and_fails_the_gate(
    prepared,
) -> None:
    """Chỉ 1 seed hợp lệ ⇒ không có cặp nào để so ⇒ mean agreement phải là NaN (Change 2), và
    NaN >= ngưỡng luôn sai ⇒ cổng đóng (Change 1). Đây là scenario mặc định của fixture `prepared`
    sau khi fix rò rỉ dữ liệu — xem docstring `configs/regime.yaml` `gate.min_mean_label_agreement`.
    """
    outcome = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303],
    )
    assert outcome.gate_status == GATE_FAILED
    assert outcome.champion is None
    assert len(outcome.agreement) == 1
    reasons_text = " ".join(outcome.gate_reasons)
    assert "seed 101" in reasons_text
    assert "nan" in reasons_text.lower()
    assert "1 seed hợp lệ" in reasons_text


def test_champion_family_agreement_stays_below_gate_even_with_all_registered_seeds(
    prepared,
) -> None:
    """Phát hiện thật về fixture mặc định (data seed=11), không phải bug: ngay cả dùng đủ 10 seed
    đã đăng ký trong configs/regime.yaml, đồng thuận trung bình cao nhất trong họ champion
    (~0.55) vẫn dưới ngưỡng 0.60 — cổng đóng là hành vi đúng của AD-04, dữ liệu tổng hợp seed=11
    này không tạo ra state đủ tách bạch để 10 seed đồng thuận với nhau."""
    outcome = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202, 303, 404, 505, 606, 707, 808, 909, 1001],
    )
    assert outcome.gate_status == GATE_FAILED
    assert outcome.champion is None
    best_agreement = max(
        float(outcome.agreement.loc[seed].drop(index=seed).mean())
        for seed in outcome.agreement.index
    )
    assert best_agreement < MIN_MEAN_LABEL_AGREEMENT


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
        min_mean_label_agreement=MIN_MEAN_LABEL_AGREEMENT,
        feature_columns=FEATURE_COLUMNS,
    )
    assert outcome.gate_status == GATE_FAILED
    assert outcome.champion is None
    reasons_text = " ".join(outcome.gate_reasons)
    assert "ValueError" in reasons_text
    assert "Không seed nào hội tụ." not in outcome.gate_reasons


def test_exception_before_convergence_flag_reports_exception_not_convergence(
    prepared, monkeypatch
) -> None:
    """Đường untested review nêu ra: test hội tụ-hay-exception hiện có làm exception ném ra từ
    `label_states`, chạy SAU `row.update(converged=...)` — nên `converged` đã là True trên các
    hàng đó và guard `ran` trong `_failure_reasons` chưa từng bị exercise với `converged` còn ở
    giá trị khởi tạo False. Ở đây buộc exception ném ra từ `fit_hmm` — TRƯỚC khi `converged` được
    gán — để guard đó chạy đúng đường mã lệnh của nó."""
    monkeypatch.setattr(
        selection_module,
        "fit_hmm",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("fit nổ trước khi hội tụ")
        ),
    )
    outcome = _run(
        prepared,
        candidates={"n_states": [3], "covariance_type": ["diag"]},
        seeds=[101, 202],
    )
    assert outcome.gate_status == GATE_FAILED
    assert outcome.champion is None
    reasons_text = " ".join(outcome.gate_reasons)
    assert "RuntimeError" in reasons_text
    assert "Không seed nào hội tụ." not in outcome.gate_reasons
    champion_rows = outcome.report.loc[
        (outcome.report["n_states"] == 3)
        & (outcome.report["covariance_type"] == "diag")
    ]
    assert not champion_rows["converged"].any(), (
        "converged phải giữ nguyên False khởi tạo"
    )


def test_champion_family_absent_from_grid_reports_family_not_in_grid(prepared) -> None:
    """Đường untested review nêu ra: `family.empty` — champion bị ghim vào (n_states,
    covariance_type) không nằm trong `candidates` thì không có fit nào để chấm cả. Lý do fail
    phải nói rõ là họ champion vắng mặt trong lưới, không phải chẩn đoán nhầm sang hội tụ hay
    ngưỡng occupancy/đồng thuận."""
    matrix, frame, raw_frame = prepared
    outcome = run_selection(
        matrix,
        frame,
        raw_frame,
        candidates={"n_states": [2], "covariance_type": ["diag"]},
        champion={"n_states": 3, "covariance_type": "diag"},
        seeds=[101],
        n_iter=50,
        min_state_occupancy=0.02,
        min_mean_label_agreement=MIN_MEAN_LABEL_AGREEMENT,
        feature_columns=FEATURE_COLUMNS,
    )
    assert outcome.gate_status == GATE_FAILED
    assert outcome.champion is None
    assert len(outcome.gate_reasons) == 1
    assert "không có trong" in outcome.gate_reasons[0]
    assert "lưới candidates" in outcome.gate_reasons[0]


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
