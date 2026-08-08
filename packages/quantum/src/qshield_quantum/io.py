# Đỗ Ngọc Tân - chuyển đổi DataFrame (đúng schemas/risk.py) <-> mảng NumPy dùng cho formulation/.
"""Cầu nối giữa artifact dạng bảng (`ActionEffectsSchema`, `PairwiseEffectsSchema`) và mảng NumPy
mà `formulation/` cần. Dùng CHUNG cho cả `--mock` (từ `fixtures.py`) lẫn dữ liệu thật sau này (từ
`packages/risk`) — cli.py không cần rẽ nhánh logic theo nguồn dữ liệu, chỉ khác ở nơi DataFrame đến
từ đâu.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def action_effects_to_arrays(
    df: pd.DataFrame, tickers: list[str]
) -> tuple[np.ndarray, np.ndarray]:
    """Trả `(g, c)` theo ĐÚNG thứ tự `tickers` — `action_id` phải khớp `range(len(tickers))` và
    `ticker` tại `action_id=i` phải là `tickers[i]` (bitstring index `i` ↔ `tickers[i]`, xem
    `decode.py`). Lệch thứ tự ở đây là lỗi âm thầm nguy hiểm nhất trong toàn bộ package — fail
    fast thay vì đoán.
    """
    ordered = df.sort_values("action_id").reset_index(drop=True)
    expected_ids = list(range(len(tickers)))
    if list(ordered["action_id"]) != expected_ids:
        raise ValueError(
            f"action_effects thiếu/thừa action_id — kỳ vọng {expected_ids}, "
            f"nhận {list(ordered['action_id'])}."
        )
    if list(ordered["ticker"]) != tickers:
        raise ValueError(
            f"Thứ tự ticker trong action_effects ({list(ordered['ticker'])}) không khớp "
            f"configs/base.yaml ({tickers}) — bitstring sẽ decode sai mã."
        )
    return ordered["g"].to_numpy(dtype=float), ordered["c"].to_numpy(dtype=float)


def pairwise_to_matrix(df: pd.DataFrame, tickers: list[str]) -> np.ndarray:
    """Dựng ma trận `C` (n,n) ĐỐI XỨNG đầy đủ từ dạng dài chỉ lưu `i<j`
    (`PairwiseEffectsSchema`) — đường chéo = 0 (không có "tự tương tác")."""
    n = len(tickers)
    C = np.zeros((n, n))
    for row in df.itertuples(index=False):
        i, j, value = int(row.action_i), int(row.action_j), float(row.C_ij)
        if not (0 <= i < n and 0 <= j < n):
            raise ValueError(
                f"pairwise_effects có action_id {i} hoặc {j} ngoài phạm vi [0,{n})."
            )
        C[i, j] = value
        C[j, i] = value
    return C
