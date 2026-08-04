# Nguyễn Anh Tú - gán state 0/1/2 → Normal/Volatile/Stress THEO THỐNG KÊ, không theo state id (quy tắc 7, CLAUDE.md).
"""Gán nhãn trạng thái theo hồ sơ thống kê, KHÔNG theo state id.

HMM trả state 0/1/2 theo thứ tự ngẫu nhiên tùy seed. Giả định "state 0 = Normal" là bug im lặng:
nó không báo lỗi, chỉ làm nhãn đảo giữa các lần chạy (`docs/runbook/troubleshooting.md` §4).

AD-05: xếp hạng bằng điểm tổng hợp trên hồ sơ CHƯA transform, CHƯA scale —

    stress_score = z(volatility) − z(return) + z(|drawdown|)

dùng cả ba tín hiệu mà CLAUDE.md quy tắc 7 nêu tên. `z` tính trên K state (không phải theo thời
gian), độ lệch chuẩn tổng thể; K state giống hệt nhau ⇒ mọi z bằng 0 và tie-break rơi về state id.

Xếp hạng xong CHƯA đủ: `economic_consistency_violations` kiểm tra thứ hạng có nghĩa kinh tế thật
không. State "stress" mà volatility thấp hơn "normal" là state vô nghĩa — cổng này biến quy tắc 7
thành thứ kiểm được, thay vì một quy ước đặt tên.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from qshield_contracts.enums import RegimeName

_RANKED_LABELS = (RegimeName.STRESS, RegimeName.VOLATILE, RegimeName.NORMAL)


@dataclass(frozen=True)
class StateProfile:
    """Hồ sơ thống kê của một state — cơ sở DUY NHẤT để gán nhãn."""

    state_id: int
    occupancy: float
    mean_return: float
    mean_volatility: float
    mean_drawdown: float
    mean_correlation: float
    stress_score: float


def _zscore(values: np.ndarray) -> np.ndarray:
    """z trên K state. Mọi state bằng nhau ⇒ std = 0 ⇒ trả 0 thay vì chia cho 0."""
    deviation = float(values.std())
    if deviation == 0.0:
        return np.zeros_like(values)
    return (values - values.mean()) / deviation


def state_profiles(
    raw_frame: pd.DataFrame,
    states: np.ndarray,
    *,
    return_column: str,
    volatility_column: str,
    drawdown_column: str,
    correlation_column: str,
) -> tuple[StateProfile, ...]:
    """Hồ sơ từng state trên `raw_frame` — frame CHƯA transform, CHƯA scale, để số đọc được."""
    if len(raw_frame) != len(states):
        raise ValueError(
            f"raw_frame và states lệch độ dài: {len(raw_frame)} vs {len(states)}."
        )
    state_ids = np.unique(states)
    grouped = {
        int(state_id): raw_frame.loc[states == state_id] for state_id in state_ids
    }

    volatility = np.array([grouped[k][volatility_column].mean() for k in grouped])
    returns = np.array([grouped[k][return_column].mean() for k in grouped])
    drawdown = np.array([grouped[k][drawdown_column].mean() for k in grouped])
    correlation = np.array([grouped[k][correlation_column].mean() for k in grouped])

    scores = _zscore(volatility) - _zscore(returns) + _zscore(np.abs(drawdown))

    return tuple(
        StateProfile(
            state_id=state_id,
            occupancy=float(len(grouped[state_id]) / len(raw_frame)),
            mean_return=float(returns[position]),
            mean_volatility=float(volatility[position]),
            mean_drawdown=float(drawdown[position]),
            mean_correlation=float(correlation[position]),
            stress_score=float(scores[position]),
        )
        for position, state_id in enumerate(grouped)
    )


def label_states(profiles: Sequence[StateProfile]) -> dict[int, str]:
    """`state_id -> nhãn`. Xếp `stress_score` giảm dần; hòa điểm thì state id nhỏ đứng trước."""
    if len(profiles) != len(_RANKED_LABELS):
        raise ValueError(
            f"Chỉ gán nhãn cho đúng 3 trạng thái (RegimeDailySchema chặn state_id ở "
            f"{{0,1,2}}), nhận {len(profiles)}."
        )
    ranked = sorted(profiles, key=lambda p: (-p.stress_score, p.state_id))
    return {
        profile.state_id: label.value
        for profile, label in zip(ranked, _RANKED_LABELS, strict=True)
    }


def economic_consistency_violations(
    profiles: Sequence[StateProfile], label_map: Mapping[int, str]
) -> list[str]:
    """Danh sách vi phạm nghĩa kinh tế. Rỗng = thứ hạng dùng được; khác rỗng = cổng HMM fail."""
    by_label = {label_map[profile.state_id]: profile for profile in profiles}
    stress = by_label[RegimeName.STRESS.value]
    normal = by_label[RegimeName.NORMAL.value]

    violations: list[str] = []
    if stress.mean_volatility <= normal.mean_volatility:
        violations.append(
            f"stress volatility ({stress.mean_volatility:.6g}) không cao hơn normal "
            f"({normal.mean_volatility:.6g})"
        )
    if stress.mean_return >= normal.mean_return:
        violations.append(
            f"stress return ({stress.mean_return:.6g}) không thấp hơn normal "
            f"({normal.mean_return:.6g})"
        )
    return violations
