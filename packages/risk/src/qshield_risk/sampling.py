"""Structured true-objective samples for the two-bit four-level QUBO surrogate."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd  # type: ignore[import-untyped]

from qshield_risk.objective import financial_objective
from qshield_risk.portfolio import validate_ticker_order


def decode_four_level_bits(bits: npt.ArrayLike, *, candidate_count: int) -> np.ndarray:
    """Decode consecutive bit pairs with mapping 00→0, 10→10, 01→20, 11→30 percent."""
    values = np.asarray(bits)
    expected = 2 * candidate_count
    if values.shape != (expected,) or not np.all(np.isin(values, (0, 1))):
        raise ValueError(
            f"[risk.sampling] bits must be a binary vector with shape ({expected},)."
        )
    pairs = values.astype(float).reshape(candidate_count, 2)
    return 0.10 * pairs[:, 0] + 0.20 * pairs[:, 1]


def structured_bit_vectors(candidate_count: int) -> tuple[np.ndarray, tuple[str, ...]]:
    """Return intercept, all ``d`` main effects and all ``d(d-1)/2`` interactions."""
    if candidate_count <= 0:
        raise ValueError("[risk.sampling] candidate_count must be positive.")
    dimension = 2 * candidate_count
    vectors = [np.zeros(dimension, dtype=np.int8)]
    kinds = ["intercept"]
    for bit in range(dimension):
        vector = np.zeros(dimension, dtype=np.int8)
        vector[bit] = 1
        vectors.append(vector)
        kinds.append("main")
    for left, right in combinations(range(dimension), 2):
        vector = np.zeros(dimension, dtype=np.int8)
        vector[[left, right]] = 1
        vectors.append(vector)
        kinds.append("pairwise")
    return np.stack(vectors), tuple(kinds)


def sample_objective(
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    candidates: Sequence[str],
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Evaluate the canonical objective on the complete structured quadratic design."""
    tickers = validate_ticker_order(ticker_order)
    candidate_order = tuple(str(ticker) for ticker in candidates)
    if not candidate_order or len(set(candidate_order)) != len(candidate_order):
        raise ValueError("[risk.sampling] candidates must be unique and non-empty.")
    missing = sorted(set(candidate_order) - set(tickers))
    if missing:
        raise ValueError(
            f"[risk.sampling] candidates absent from ticker_order: {missing}."
        )
    indices = [tickers.index(ticker) for ticker in candidate_order]
    vectors, kinds = structured_bit_vectors(len(candidate_order))
    rows: list[dict[str, object]] = []
    for sample_id, (bits, kind) in enumerate(zip(vectors, kinds, strict=True)):
        candidate_reductions = decode_four_level_bits(
            bits, candidate_count=len(candidate_order)
        )
        reductions = np.zeros(len(tickers), dtype=float)
        reductions[indices] = candidate_reductions
        result = financial_objective(
            reductions, scenarios, tickers, weights, cash_weight, config
        )
        row: dict[str, object] = {
            "sample_id": sample_id,
            "sample_type": kind,
            "bitstring": "".join(str(int(bit)) for bit in bits),
            "decoded_actions": {
                ticker: float(value)
                for ticker, value in zip(
                    candidate_order, candidate_reductions, strict=True
                )
            },
            "objective": result.value,
            "constraint_violations": result.constraint_violations,
        }
        for name, component in result.components.items():
            row[f"{name}_raw"] = component.raw
            row[f"{name}_scaled"] = component.scaled
            row[f"{name}_weight"] = component.weight
            row[f"{name}_contribution"] = component.contribution
        rows.append(row)
    return pd.DataFrame(rows)
