"""Fit and evaluate a generic quadratic binary surrogate from risk samples.

For ``d`` bits the design is ``[1, z_i, z_i*z_j for i<j]`` and therefore has
``1 + d + d(d-1)/2`` coefficients (211 at d=20).  Structured handoff samples
must identify bits either with a ``bitstring`` column, ``bit_0..bit_{d-1}``,
or per-candidate action columns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from qshield_quantum.formulation.four_level import encode_action_levels

_TARGET_COLUMNS = ("objective", "energy", "target", "qubo_objective", "true_objective")


@dataclass(frozen=True)
class QuadraticSurrogate:
    """Binary quadratic model in ``z'Qz + linear'z + constant`` convention."""

    Q: np.ndarray
    linear: np.ndarray
    constant: float
    residual_sum_squares: float
    rank: int
    sample_count: int

    @property
    def dimension(self) -> int:
        return int(self.linear.shape[0])

    def evaluate(self, bits: np.ndarray) -> float:
        z = np.asarray(bits, dtype=float)
        if z.shape != (self.dimension,):
            raise ValueError(f"Expected bits shape {(self.dimension,)}, got {z.shape}.")
        return float(z @ self.Q @ z + self.linear @ z + self.constant)

    def evaluate_batch(self, bit_matrix: np.ndarray) -> np.ndarray:
        Z = np.asarray(bit_matrix, dtype=float)
        if Z.ndim != 2 or Z.shape[1] != self.dimension:
            raise ValueError(
                f"Expected bit matrix with {self.dimension} columns, got {Z.shape}."
            )
        return np.einsum("bi,ij,bj->b", Z, self.Q, Z) + Z @ self.linear + self.constant

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "constant": self.constant,
            "linear": self.linear.tolist(),
            "quadratic_matrix": self.Q.tolist(),
            "sample_count": self.sample_count,
            "fit_rank": self.rank,
            "residual_sum_squares": self.residual_sum_squares,
        }


def quadratic_feature_count(dimension: int) -> int:
    if dimension < 1:
        raise ValueError(f"dimension must be positive, got {dimension}.")
    return 1 + dimension + dimension * (dimension - 1) // 2


def quadratic_design_matrix(bit_matrix: np.ndarray) -> np.ndarray:
    Z = np.asarray(bit_matrix, dtype=float)
    if Z.ndim != 2 or not np.isin(Z, (0, 1)).all():
        raise ValueError("bit_matrix must be a two-dimensional binary array.")
    rows, dimension = Z.shape
    design = np.empty((rows, quadratic_feature_count(dimension)), dtype=float)
    design[:, 0] = 1.0
    design[:, 1 : dimension + 1] = Z
    cursor = dimension + 1
    for i in range(dimension):
        width = dimension - i - 1
        if width:
            design[:, cursor : cursor + width] = Z[:, [i]] * Z[:, i + 1 :]
            cursor += width
    return design


def structured_samples_to_arrays(
    samples: pd.DataFrame,
    candidate_order: list[str],
    *,
    target_column: str | None = None,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Normalize supported risk handoff layouts into ``(Z, y, target_name)``."""
    dimension = 2 * len(candidate_order)
    target = target_column or next(
        (name for name in _TARGET_COLUMNS if name in samples.columns), None
    )
    if target is None:
        raise ValueError(
            f"Objective samples need one target column from {_TARGET_COLUMNS}."
        )

    bit_columns = [f"bit_{i}" for i in range(dimension)]
    if "bitstring" in samples.columns:
        strings = samples["bitstring"].astype(str).str.zfill(dimension)
        invalid = strings.map(
            lambda value: len(value) != dimension or bool(set(value) - {"0", "1"})
        )
        if invalid.any():
            raise ValueError(
                f"Invalid bitstring rows: {samples.index[invalid].tolist()[:5]}."
            )
        Z = np.array([[int(bit) for bit in value] for value in strings], dtype=np.int8)
    elif all(column in samples.columns for column in bit_columns):
        Z = samples[bit_columns].to_numpy()
    else:
        action_columns = _find_action_columns(samples, candidate_order)
        if action_columns is None:
            raise ValueError(
                "Objective samples need bitstring, bit_0..bit_{d-1}, or one action "
                "percentage column per candidate."
            )
        Z = np.vstack(
            [
                encode_action_levels(row)
                for row in samples[action_columns].to_numpy(dtype=float)
            ]
        )

    Z_float = np.asarray(Z, dtype=float)
    if Z_float.shape != (len(samples), dimension) or not np.isin(Z_float, (0, 1)).all():
        raise ValueError(
            f"Decoded sample bits must have shape {(len(samples), dimension)} and contain 0/1."
        )
    y = samples[target].to_numpy(dtype=float)
    if not np.isfinite(Z_float).all() or not np.isfinite(y).all():
        raise ValueError("Objective samples contain non-finite bits or target values.")
    return Z_float, y, target


def _find_action_columns(
    samples: pd.DataFrame, candidate_order: list[str]
) -> list[str] | None:
    layouts = (
        [f"{ticker}_action_pct" for ticker in candidate_order],
        [f"action_{i}" for i in range(len(candidate_order))],
        candidate_order,
    )
    return next(
        (columns for columns in layouts if all(c in samples.columns for c in columns)),
        None,
    )


def fit_quadratic_surrogate(
    bit_matrix: np.ndarray,
    targets: np.ndarray,
    *,
    rank_tolerance: float | None = None,
) -> QuadraticSurrogate:
    """Least-squares fit, failing fast if samples do not identify every coefficient."""
    Z = np.asarray(bit_matrix, dtype=float)
    y = np.asarray(targets, dtype=float)
    design = quadratic_design_matrix(Z)
    if y.shape != (len(Z),):
        raise ValueError(f"targets must have shape {(len(Z),)}, got {y.shape}.")
    required = design.shape[1]
    if len(Z) < required:
        raise ValueError(
            f"Need at least {required} structured samples for d={Z.shape[1]}, got {len(Z)}."
        )
    coefficients, residuals, rank, _ = np.linalg.lstsq(design, y, rcond=rank_tolerance)
    if rank < required:
        raise ValueError(
            f"Quadratic sample design is rank deficient: rank={rank}, required={required}."
        )

    dimension = Z.shape[1]
    linear = coefficients[1 : dimension + 1].copy()
    Q = np.zeros((dimension, dimension), dtype=float)
    cursor = dimension + 1
    for i in range(dimension):
        for j in range(i + 1, dimension):
            # Symmetric matrix form counts each off-diagonal term twice.
            Q[i, j] = Q[j, i] = coefficients[cursor] / 2.0
            cursor += 1
    fitted = design @ coefficients
    rss = float(residuals[0]) if len(residuals) else float(np.sum((fitted - y) ** 2))
    return QuadraticSurrogate(
        Q=Q,
        linear=linear,
        constant=float(coefficients[0]),
        residual_sum_squares=rss,
        rank=int(rank),
        sample_count=len(Z),
    )
