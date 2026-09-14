# Đỗ Ngọc Tân - hash ổn định cho provenance của track thí nghiệm hybrid (QAOA-assisted).
"""Một chỗ DUY NHẤT sinh hash provenance cho thí nghiệm hybrid.

Mọi artifact hybrid phải mang `portfolio_hash`, `scenario_hash`, `candidate_order_hash`,
`qubo_hash` và `manifest_hash`. Nếu mỗi module tự băm theo cách riêng, hai hash "cùng tên" có thể
khác nhau cho cùng một đối tượng và kiểm tra khớp hash mất ý nghĩa.

`effective_action_hash` băm HÀNH ĐỘNG THỰC SAU DECODE (phần trăm nguyên trên mỗi mã), không băm
bitstring thô: hai bitstring cho cùng lệnh thực thi không phải hai ý tưởng đầu tư khác nhau.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import numpy as np


def stable_hash(payload: Any) -> str:
    """SHA-256 của JSON chuẩn hóa (sort_keys, không khoảng trắng)."""
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def array_hash(array: np.ndarray) -> str:
    """SHA-256 của shape + dtype + bytes (C-contiguous) — dùng cho scenario cube."""
    values = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(values.shape).encode("utf-8"))
    digest.update(str(values.dtype).encode("utf-8"))
    digest.update(values.tobytes())
    return digest.hexdigest()


def effective_action_hash(levels_pct: Sequence[int | float] | np.ndarray) -> str:
    """Hash hành động thực: làm tròn về phần trăm nguyên rồi băm theo thứ tự candidate."""
    values = np.asarray(levels_pct, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError(
            f"[contracts.hashing] levels_pct must be a finite 1-D vector, got {values.shape}."
        )
    rounded = np.rint(values).astype(int)
    return hashlib.sha256(",".join(str(v) for v in rounded).encode("utf-8")).hexdigest()
