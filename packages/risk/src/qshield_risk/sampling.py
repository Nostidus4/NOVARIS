"""Structured true-objective samples for the two-bit four-level QUBO surrogate."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd  # type: ignore[import-untyped]

from qshield_risk.objective import financial_objective, financial_objective_from_growth
from qshield_risk.paths import asset_growth_paths, validate_scenario_cube
from qshield_risk.portfolio import validate_ticker_order


@dataclass(frozen=True)
class ObjectiveSampleDataset:
    """Leakage-safe true-objective train/validation/holdout splits and manifest."""

    train: pd.DataFrame
    validation: pd.DataFrame
    holdout: pd.DataFrame
    manifest: dict[str, Any]


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


def _random_stratified_vectors(
    *,
    candidate_count: int,
    count: int,
    seed: int,
    excluded: set[str],
) -> np.ndarray:
    """Generate unique four-level actions balanced cyclically by active-asset count."""
    if count < 0:
        raise ValueError("[risk.sampling] random sample count must be non-negative.")
    dimension = 2 * candidate_count
    available = (1 << dimension) - len(excluded)
    if count > available:
        raise ValueError(
            f"[risk.sampling] requested {count} unique samples but only {available} remain."
        )
    if count == 0:
        return np.empty((0, dimension), dtype=np.int8)
    rng = np.random.default_rng(seed)
    vectors: list[np.ndarray] = []
    seen = set(excluded)
    attempts = 0
    maximum_attempts = max(10_000, count * 500)
    while len(vectors) < count and attempts < maximum_attempts:
        attempts += 1
        target_active = 1 + ((attempts - 1) % candidate_count)
        active = rng.choice(candidate_count, size=target_active, replace=False)
        vector = np.zeros(dimension, dtype=np.int8)
        levels = rng.integers(1, 4, size=target_active)
        for asset, level in zip(active, levels, strict=True):
            # level 1/2/3 maps to bit pairs 10/01/11.
            vector[2 * asset] = int(level in (1, 3))
            vector[2 * asset + 1] = int(level in (2, 3))
        bitstring = "".join(str(int(bit)) for bit in vector)
        if bitstring in seen:
            continue
        seen.add(bitstring)
        vectors.append(vector)
    if len(vectors) != count:
        raise RuntimeError(
            f"[risk.sampling] could not generate {count} unique stratified samples "
            f"after {attempts} attempts."
        )
    return np.stack(vectors)


def _fit_random_split_counts(
    requested: Mapping[str, int], *, available: int
) -> tuple[dict[str, int], bool]:
    """Proportionally shrink analysis splits when an underfilled bitspace is exhaustive."""
    if available < 0 or any(value < 0 for value in requested.values()):
        raise ValueError("[risk.sampling] sample counts and available states must be non-negative.")
    total = sum(requested.values())
    if total <= available:
        return dict(requested), False
    if total == 0 or available == 0:
        return {name: 0 for name in requested}, total > available

    exact = {name: available * value / total for name, value in requested.items()}
    fitted = {name: int(np.floor(value)) for name, value in exact.items()}
    remaining = available - sum(fitted.values())
    order = sorted(
        requested,
        key=lambda name: (-(exact[name] - fitted[name]), name),
    )
    for name in order[:remaining]:
        fitted[name] += 1
    return fitted, True


def _evaluate_vectors(
    vectors: np.ndarray,
    *,
    sample_types: Sequence[str],
    split: str,
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    candidates: Sequence[str],
    config: Mapping[str, Any],
    chunk_size: int,
    growth_paths: npt.ArrayLike | None = None,
) -> pd.DataFrame:
    if chunk_size <= 0:
        raise ValueError("[risk.sampling] chunk_size must be positive.")
    tickers = validate_ticker_order(ticker_order)
    ordered = tuple(str(ticker) for ticker in candidates)
    indices = [tickers.index(ticker) for ticker in ordered]
    growth = (
        np.asarray(growth_paths, dtype=float)
        if growth_paths is not None
        else asset_growth_paths(
            validate_scenario_cube(
                scenarios,
                expected_horizon=int(config.get("horizon_days", 20)),
                expected_assets=len(tickers),
            )
        )
    )
    rows: list[dict[str, object]] = []
    for start in range(0, len(vectors), chunk_size):
        stop = min(start + chunk_size, len(vectors))
        for sample_id in range(start, stop):
            bits = vectors[sample_id]
            decoded = decode_four_level_bits(bits, candidate_count=len(ordered))
            reductions = np.zeros(len(tickers), dtype=float)
            reductions[indices] = decoded
            result = financial_objective_from_growth(
                reductions, growth, tickers, weights, cash_weight, config
            )
            reduction_sum = float(decoded.sum())
            maximum_sum = max(len(ordered) * 0.30, 1e-12)
            fraction = reduction_sum / maximum_sum
            cash_bucket = "low" if fraction < 1 / 3 else "medium" if fraction < 2 / 3 else "high"
            row: dict[str, object] = {
                "sample_id": sample_id,
                "split": split,
                "sample_type": str(sample_types[sample_id]),
                "bitstring": "".join(str(int(bit)) for bit in bits),
                "decoded_actions": {
                    ticker: float(value)
                    for ticker, value in zip(ordered, decoded, strict=True)
                },
                "action_count": int(np.count_nonzero(decoded)),
                "reduction_sum": reduction_sum,
                "cash_bucket": cash_bucket,
                "objective": result.value,
                "constraint_violations": result.constraint_violations,
                "constraint_details": tuple(
                    item.to_dict() for item in result.constraint_details
                ),
                "feasible": not result.constraint_violations,
            }
            for name, component in result.components.items():
                row[f"{name}_raw"] = component.raw
                row[f"{name}_scaled"] = component.scaled
                row[f"{name}_weight"] = component.weight
                row[f"{name}_contribution"] = component.contribution
            rows.append(row)
    base_columns = (
        "sample_id",
        "split",
        "sample_type",
        "bitstring",
        "decoded_actions",
        "action_count",
        "reduction_sum",
        "cash_bucket",
        "objective",
        "constraint_violations",
        "constraint_details",
        "feasible",
    )
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=base_columns)


def _split_hash(frame: pd.DataFrame) -> str:
    payload = "\n".join(sorted(frame["bitstring"].astype(str))).encode()
    return hashlib.sha256(payload).hexdigest()


def sample_objective_dataset(
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    candidates: Sequence[str],
    config: Mapping[str, Any],
    *,
    candidate_order_hash: str | None = None,
) -> ObjectiveSampleDataset:
    """Build registered structured+random splits with no accidental bitstring overlap."""
    tickers = validate_ticker_order(ticker_order)
    ordered = tuple(str(ticker) for ticker in candidates)
    if not ordered or len(set(ordered)) != len(ordered):
        raise ValueError("[risk.sampling] candidates must be unique and non-empty.")
    missing = sorted(set(ordered) - set(tickers))
    if missing:
        raise ValueError(f"[risk.sampling] candidates absent from ticker_order: {missing}.")
    raw = config.get("objective_sampling")
    if not isinstance(raw, Mapping):
        raise TypeError("[risk.sampling] objective_sampling config is required.")
    requested_counts = {
        "train_random": int(raw.get("train_random_count", 500)),
        "validation": int(raw.get("validation_count", 500)),
        "holdout": int(raw.get("holdout_count", 1_000)),
    }
    seeds_raw = raw.get("seeds")
    if not isinstance(seeds_raw, Mapping):
        raise TypeError("[risk.sampling] objective_sampling.seeds is required.")
    seed_names = ("train", "validation", "holdout")
    if any(seeds_raw.get(name) is None for name in seed_names):
        raise ValueError("[risk.sampling] train, validation and holdout seeds are required.")
    seeds = {name: int(seeds_raw[name]) for name in seed_names}
    if len(set(seeds.values())) != 3:
        raise ValueError("[risk.sampling] split seeds must be distinct.")
    chunk_size = int(raw.get("chunk_size", 64))
    cube = validate_scenario_cube(
        scenarios,
        expected_horizon=int(config.get("horizon_days", 20)),
        expected_assets=len(tickers),
    )
    growth = asset_growth_paths(cube)

    structured, kinds = structured_bit_vectors(len(ordered))
    available_random_states = (1 << (2 * len(ordered))) - len(structured)
    counts, sampling_truncated = _fit_random_split_counts(
        requested_counts,
        available=available_random_states,
    )
    excluded = {"".join(str(int(bit)) for bit in vector) for vector in structured}
    train_random = _random_stratified_vectors(
        candidate_count=len(ordered),
        count=counts["train_random"],
        seed=seeds["train"],
        excluded=excluded,
    )
    excluded.update("".join(str(int(bit)) for bit in vector) for vector in train_random)
    validation_vectors = _random_stratified_vectors(
        candidate_count=len(ordered),
        count=counts["validation"],
        seed=seeds["validation"],
        excluded=excluded,
    )
    excluded.update("".join(str(int(bit)) for bit in vector) for vector in validation_vectors)
    holdout_vectors = _random_stratified_vectors(
        candidate_count=len(ordered),
        count=counts["holdout"],
        seed=seeds["holdout"],
        excluded=excluded,
    )

    train_vectors = np.concatenate((structured, train_random), axis=0)
    train_types = (*kinds, *("random_stratified" for _ in range(len(train_random))))
    train = _evaluate_vectors(
        train_vectors,
        sample_types=train_types,
        split="train",
        scenarios=scenarios,
        ticker_order=tickers,
        weights=weights,
        cash_weight=cash_weight,
        candidates=ordered,
        config=config,
        chunk_size=chunk_size,
        growth_paths=growth,
    )
    validation = _evaluate_vectors(
        validation_vectors,
        sample_types=("random_stratified",) * len(validation_vectors),
        split="validation",
        scenarios=scenarios,
        ticker_order=tickers,
        weights=weights,
        cash_weight=cash_weight,
        candidates=ordered,
        config=config,
        chunk_size=chunk_size,
        growth_paths=growth,
    )
    holdout = _evaluate_vectors(
        holdout_vectors,
        sample_types=("random_stratified",) * len(holdout_vectors),
        split="holdout",
        scenarios=scenarios,
        ticker_order=tickers,
        weights=weights,
        cash_weight=cash_weight,
        candidates=ordered,
        config=config,
        chunk_size=chunk_size,
        growth_paths=growth,
    )
    split_sets = [set(frame["bitstring"]) for frame in (train, validation, holdout)]
    if split_sets[0] & split_sets[1] or split_sets[0] & split_sets[2] or split_sets[1] & split_sets[2]:
        raise RuntimeError("[risk.sampling] objective sample splits overlap.")

    order_hash = candidate_order_hash or hashlib.sha256(
        json.dumps(ordered, separators=(",", ":")).encode()
    ).hexdigest()
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()
    manifest = {
        "sampling_policy_version": str(raw.get("policy_version", "provisional-v2")),
        "candidate_order": list(ordered),
        "candidate_order_hash": order_hash,
        "config_hash": config_hash,
        "candidate_count": len(ordered),
        "bit_count": 2 * len(ordered),
        "structured_count": len(structured),
        "requested_random_counts": requested_counts,
        "counts": {"train": len(train), "validation": len(validation), "holdout": len(holdout)},
        "available_random_states": available_random_states,
        "sampling_truncated": sampling_truncated,
        "sampling_warning": (
            "INSUFFICIENT_STATE_SPACE_FOR_REQUESTED_SPLITS" if sampling_truncated else None
        ),
        "seeds": seeds,
        "chunk_size": chunk_size,
        "split_hashes": {
            "train": _split_hash(train),
            "validation": _split_hash(validation),
            "holdout": _split_hash(holdout),
        },
        "overlap_count": 0,
        "status": "NON_BASELINE_RUN",
    }
    return ObjectiveSampleDataset(train, validation, holdout, manifest)
