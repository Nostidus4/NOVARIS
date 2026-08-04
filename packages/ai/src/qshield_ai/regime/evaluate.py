# Nguyễn Anh Tú - duration, transition matrix, ổn định qua seed.
"""Chẩn đoán regime để đưa vào `regime_summary.json` và dashboard.

Toàn bộ hàm ở đây nhận CHUỖI NHÃN (đã gán theo thống kê), không nhận state id — nhãn mới là thứ so
sánh được giữa các seed và đọc được trên slide.

Quy ước: một nhãn không xuất hiện có `duration = 0` và hàng chuyển toàn 0 (không phải NaN) để
`metrics.json` luôn tuần tự hóa được. `mean_durations` không kiểm duyệt (censor) run ở hai đầu
chuỗi — xem docstring của hàm đó.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise

import numpy as np
import pandas as pd


def _as_array(labels: Sequence[str]) -> np.ndarray:
    array = np.asarray(labels, dtype=object)
    if array.size == 0:
        raise ValueError("Chuỗi nhãn rỗng — không tính được chẩn đoán regime.")
    return array


def _validate_labels_within_order(
    labels: np.ndarray, order: Sequence[str], caller: str
) -> None:
    """Nhãn lạ phải nổ ngay tại biên, không được im lặng biến mất khỏi occupancy."""
    unknown = sorted(set(map(str, labels)) - {str(name) for name in order})
    if unknown:
        raise ValueError(
            f"{caller}: nhãn {unknown} không có trong order={list(order)} — "
            f"kiểm tra label_map ở regime/labeling.py."
        )


def occupancy(labels: Sequence[str], *, order: Sequence[str]) -> dict[str, float]:
    """Tỷ lệ ngày ở mỗi trạng thái."""
    array = _as_array(labels)
    _validate_labels_within_order(array, order, "occupancy")
    return {label: float(np.mean(array == label)) for label in order}


def mean_durations(labels: Sequence[str], *, order: Sequence[str]) -> dict[str, float]:
    """Độ dài trung bình một lượt ở mỗi trạng thái (số phiên liên tiếp trước khi đổi).

    Quy ước biên: một run đang MỞ ở cuối chuỗi, và một run BẮT ĐẦU ngay tại index 0, đều được
    tính là run hoàn chỉnh. Không kiểm duyệt (censor) hai đầu. Với chuỗi ngắn, quy ước này kéo
    trung bình xuống so với cách kiểm duyệt, vì run cụt vẫn được đếm đủ.
    """
    array = _as_array(labels)
    _validate_labels_within_order(array, order, "mean_durations")
    runs: dict[str, list[int]] = {label: [] for label in order}
    current, length = array[0], 1
    for value in array[1:]:
        if value == current:
            length += 1
        else:
            runs.setdefault(str(current), []).append(length)
            current, length = value, 1
    runs.setdefault(str(current), []).append(length)
    return {
        label: float(np.mean(runs[label])) if runs.get(label) else 0.0
        for label in order
    }


def transition_matrix(labels: Sequence[str], *, order: Sequence[str]) -> pd.DataFrame:
    """Ma trận chuyển thực nghiệm, chuẩn hóa theo hàng. Trạng thái không xuất hiện ⇒ hàng 0."""
    array = _as_array(labels)
    _validate_labels_within_order(array, order, "transition_matrix")
    index = {label: position for position, label in enumerate(order)}
    counts = np.zeros((len(order), len(order)), dtype=float)
    for source, target in pairwise(array):
        counts[index[str(source)], index[str(target)]] += 1.0

    totals = counts.sum(axis=1, keepdims=True)
    normalized = np.divide(counts, totals, out=np.zeros_like(counts), where=totals > 0)
    return pd.DataFrame(normalized, index=list(order), columns=list(order))


def stability_summary(agreement: pd.DataFrame) -> dict[str, float]:
    """Tóm tắt ma trận đồng thuận giữa các seed — chỉ nhìn phần ngoài đường chéo."""
    matrix = agreement.to_numpy(dtype=float)
    n_seeds = len(matrix)
    if n_seeds < 2:
        return {
            "n_seeds": float(n_seeds),
            "mean_agreement": float("nan"),
            "min_agreement": float("nan"),
            "max_agreement": float("nan"),
        }
    off_diagonal = matrix[~np.eye(n_seeds, dtype=bool)]
    return {
        "n_seeds": float(n_seeds),
        "mean_agreement": float(off_diagonal.mean()),
        "min_agreement": float(off_diagonal.min()),
        "max_agreement": float(off_diagonal.max()),
    }
