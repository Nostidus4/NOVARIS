# Đỗ Ngọc Tân - StatevectorSampler — môi trường thực thi chính cho 8 qubit.
"""`StatevectorSampler` — với 8 qubit (2⁸=256 biên độ), mô phỏng statevector đủ nhanh, không cần
Aer transpile pipeline. `backends/hardware.py` để trống có chủ đích (CLAUDE.md: ngoài phạm vi).
"""

from __future__ import annotations

from qiskit.primitives import StatevectorSampler


def make_sampler(*, shots: int, seed: int) -> StatevectorSampler:
    return StatevectorSampler(default_shots=shots, seed=seed)
