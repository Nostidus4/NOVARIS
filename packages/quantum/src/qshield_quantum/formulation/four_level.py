"""Codec for the workflow four-level action representation.

Each candidate owns two consecutive bits.  The bit order is deliberately the
one fixed by the workflow profile: ``00/10/01/11 -> 0/10/20/30`` percent.
This is equivalent to ``10 * first_bit + 20 * second_bit``; it is not the
usual little-endian interpretation of a two-bit integer.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

ACTION_LEVELS_PCT = (0, 10, 20, 30)
BITS_PER_CANDIDATE = 2


def encode_action_levels(action_levels_pct: Sequence[int | float]) -> np.ndarray:
    """Encode action percentages as a flat ``2 * M`` binary vector."""
    levels = np.asarray(action_levels_pct, dtype=float)
    if levels.ndim != 1:
        raise ValueError(
            f"action_levels_pct must be one-dimensional, got shape={levels.shape}."
        )
    rounded = np.rint(levels).astype(int)
    if (
        not np.allclose(levels, rounded)
        or not np.isin(rounded, ACTION_LEVELS_PCT).all()
    ):
        raise ValueError(
            f"Action levels must be in {ACTION_LEVELS_PCT}; got {levels.tolist()}."
        )
    bits = np.empty((len(rounded), BITS_PER_CANDIDATE), dtype=np.int8)
    bits[:, 0] = (rounded % 20 == 10).astype(np.int8)
    bits[:, 1] = (rounded >= 20).astype(np.int8)
    return bits.reshape(-1)


def decode_action_levels(
    bits: Sequence[int | float] | np.ndarray | str,
) -> np.ndarray:
    """Decode a flat bit vector/bitstring into one percentage per candidate."""
    if isinstance(bits, str):
        if set(bits) - {"0", "1"}:
            raise ValueError(f"bitstring contains non-binary characters: {bits!r}.")
        values = np.fromiter((int(bit) for bit in bits), dtype=np.int8)
    else:
        raw = np.asarray(bits)
        if raw.ndim != 1:
            raise ValueError(f"bits must be one-dimensional, got shape={raw.shape}.")
        values = np.rint(raw).astype(np.int8)
        if not np.allclose(raw, values) or not np.isin(values, (0, 1)).all():
            raise ValueError(f"bits must contain only 0/1 values; got {raw.tolist()}.")
    if len(values) % BITS_PER_CANDIDATE:
        raise ValueError(
            f"Four-level encoding needs an even bit count; got {len(values)}."
        )
    pairs = values.reshape(-1, BITS_PER_CANDIDATE)
    return 10 * pairs[:, 0] + 20 * pairs[:, 1]


def four_level_bitstring(action_levels_pct: Sequence[int | float]) -> str:
    """Encode levels directly to their stable artifact bitstring."""
    return "".join(str(int(bit)) for bit in encode_action_levels(action_levels_pct))


def four_level_variable_names(candidate_order: Sequence[str]) -> list[str]:
    """Return unique Qiskit variable names in codec order."""
    if len(set(candidate_order)) != len(candidate_order):
        raise ValueError("candidate_order contains duplicate tickers.")
    return [
        f"{ticker}__b{bit}"
        for ticker in candidate_order
        for bit in range(BITS_PER_CANDIDATE)
    ]
