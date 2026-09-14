# Đỗ Ngọc Tân - chuẩn hóa thang energy QUBO trước QAOA (không đổi argmin).
"""Energy normalization cho QAOA.

Đo thật 2026-09-13 (hybrid exploratory): surrogate workflow có |linear| ~ 0,04, |Q| ~ 2e-5, dải
energy ~0,46. Với thang đó, pha ``exp(-iγH)`` gần như không tách trạng thái trong miền γ mà COBYLA
khám phá ⇒ phân phối QAOA p=1 gần uniform (top-10 mass 0,3%, không đo ra optimum). Nhân hằng
dương ``k`` và bỏ hằng số không đổi argmin/thứ tự trạng thái nhưng đưa Hamiltonian về thang mà
QAOA tối ưu được (cùng probe: xác suất đo ra optimum 0% → 13,8%).

Quy tắc (không cần enumerate, dùng được ở 20-bit):
``span = Σ|l_i| + Σ_{i≠j}|Q_ij| + Σ|Q_ii|`` là cận trên của ``max E − min E``;
``k = target_range / span``; ``E_scaled = k (E − constant)``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qshield_quantum.formulation.surrogate import QuadraticSurrogate


@dataclass(frozen=True)
class EnergyNormalization:
    method: str
    target_range: float
    coefficient_span: float
    scale: float
    offset: float

    def to_scaled(self, energy: float | np.ndarray) -> float | np.ndarray:
        return self.scale * (energy - self.offset)


def normalize_for_qaoa(
    model: QuadraticSurrogate, target_range: float
) -> tuple[QuadraticSurrogate, EnergyNormalization]:
    if not np.isfinite(target_range) or target_range <= 0.0:
        raise ValueError(f"target_range must be positive, got {target_range}.")
    span = float(np.abs(model.linear).sum() + np.abs(model.Q).sum())
    if not np.isfinite(span) or span <= 0.0:
        raise ValueError(f"QUBO coefficient span must be positive, got {span}.")
    scale = target_range / span
    scaled = QuadraticSurrogate(
        Q=model.Q * scale,
        linear=model.linear * scale,
        constant=0.0,
        residual_sum_squares=model.residual_sum_squares,
        rank=model.rank,
        sample_count=model.sample_count,
    )
    return scaled, EnergyNormalization(
        "coefficient_l1", float(target_range), span, scale, float(model.constant)
    )
