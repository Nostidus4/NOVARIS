# Nguyễn Anh Tú - lắp regime_daily (8 cột hợp đồng + cột chẩn đoán) và regime_summary; hàm thuần.
"""Lắp artifact chặng regime. Hàm THUẦN — trả dữ liệu, không mở file (CLAUDE.md quy tắc 13).

AD-06: `regime_daily.parquet` mang 8 cột hợp đồng của `RegimeDailySchema`, trong đó `state_id`,
`regime`, `prob_*` đều là giá trị FILTERED (nhân quả) — đúng thứ downstream được phép dùng — cộng
thêm cột chẩn đoán đặt tên riêng (`viterbi_*`, `prob_*_smoothed`). `DataFrameSchema` mặc định
`strict=False` nên cột thừa vẫn qua `validate_or_raise`; null thì KHÔNG, nên ngày warm-up bị loại
hẳn từ `build_feature_frame` chứ không ghi thành dòng null.

`prob_normal` lấy từ CỘT của state được gán nhãn "normal", không phải cột 0 — cột `state_id` chỉ để
trace (quy tắc 7).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd
from qshield_contracts.enums import RegimeName

from qshield_ai.regime.evaluate import (
    mean_durations,
    occupancy,
    stability_summary,
    transition_matrix,
)
from qshield_ai.regime.selection import SelectionOutcome

HMM_METHOD = "hmm"
STATUS_OK = "ok"
RUN_MODE_NON_BASELINE = "NON_BASELINE_RUN"

# Nguồn dữ liệu đầu vào của một run. `--mock` và run thật ghi vào CÙNG `artifacts/dev/`, nên nếu
# artifact không tự khai mình sinh từ fixture thì chặng sau đọc phải nhãn giả mà không có cách nào
# biết: đã xảy ra thật (chi tiết ở docs/perf/2026-08-04-pipeline-timing.md §7 — scenarios chạy
# thật đọc nhãn mock rồi báo gate PASS, không exception nào). `run_mode` KHÔNG thay được vai này:
# nó nói về trạng thái baseline/UAT, không nói về việc đầu vào là thật hay giả.
INPUT_SOURCE_MOCK = "mock"
INPUT_SOURCE_REAL = "real"

_LABEL_ORDER = (
    RegimeName.NORMAL.value,
    RegimeName.VOLATILE.value,
    RegimeName.STRESS.value,
)

UNRESOLVED_DECISIONS = (
    "IN-PO-01 (S=500 vs 2000/5000)",
    "IN-PO-02 (tư cách bằng chứng của fallback)",
    "IN-RISK-01 (đơn vị return của cube)",
    "IN-RISK-02 (ngày đánh giá t)",
    "IN-RISK-03 (ngưỡng Scenario Validation Gate)",
    "IN-CTR-01 (cột thừa trong regime_daily.parquet)",
    "IN-PO-04 (duyệt configs/regime.yaml + scenarios.yaml)",
)


def _state_for_label(label_map: Mapping[int, str]) -> dict[str, int]:
    inverted = {label: state_id for state_id, label in label_map.items()}
    missing = [label for label in _LABEL_ORDER if label not in inverted]
    if missing:
        raise ValueError(
            f"label_map thiếu nhãn {missing} — mỗi nhãn phải ứng với đúng một state."
        )
    return inverted


def build_regime_daily(
    frame: pd.DataFrame,
    *,
    filtered: np.ndarray,
    smoothed: np.ndarray,
    viterbi: np.ndarray,
    label_map: Mapping[int, str],
    model_version: str,
    seed: int,
    feature_version: str,
    run_mode: str,
) -> pd.DataFrame:
    """Một dòng/ngày: 8 cột hợp đồng (giá trị filtered) + cột chẩn đoán."""
    lengths = {len(frame), len(filtered), len(smoothed), len(viterbi)}
    if len(lengths) != 1:
        raise ValueError(f"Các đầu vào lệch độ dài: {sorted(lengths)}.")
    state_for_label = _state_for_label(label_map)

    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(frame["date"].to_numpy()),
            "state_id": filtered.argmax(axis=1).astype(int),
        }
    )
    daily["regime"] = [label_map[int(state)] for state in daily["state_id"]]
    for label in _LABEL_ORDER:
        column = state_for_label[label]
        daily[f"prob_{label}"] = filtered[:, column]
        daily[f"prob_{label}_smoothed"] = smoothed[:, column]

    daily["model_version"] = model_version
    daily["seed"] = int(seed)
    daily["method"] = HMM_METHOD
    daily["inference_status"] = STATUS_OK
    daily["split"] = frame["split"].to_numpy()
    daily["feature_version"] = feature_version
    daily["run_mode"] = run_mode
    daily["viterbi_state_id"] = np.asarray(viterbi, dtype=int)
    daily["viterbi_label"] = [label_map[int(state)] for state in viterbi]
    return daily


def build_regime_summary(
    *,
    outcome: SelectionOutcome,
    daily: pd.DataFrame | None,
    feature_names: Sequence[str],
    feature_version: str,
    run_mode: str,
    data_version: str,
    input_source: str,
    unresolved_decisions: Sequence[str] = UNRESOLVED_DECISIONS,
) -> dict[str, Any]:
    """Provenance của chặng regime. `RunContext`/CLI ghi ra đĩa; module này chỉ TRẢ VỀ dict.

    `input_source` bắt buộc (keyword, không có mặc định): một mặc định "real" sẽ khiến đúng cái
    lỗi cần chặn — artifact sinh từ fixture tự khai là thật — quay lại ngay khi ai đó quên truyền.
    """
    if input_source not in (INPUT_SOURCE_MOCK, INPUT_SOURCE_REAL):
        raise ValueError(
            f"input_source phải là {INPUT_SOURCE_MOCK!r} hoặc {INPUT_SOURCE_REAL!r}, "
            f"nhận {input_source!r}."
        )
    summary: dict[str, Any] = {
        "run_mode": run_mode,
        "input_source": input_source,
        "gate_status": outcome.gate_status,
        "gate_reasons": list(outcome.gate_reasons),
        "feature_version": feature_version,
        "feature_names": list(feature_names),
        "data_version": data_version,
        "unresolved_decisions": list(unresolved_decisions),
        "seeds_reported": sorted(int(seed) for seed in outcome.report["seed"].unique()),
        "stability": stability_summary(outcome.agreement),
    }

    if outcome.champion is not None:
        summary["champion"] = {
            "seed": outcome.champion.seed,
            "n_states": outcome.champion.n_states,
            "covariance_type": outcome.champion.covariance_type,
            "converged": outcome.champion.converged,
            "log_likelihood_train": outcome.champion.log_likelihood_train,
            "log_likelihood_validation": outcome.champion.log_likelihood_validation,
            "n_parameters": outcome.champion.n_parameters,
            "aic": outcome.champion.aic,
            "bic": outcome.champion.bic,
        }
    if outcome.label_map is not None:
        summary["label_map"] = {str(k): v for k, v in outcome.label_map.items()}
    if outcome.profiles is not None:
        summary["state_profiles"] = [
            {
                "state_id": profile.state_id,
                "label": (outcome.label_map or {}).get(profile.state_id),
                "occupancy": profile.occupancy,
                "mean_return": profile.mean_return,
                "mean_volatility": profile.mean_volatility,
                "mean_drawdown": profile.mean_drawdown,
                "mean_correlation": profile.mean_correlation,
                "stress_score": profile.stress_score,
            }
            for profile in outcome.profiles
        ]

    if daily is not None and not daily.empty:
        labels = daily["regime"].tolist()
        summary["coverage"] = {
            "n_rows": len(daily),
            "start": str(daily["date"].min().date()),
            "end": str(daily["date"].max().date()),
            "by_split": daily.groupby("split").size().to_dict(),
        }
        summary["occupancy"] = occupancy(labels, order=_LABEL_ORDER)
        summary["mean_durations"] = mean_durations(labels, order=_LABEL_ORDER)
        summary["transition_matrix"] = transition_matrix(
            labels, order=_LABEL_ORDER
        ).to_dict()
    return summary
