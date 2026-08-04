# Nguyễn Anh Tú - GaussianHMM 3 trạng thái, 10 seed, n_iter=500.
"""Fit `GaussianHMM` + ba kiểu suy luận trạng thái.

`filtered` (forward-only) là thứ DUY NHẤT được dùng xuống downstream vì nó nhân quả: xác suất tại
`t` chỉ dùng quan sát đến `t`. `smoothed` (forward-backward, `score_samples`) và `viterbi` nhìn
toàn chuỗi nên CHỈ để chẩn đoán (DR v0.1 §3).

hmmlearn không expose xác suất filtered nên `_forward_log_alpha` tự chạy đệ quy tiến trên log-scale.
Mật độ emission lấy từ `means_`/`covars_` (public) — KHÔNG dùng `_compute_log_likelihood` (private).
`covars_` LUÔN trả ma trận đầy đủ `(K, F, F)` kể cả khi `covariance_type="diag"`, nên một đường
`multivariate_normal` dùng được cho cả hai loại (đã kiểm chứng trên hmmlearn 0.3.3).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from hmmlearn.hmm import GaussianHMM
from scipy.special import logsumexp
from scipy.stats import multivariate_normal

_SUPPORTED_COVARIANCE = ("diag", "full")


def _validate_covariance_type(covariance_type: str) -> None:
    """Chốt chặn dùng chung cho `fit_hmm` và `count_parameters` — cùng một thông báo lỗi."""
    if covariance_type not in _SUPPORTED_COVARIANCE:
        raise ValueError(
            f"covariance_type {covariance_type!r} không hỗ trợ, chỉ có {_SUPPORTED_COVARIANCE}."
        )


@dataclass(frozen=True)
class HmmFit:
    """Một lần fit + các chỉ số dùng để chấm nó. `model` giữ nguyên để suy luận lại."""

    seed: int
    n_states: int
    covariance_type: str
    converged: bool
    log_likelihood_train: float
    log_likelihood_validation: float
    n_parameters: int
    aic: float
    bic: float
    model: GaussianHMM


def fit_hmm(
    x_train: np.ndarray,
    *,
    n_states: int,
    covariance_type: str,
    seed: int,
    n_iter: int,
) -> GaussianHMM:
    """Fit trên MA TRẬN TRAIN đã scale. `random_state=seed` để tái lập được."""
    _validate_covariance_type(covariance_type)
    if len(x_train) <= n_states:
        raise ValueError(
            f"Chỉ có {len(x_train)} quan sát train cho {n_states} trạng thái — không fit được."
        )
    model = GaussianHMM(
        n_components=n_states,
        covariance_type=covariance_type,
        n_iter=n_iter,
        random_state=seed,
    )
    model.fit(x_train)
    return model


def count_parameters(n_states: int, n_features: int, covariance_type: str) -> int:
    """Số tham số tự do — dùng cho AIC/BIC. Tính tay để giải thích được trên slide."""
    start = n_states - 1
    transitions = n_states * (n_states - 1)
    means = n_states * n_features
    _validate_covariance_type(covariance_type)
    if covariance_type == "diag":
        covariances = n_states * n_features
    else:  # "full" — đã được _validate_covariance_type xác nhận hợp lệ
        covariances = n_states * n_features * (n_features + 1) // 2
    return start + transitions + means + covariances


def aic_bic(
    log_likelihood: float, n_parameters: int, n_observations: int
) -> tuple[float, float]:
    """`AIC = -2·LL + 2p`, `BIC = -2·LL + p·ln(T)`."""
    if n_observations < 1:
        raise ValueError(f"n_observations phải >= 1, nhận {n_observations}.")
    aic = -2.0 * log_likelihood + 2.0 * n_parameters
    bic = -2.0 * log_likelihood + n_parameters * float(np.log(n_observations))
    return aic, bic


def emission_log_prob(model: GaussianHMM, x: np.ndarray) -> np.ndarray:
    """`log p(x_t | state=k)` cho mọi `t`, `k` → `(T, K)`.

    Chốt chặn đầu vào cho đường suy diễn NHÂN QUẢ: `filtered_probabilities` →
    `_forward_log_alpha` → hàm này. Một `NaN` duy nhất trong `x` sẽ lan qua
    `log_alpha[step-1]` và đầu độc toàn bộ phần còn lại của chuỗi — artifact regime sẽ hỏng
    im lặng thay vì báo lỗi. CLAUDE.md quy tắc 12: fail fast tại chỗ.

    LƯU Ý: `smoothed_probabilities` và `viterbi_states` gọi thẳng hmmlearn nên KHÔNG đi qua
    chốt chặn này; hmmlearn không báo lỗi tương đương. Chấp nhận được vì cả hai chỉ dùng để
    chẩn đoán, không bao giờ chảy vào artifact.
    """
    if x.ndim != 2 or x.shape[1] != model.n_features:
        raise ValueError(
            f"emission_log_prob: x phải có shape (T, {model.n_features}), nhận {x.shape}."
        )
    if len(x) == 0:
        raise ValueError("emission_log_prob: x rỗng, cần ít nhất một quan sát.")
    if not np.isfinite(x).all():
        bad = np.argwhere(~np.isfinite(x))
        raise ValueError(
            f"emission_log_prob: x chứa {len(bad)} giá trị không hữu hạn, "
            f"đầu tiên tại (hàng={bad[0][0]}, cột={bad[0][1]})."
        )
    return np.column_stack(
        [
            multivariate_normal(
                mean=model.means_[state],
                cov=model.covars_[state],
                allow_singular=True,
            ).logpdf(x)
            for state in range(model.n_components)
        ]
    )


def _forward_log_alpha(model: GaussianHMM, x: np.ndarray) -> np.ndarray:
    """`log α_t(k) = log p(x_1..x_t, state_t=k)` — đệ quy tiến, không nhìn tương lai."""
    log_emission = emission_log_prob(model, x)
    with np.errstate(
        divide="ignore"
    ):  # transmat/startprob có thể chứa 0 ⇒ -inf, hợp lệ
        log_transition = np.log(model.transmat_)
        log_start = np.log(model.startprob_)

    log_alpha = np.empty_like(log_emission)
    log_alpha[0] = log_start + log_emission[0]
    for step in range(1, len(x)):
        log_alpha[step] = (
            logsumexp(log_alpha[step - 1][:, None] + log_transition, axis=0)
            + log_emission[step]
        )
    return log_alpha


def filtered_probabilities(model: GaussianHMM, x: np.ndarray) -> np.ndarray:
    """`p(state_t = k | x_1..x_t)` — NHÂN QUẢ, là thứ duy nhất downstream được dùng."""
    log_alpha = _forward_log_alpha(model, x)
    return np.exp(log_alpha - logsumexp(log_alpha, axis=1, keepdims=True))


def smoothed_probabilities(model: GaussianHMM, x: np.ndarray) -> np.ndarray:
    """`p(state_t = k | toàn chuỗi)` — CHẨN ĐOÁN, không được điều kiện hóa kịch bản bằng cái này."""
    _, posteriors = model.score_samples(x)
    return posteriors


def viterbi_states(model: GaussianHMM, x: np.ndarray) -> np.ndarray:
    """Đường trạng thái khả dĩ nhất trên TOÀN chuỗi — CHẨN ĐOÁN, không nhân quả."""
    return model.predict(x)
