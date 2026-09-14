# Đỗ Ngọc Tân - QUBO con cho Phương án B: cố định biến ngoài neighborhood, giải 8–16 bit bên trong.
"""Condition một QUBO surrogate lên các biến cố định.

Với ``z = (f, x)`` (f tự do, x cố định) và ``E(z) = z'Qz + l'z + c``::

    E = f'Q_ff f + 2 f'Q_fx x + x'Q_xx x + l_f'f + l_x'x + c
      = f'Q' f + l'' f + c''
    Q'  = Q_ff
    l'' = l_f + 2 Q_fx x
    c'' = c + x'Q_xx x + l_x'x

Đây là đại số chính xác — không fit lại surrogate — nên energy con + hằng số khớp energy đầy đủ
trên mọi trạng thái của neighborhood (có test enumerate).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from qshield_quantum.formulation.surrogate import QuadraticSurrogate


def candidate_bit_indices(candidate_indices: Sequence[int]) -> list[int]:
    """Mã thứ i sở hữu hai bit ``2i, 2i+1`` (four-level codec)."""
    return [
        bit
        for index in sorted(int(i) for i in candidate_indices)
        for bit in (2 * index, 2 * index + 1)
    ]


def condition_qubo(
    model: QuadraticSurrogate,
    base_bits: Sequence[int] | np.ndarray,
    free_bits: Sequence[int],
) -> QuadraticSurrogate:
    base = np.asarray(base_bits, dtype=float)
    if base.shape != (model.dimension,) or not np.isin(base, (0, 1)).all():
        raise ValueError(f"base_bits must be binary with shape ({model.dimension},).")
    free = sorted(int(bit) for bit in free_bits)
    if (
        len(set(free)) != len(free)
        or not free
        or free[-1] >= model.dimension
        or free[0] < 0
    ):
        raise ValueError(f"free_bits must be unique indices in [0, {model.dimension}).")
    fixed = [bit for bit in range(model.dimension) if bit not in set(free)]
    x = base[fixed]
    Q_ff = model.Q[np.ix_(free, free)]
    Q_fx = model.Q[np.ix_(free, fixed)]
    Q_xx = model.Q[np.ix_(fixed, fixed)]
    linear = model.linear[free] + 2.0 * Q_fx @ x
    constant = float(model.constant + x @ Q_xx @ x + model.linear[fixed] @ x)
    return QuadraticSurrogate(
        Q=Q_ff.copy(),
        linear=linear,
        constant=constant,
        residual_sum_squares=model.residual_sum_squares,
        rank=model.rank,
        sample_count=model.sample_count,
    )


def embed_bits(
    base_bits: Sequence[int] | np.ndarray,
    free_bits: Sequence[int],
    sub_bits: Sequence[int],
) -> np.ndarray:
    full = np.asarray(base_bits, dtype=np.int8).copy()
    free = sorted(int(bit) for bit in free_bits)
    values = np.asarray(sub_bits, dtype=np.int8)
    if values.shape != (len(free),):
        raise ValueError(
            f"sub_bits must have shape ({len(free)},), got {values.shape}."
        )
    full[free] = values
    return full
