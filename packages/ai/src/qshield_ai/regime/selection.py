# Nguyễn Anh Tú - chọn model theo converged + val log-likelihood + BIC/AIC + stability, không chỉ theo AIC/BIC thấp nhất.
"""Chạy lưới candidate, báo cáo TẤT CẢ, rồi chọn champion bằng medoid độ đồng thuận nhãn.

AD-03: lưới `n_states × covariance_type × seed` được báo cáo đầy đủ (PR-REG-002, AC-REG-001/002),
nhưng champion bị ghim ở `3/diag` — `RegimeDailySchema` chặn `state_id` ở `{0,1,2}` nên model rộng
hơn không bao giờ ghi được ra artifact hợp đồng.

AD-04: champion = seed có mức đồng thuận nhãn trung bình cao nhất với các seed hợp lệ còn lại
(medoid — nghiệm "điển hình" nhất, không phải nghiệm may nhất). Hòa thì val log-likelihood cao hơn
thắng, rồi đến seed nhỏ hơn. Đồng thuận đo trên train+validation, KHÔNG dùng test.

Cổng còn chặn theo `min_mean_label_agreement` (config `gate`): đồng thuận trung bình của chính
champion phải đạt ngưỡng đó, nếu không cổng đóng (`GATE_FAILED`) dù đã xác định được medoid — một
medoid không đồng thuận với các seed khác không phải bằng chứng fit ổn định. Chỉ 1 seed hợp lệ thì
đồng thuận trung bình là NaN và luôn trượt ngưỡng — cố ý, vì không có gì để so sánh chéo.

`log_likelihood_validation` tính bằng `model.score` trên đoạn validation như một chuỗi độc lập —
đây là chỉ số so sánh giữa các candidate, không phải likelihood có điều kiện theo train.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

from qshield_ai.regime.labeling import (
    StateProfile,
    economic_consistency_violations,
    label_states,
    state_profiles,
)
from qshield_ai.regime.train import (
    HmmFit,
    aic_bic,
    count_parameters,
    filtered_probabilities,
    fit_hmm,
)

GATE_OK = "OK"
GATE_FAILED = "HMM_FAILED"


@dataclass(frozen=True)
class SelectionOutcome:
    """Kết quả vòng chọn model. `champion is None` ⇔ `gate_status == GATE_FAILED`."""

    champion: HmmFit | None
    label_map: dict[int, str] | None
    profiles: tuple[StateProfile, ...] | None
    report: pd.DataFrame
    agreement: pd.DataFrame
    gate_status: str
    gate_reasons: list[str]


def label_agreement(left: np.ndarray, right: np.ndarray) -> float:
    """Tỷ lệ ngày hai chuỗi nhãn trùng nhau.

    Nhãn đã gán theo thống kê nên so sánh được chéo seed.
    """
    if len(left) != len(right):
        raise ValueError(f"Hai chuỗi nhãn lệch độ dài: {len(left)} vs {len(right)}.")
    if len(left) == 0:
        raise ValueError("Không có ngày nào để so sánh nhãn.")
    return float(np.mean(np.asarray(left) == np.asarray(right)))


def _candidate_labels(
    model,
    matrix: np.ndarray,
    raw_frame: pd.DataFrame,
    feature_columns: Mapping[str, str],
    stability_mask: np.ndarray,
) -> tuple[np.ndarray, dict[int, str], tuple[StateProfile, ...], list[str]]:
    """Suy luận filtered trên TOÀN chuỗi, nhưng hồ sơ/nhãn/vi phạm chỉ học trên train+validation.

    CLAUDE.md quy tắc 4: quyết định chọn model không được nhìn test. Nhãn từng ngày thì vẫn
    phải phủ cả test vì artifact cần nhãn cho mọi ngày — `filtered_probabilities` là nhân quả
    nên điều đó không rò rỉ tương lai.
    """
    states = filtered_probabilities(model, matrix).argmax(axis=1)
    profiles = state_profiles(
        raw_frame.loc[stability_mask], states[stability_mask], **feature_columns
    )
    label_map = label_states(profiles)
    violations = economic_consistency_violations(profiles, label_map)
    labels = np.array([label_map[int(state)] for state in states])
    return labels, label_map, profiles, violations


def run_selection(
    matrix: np.ndarray,
    frame: pd.DataFrame,
    raw_frame: pd.DataFrame,
    *,
    candidates: Mapping[str, Sequence],
    champion: Mapping[str, Any],
    seeds: Sequence[int],
    n_iter: int,
    min_state_occupancy: float,
    min_mean_label_agreement: float,
    feature_columns: Mapping[str, str],
) -> SelectionOutcome:
    """Fit toàn lưới, báo cáo tất cả, chọn champion trong họ đã ghim."""
    train_mask = (frame["split"] == "train").to_numpy()
    validation_mask = (frame["split"] == "validation").to_numpy()
    stability_mask = train_mask | validation_mask
    x_train = matrix[train_mask]
    x_validation = matrix[validation_mask]
    n_features = matrix.shape[1]

    champion_states = int(champion["n_states"])
    champion_covariance = str(champion["covariance_type"])

    rows: list[dict] = []
    eligible: dict[
        int, tuple[HmmFit, np.ndarray, dict[int, str], tuple[StateProfile, ...]]
    ] = {}

    for n_states, covariance_type in product(
        candidates["n_states"], candidates["covariance_type"]
    ):
        for seed in seeds:
            row: dict = {
                "n_states": int(n_states),
                "covariance_type": str(covariance_type),
                "seed": int(seed),
                "converged": False,
                "log_likelihood_train": float("nan"),
                "log_likelihood_validation": float("nan"),
                "n_parameters": count_parameters(
                    int(n_states), n_features, str(covariance_type)
                ),
                "aic": float("nan"),
                "bic": float("nan"),
                "min_state_occupancy": float("nan"),
                "economic_consistent": None,
                "violations": "",
                "mean_label_agreement": float("nan"),
                "is_champion": False,
                "error": "",
            }
            try:
                model = fit_hmm(
                    x_train,
                    n_states=int(n_states),
                    covariance_type=str(covariance_type),
                    seed=int(seed),
                    n_iter=n_iter,
                )
                log_likelihood_train = float(model.score(x_train))
                log_likelihood_validation = (
                    float(model.score(x_validation))
                    if len(x_validation)
                    else float("nan")
                )
                aic, bic = aic_bic(
                    log_likelihood_train, row["n_parameters"], len(x_train)
                )
                states = filtered_probabilities(model, matrix).argmax(axis=1)
                gated_states = states[stability_mask]
                occupancy = np.bincount(gated_states, minlength=int(n_states)) / len(
                    gated_states
                )

                row.update(
                    converged=bool(model.monitor_.converged),
                    log_likelihood_train=log_likelihood_train,
                    log_likelihood_validation=log_likelihood_validation,
                    aic=aic,
                    bic=bic,
                    min_state_occupancy=float(occupancy.min()),
                )

                fit = HmmFit(
                    seed=int(seed),
                    n_states=int(n_states),
                    covariance_type=str(covariance_type),
                    converged=bool(model.monitor_.converged),
                    log_likelihood_train=log_likelihood_train,
                    log_likelihood_validation=log_likelihood_validation,
                    n_parameters=row["n_parameters"],
                    aic=aic,
                    bic=bic,
                    model=model,
                )

                is_champion_family = (
                    int(n_states) == champion_states
                    and str(covariance_type) == champion_covariance
                )
                if is_champion_family:
                    labels, label_map, profiles, violations = _candidate_labels(
                        model, matrix, raw_frame, feature_columns, stability_mask
                    )
                    row["economic_consistent"] = not violations
                    row["violations"] = "; ".join(violations)
                    if (
                        fit.converged
                        and not violations
                        and row["min_state_occupancy"] >= min_state_occupancy
                    ):
                        eligible[int(seed)] = (fit, labels, label_map, profiles)
            except Exception as error:  # noqa: BLE001 — fit hỏng là dữ liệu báo cáo, không phải lỗi
                row["error"] = f"{type(error).__name__}: {error}"
            rows.append(row)

    report = pd.DataFrame(rows)
    agreement = _agreement_matrix(eligible, stability_mask)

    if not eligible:
        reasons = _failure_reasons(
            report, champion_states, champion_covariance, min_state_occupancy
        )
        return SelectionOutcome(
            None, None, None, report, agreement, GATE_FAILED, reasons
        )

    mean_agreement = {
        # 1 seed hợp lệ ⇒ zero cặp để so — KHÔNG phải bằng chứng đồng thuận hoàn hảo (1.0).
        # Cùng nguyên tắc đã áp dụng cho hàng ngoài họ champion: chưa từng chấm thì phải là NaN.
        seed: float(agreement.loc[seed].drop(index=seed).mean())
        if len(agreement) > 1
        else float("nan")
        for seed in eligible
    }

    def _ranking_key(seed: int) -> tuple[float, float, int]:
        """NaN (mean_agreement lẫn val-log-likelihood) phải xếp CUỐI bằng sentinel hữu hạn trong
        khóa sắp xếp — cột report vẫn giữ NaN nguyên vẹn, sentinel chỉ sống trong hàm này. Nếu
        không, tie-break theo seed không chạy được (so sánh với NaN luôn False).

        Với đúng 1 seed hợp lệ, `min` trên tập một phần tử không bao giờ so sánh nên sentinel này
        không đổi kết quả — vẫn viết đúng vì phòng thủ, không phải vì cần thiết ở đây.
        """
        agreement_score = mean_agreement[seed]
        validation = eligible[seed][0].log_likelihood_validation
        return (
            -agreement_score if np.isfinite(agreement_score) else float("inf"),
            -validation if np.isfinite(validation) else float("inf"),
            seed,
        )

    best_seed = min(eligible, key=_ranking_key)
    fit, _, label_map, profiles = eligible[best_seed]
    champion_agreement = mean_agreement[best_seed]

    champion_family_rows = (report["n_states"] == champion_states) & (
        report["covariance_type"] == champion_covariance
    )
    report.loc[champion_family_rows, "mean_label_agreement"] = (
        report.loc[champion_family_rows, "seed"].map(mean_agreement).astype(float)
    )
    report.loc[
        (report["seed"] == best_seed)
        & (report["n_states"] == champion_states)
        & (report["covariance_type"] == champion_covariance),
        "is_champion",
    ] = True

    # `not (x >= threshold)` thay vì `x < threshold`: NaN so sánh nào cũng False, nên `x < t` để
    # NaN lọt qua cổng. `not (x >= t)` bắt NaN đóng cổng đúng như champion 1-seed cần.
    if not (champion_agreement >= min_mean_label_agreement):
        reason = (
            f"Đồng thuận nhãn của champion (seed {best_seed}) là {champion_agreement:.4g}, "
            f"dưới ngưỡng min_mean_label_agreement={min_mean_label_agreement}. "
            f"Chỉ có {len(eligible)} seed hợp lệ để so sánh."
        )
        return SelectionOutcome(
            None, None, None, report, agreement, GATE_FAILED, [reason]
        )

    return SelectionOutcome(fit, label_map, profiles, report, agreement, GATE_OK, [])


def _agreement_matrix(eligible: Mapping, stability_mask: np.ndarray) -> pd.DataFrame:
    """Ma trận đồng thuận nhãn giữa các seed hợp lệ, đo trên train+validation."""
    seeds = sorted(eligible)
    matrix = pd.DataFrame(np.eye(len(seeds)), index=seeds, columns=seeds, dtype=float)
    for i, left in enumerate(seeds):
        for right in seeds[i + 1 :]:
            score = label_agreement(
                eligible[left][1][stability_mask], eligible[right][1][stability_mask]
            )
            matrix.loc[left, right] = score
            matrix.loc[right, left] = score
    return matrix


def _failure_reasons(
    report: pd.DataFrame,
    champion_states: int,
    champion_covariance: str,
    min_state_occupancy: float,
) -> list[str]:
    """Vì sao không fit nào đủ điều kiện — phải cụ thể, để `regime_summary.json` giải thích được."""
    family = report.loc[
        (report["n_states"] == champion_states)
        & (report["covariance_type"] == champion_covariance)
    ]
    if family.empty:
        return [
            (
                f"Họ champion ({champion_states} state/{champion_covariance}) không có trong "
                f"lưới candidates — không có fit nào để chấm."
            )
        ]
    reasons = [
        (
            f"Không fit nào trong họ champion ({champion_states} state/{champion_covariance}) "
            f"vượt qua cổng trên {len(family)} seed đã đăng ký."
        )
    ]
    ran = family.loc[~family["error"].astype(bool)]
    if not ran.empty and not ran["converged"].any():
        reasons.append("Không seed nào hội tụ.")
    failed = family.loc[family["error"].astype(bool), "error"]
    if not failed.empty:
        reasons.append(
            f"{len(failed)}/{len(family)} fit ném exception, đầu tiên: {failed.iloc[0]}"
        )
    if (family["min_state_occupancy"] < min_state_occupancy).any():
        reasons.append(
            f"Có seed vi phạm min_state_occupancy={min_state_occupancy}: "
            f"thấp nhất {family['min_state_occupancy'].min():.4g}."
        )
    inconsistent = family.loc[family["violations"].astype(bool), "violations"]
    if not inconsistent.empty:
        reasons.append(f"Vi phạm nghĩa kinh tế: {inconsistent.iloc[0]}")
    return reasons
