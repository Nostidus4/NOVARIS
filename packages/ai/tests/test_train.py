# Nguyễn Anh Tú - test HMM: filtered là nhân quả, AIC/BIC tính tay, fit tất định theo seed.
import numpy as np
import pytest
from qshield_ai.fixtures import synthetic_dataset
from qshield_ai.regime.feature_set import (
    apply_transforms,
    build_feature_frame,
    fit_scaler,
    to_matrix,
)
from qshield_ai.regime.train import (
    aic_bic,
    count_parameters,
    emission_log_prob,
    filtered_probabilities,
    fit_hmm,
    smoothed_probabilities,
    viterbi_states,
)

TICKERS = ["AAA", "BBB", "CCC", "DDD"]
MARKET_COLS = ["market_log_return", "realized_vol_20d", "drawdown", "liquidity_20d"]
FEATURES = [*MARKET_COLS, "mean_pairwise_corr_60d"]


@pytest.fixture(scope="module")
def matrix_and_frame() -> tuple[np.ndarray, object]:
    returns, market = synthetic_dataset(tickers=TICKERS, n_days=700, seed=11)
    frame = build_feature_frame(
        market, returns, tickers=TICKERS, market_columns=MARKET_COLS, corr_window=60
    )
    frame = apply_transforms(
        frame, {"realized_vol_20d": "log", "mean_pairwise_corr_60d": "fisher_z"}
    )
    scaler = fit_scaler(frame, FEATURES)
    return to_matrix(frame, FEATURES, scaler), frame


@pytest.fixture(scope="module")
def fitted(matrix_and_frame):
    matrix, frame = matrix_and_frame
    train = matrix[(frame["split"] == "train").to_numpy()]
    return fit_hmm(
        train, n_states=3, covariance_type="diag", seed=101, n_iter=200
    ), matrix


def test_count_parameters_matches_hand_calculation() -> None:
    """K=3, F=5, diag: start 2 + trans 6 + means 15 + covars 15 = 38."""
    assert count_parameters(3, 5, "diag") == 38
    # full: covars = 3 * 5 * 6 / 2 = 45 ⇒ 2 + 6 + 15 + 45 = 68
    assert count_parameters(3, 5, "full") == 68


def test_count_parameters_rejects_unknown_covariance() -> None:
    with pytest.raises(ValueError, match="covariance_type"):
        count_parameters(3, 5, "tied")


def test_aic_bic_match_hand_calculation() -> None:
    """loglik=-100, p=10, T=100 ⇒ AIC = 200 + 20 = 220; BIC = 200 + 10*ln(100)."""
    aic, bic = aic_bic(-100.0, 10, 100)
    assert aic == pytest.approx(220.0)
    assert bic == pytest.approx(200.0 + 10.0 * np.log(100.0))


def test_fit_is_deterministic_for_a_seed(matrix_and_frame) -> None:
    matrix, frame = matrix_and_frame
    train = matrix[(frame["split"] == "train").to_numpy()]
    first = fit_hmm(train, n_states=3, covariance_type="diag", seed=7, n_iter=50)
    second = fit_hmm(train, n_states=3, covariance_type="diag", seed=7, n_iter=50)
    np.testing.assert_allclose(first.means_, second.means_)


def test_filtered_rows_are_probability_distributions(fitted) -> None:
    model, matrix = fitted
    filtered = filtered_probabilities(model, matrix)
    assert filtered.shape == (len(matrix), 3)
    np.testing.assert_allclose(filtered.sum(axis=1), 1.0, atol=1e-10)
    assert (filtered >= 0).all()


def test_filtered_is_causal_prefix_stable(fitted) -> None:
    """Cốt lõi của quy tắc 4: xác suất tại t không đổi khi có thêm quan sát SAU t."""
    model, matrix = fitted
    cutoff = 200
    full = filtered_probabilities(model, matrix)
    prefix = filtered_probabilities(model, matrix[:cutoff])
    np.testing.assert_allclose(prefix, full[:cutoff], atol=1e-12)


def test_filtered_equals_smoothed_at_the_final_observation(fitted) -> None:
    """Bất biến toán học: tại quan sát cuối, forward-only trùng forward-backward."""
    model, matrix = fitted
    filtered = filtered_probabilities(model, matrix)
    smoothed = smoothed_probabilities(model, matrix)
    np.testing.assert_allclose(filtered[-1], smoothed[-1], atol=1e-8)


def test_filtered_differs_from_smoothed_mid_series(fitted) -> None:
    """Trùng nhau khắp nơi ⇒ forward recursion đang chạy sai (hoặc dữ liệu bão hòa)."""
    model, matrix = fitted
    filtered = filtered_probabilities(model, matrix)
    smoothed = smoothed_probabilities(model, matrix)
    # Cắt hai đầu: tại t=0 hai phân phối luôn lệch mạnh, tại t=T-1 chúng luôn trùng khớp.
    # Chỉ phần GIỮA mới là bằng chứng recursion chạy tiến thật, đúng như tên test.
    interior = slice(10, -10)
    assert np.abs(filtered[interior] - smoothed[interior]).max() > 0.05


def test_forward_recursion_reproduces_model_log_likelihood(fitted) -> None:
    """Tổng xác suất forward tại bước cuối phải bằng log-likelihood hmmlearn tự tính."""
    from qshield_ai.regime.train import _forward_log_alpha
    from scipy.special import logsumexp

    model, matrix = fitted
    log_alpha = _forward_log_alpha(model, matrix)
    assert logsumexp(log_alpha[-1]) == pytest.approx(model.score(matrix), rel=1e-9)


def test_viterbi_returns_valid_state_ids(fitted) -> None:
    model, matrix = fitted
    states = viterbi_states(model, matrix)
    assert states.shape == (len(matrix),)
    assert set(np.unique(states)) <= {0, 1, 2}


def test_emission_log_prob_rejects_nan_and_names_location(fitted) -> None:
    """Một NaN duy nhất phải chặn ngay tại emission_log_prob, và lỗi phải chỉ đúng vị trí."""
    model, matrix = fitted
    bad = matrix[:6].copy()
    bad[3, 2] = np.nan
    with pytest.raises(ValueError, match=r"hàng=3, cột=2"):
        emission_log_prob(model, bad)


def test_emission_log_prob_rejects_wrong_width(fitted) -> None:
    model, matrix = fitted
    # Khớp cả tiền tố hàm: scipy cũng raise ValueError chứa "shape" khi lệch cột, nên
    # match="shape" đơn thuần vẫn pass dù chốt chặn bị xóa — không bảo vệ được gì.
    with pytest.raises(ValueError, match=r"emission_log_prob: x phải có shape"):
        emission_log_prob(model, matrix[:, :3])


def test_emission_log_prob_rejects_empty(fitted) -> None:
    model, matrix = fitted
    with pytest.raises(ValueError, match="rỗng"):
        emission_log_prob(model, matrix[:0])


def test_filtered_probabilities_rejects_non_finite_input(fitted) -> None:
    """Chốt chặn ở emission_log_prob phải bảo vệ luôn đường downstream filtered_probabilities."""
    model, matrix = fitted
    bad = matrix[:6].copy()
    bad[3, 2] = np.nan
    with pytest.raises(ValueError, match="không hữu hạn"):
        filtered_probabilities(model, bad)
