# Liễu Hoài Phúc / Đỗ Ngọc Tân - true objective cho thí nghiệm QAOA-assisted: grid, multistart, polish.
"""Risk side của thí nghiệm hybrid (plan-qaoa-assisted.md Pha 2).

- ``ObjectiveContext``: growth paths tính MỘT lần mỗi instance; mọi đánh giá đi qua
  ``financial_objective_from_growth`` — cùng hàm với sampling/rerank/polish, không công thức mới.
- ``TrueObjectiveScorer``: đếm số trạng thái unique bị chấm (budget B). Trạng thái đã chấm trong
  cùng scorer không tốn thêm (memoization là hợp lệ với mọi nguồn như nhau).
- ``exact_true_grid``: ``J*_grid`` = min true objective trên lưới 4 mức (song song theo process).
  Chỉ là reference — không bao giờ seed track khác.
- ``true_coordinate_search_pool``: classical multistart trên TRUE objective (baseline T1/T4).
- ``polish_top_candidates``: cùng polishing (±5pp, zero-lock) với cùng top-k và evaluation cap cho
  mọi nguồn.

Package này KHÔNG import ``qshield_quantum`` (chiều phụ thuộc một chiều): proposal đi vào dưới dạng
dict thuần có ``bitstring``.
"""

from __future__ import annotations

import multiprocessing
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from qshield_risk.evaluate import required_float
from qshield_risk.metrics import alpha_key
from qshield_risk.objective import FinancialObjective, financial_objective_from_growth
from qshield_risk.paths import asset_growth_paths, validate_scenario_cube
from qshield_risk.portfolio import validate_ticker_order
from qshield_risk.rerank import polish_reductions
from qshield_risk.sampling import decode_four_level_bits

_LEVEL_TO_BITS = {0: "00", 10: "10", 20: "01", 30: "11"}
_LEVELS = (0, 10, 20, 30)


@dataclass(frozen=True)
class ObjectiveContext:
    growth: np.ndarray
    tickers: tuple[str, ...]
    weights: dict[str, float]
    cash_weight: float
    config: dict[str, Any]
    candidates: tuple[str, ...]
    candidate_indices: tuple[int, ...]

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def bit_count(self) -> int:
        return 2 * len(self.candidates)

    def reductions_from_bitstring(self, bitstring: str) -> np.ndarray:
        if len(bitstring) != self.bit_count or set(bitstring) - {"0", "1"}:
            raise ValueError(
                f"[risk.hybrid] bitstring {bitstring!r} is not a {self.bit_count}-bit string."
            )
        bits = np.fromiter((int(char) for char in bitstring), dtype=int)
        reductions = np.zeros(len(self.tickers), dtype=float)
        reductions[list(self.candidate_indices)] = decode_four_level_bits(
            bits, candidate_count=self.candidate_count
        )
        return reductions

    def evaluate(self, reductions: npt.ArrayLike) -> FinancialObjective:
        return financial_objective_from_growth(
            reductions,
            self.growth,
            self.tickers,
            self.weights,
            self.cash_weight,
            self.config,
        )


def build_objective_context(
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    candidates: Sequence[str],
    config: Mapping[str, Any],
) -> ObjectiveContext:
    tickers = validate_ticker_order(ticker_order)
    ordered = tuple(str(ticker) for ticker in candidates)
    if not ordered or len(set(ordered)) != len(ordered):
        raise ValueError("[risk.hybrid] candidates must be unique and non-empty.")
    missing = sorted(set(ordered) - set(tickers))
    if missing:
        raise ValueError(
            f"[risk.hybrid] candidates absent from ticker_order: {missing}."
        )
    cube = validate_scenario_cube(
        scenarios,
        expected_horizon=int(config.get("horizon_days", 20)),
        expected_assets=len(tickers),
    )
    return ObjectiveContext(
        growth=asset_growth_paths(cube),
        tickers=tickers,
        weights={str(k): float(v) for k, v in weights.items()},
        cash_weight=float(cash_weight),
        config=dict(config),
        candidates=ordered,
        candidate_indices=tuple(tickers.index(ticker) for ticker in ordered),
    )


def levels_from_bitstring(bitstring: str) -> np.ndarray:
    bits = np.fromiter((int(char) for char in bitstring), dtype=int).reshape(-1, 2)
    return 10 * bits[:, 0] + 20 * bits[:, 1]


def bitstring_from_levels(levels_pct: Sequence[int] | np.ndarray) -> str:
    try:
        return "".join(_LEVEL_TO_BITS[int(level)] for level in levels_pct)
    except KeyError as exc:
        raise ValueError(f"[risk.hybrid] level outside {_LEVELS}: {exc}.") from exc


# --------------------------------------------------------------------------- exact true grid


@dataclass(frozen=True)
class TrueGrid:
    values: np.ndarray
    feasible: np.ndarray
    seconds: float
    workers: int

    @property
    def bit_count(self) -> int:
        return int(self.values.shape[0]).bit_length() - 1

    def ordered_indices(self) -> np.ndarray:
        """Feasible trước, rồi true objective tăng dần, rồi chỉ số (tie-break tất định)."""
        indices = np.arange(self.values.shape[0])
        return np.lexsort((indices, self.values, ~self.feasible))

    def best_index(self) -> int:
        return int(self.ordered_indices()[0])

    def top_indices(self, k: int) -> np.ndarray:
        return self.ordered_indices()[:k]

    def feasible_rank(self, value: float) -> int:
        """1 + số trạng thái feasible có objective NHỎ HƠN hẳn ``value``."""
        feasible_values = np.sort(self.values[self.feasible])
        return int(np.searchsorted(feasible_values, value, side="left")) + 1


def _evaluate_range(
    context: ObjectiveContext, start: int, stop: int
) -> tuple[int, np.ndarray, np.ndarray]:
    values = np.empty(stop - start, dtype=float)
    feasible = np.empty(stop - start, dtype=bool)
    width = context.bit_count
    for offset, index in enumerate(range(start, stop)):
        result = context.evaluate(
            context.reductions_from_bitstring(format(index, f"0{width}b"))
        )
        values[offset] = result.value
        feasible[offset] = not result.constraint_violations
    return start, values, feasible


# State của process worker (spawn initializer) — không phải state của thuật toán: mỗi worker nhận
# đúng một ObjectiveContext bất biến thay vì pickle growth paths cho từng chunk.
_WORKER_CONTEXT: ObjectiveContext | None = None


def _init_grid_worker(context: ObjectiveContext) -> None:
    global _WORKER_CONTEXT
    _WORKER_CONTEXT = context


def _grid_worker(bounds: tuple[int, int]) -> tuple[int, np.ndarray, np.ndarray]:
    if _WORKER_CONTEXT is None:
        raise RuntimeError("[risk.hybrid] grid worker was not initialised.")
    return _evaluate_range(_WORKER_CONTEXT, *bounds)


def exact_true_grid(
    context: ObjectiveContext,
    *,
    workers: int = 1,
    chunk_size: int = 2048,
    max_bits: int = 20,
) -> TrueGrid:
    """True objective của MỌI trạng thái lưới 4 mức (``2^(2M)``)."""
    if context.bit_count > max_bits:
        raise ValueError(
            f"[risk.hybrid] exact true grid refused: {context.bit_count} bits > max_bits="
            f"{max_bits}. Use best-known reference instead."
        )
    started = time.perf_counter()
    size = 1 << context.bit_count
    values = np.empty(size, dtype=float)
    feasible = np.empty(size, dtype=bool)
    bounds = [
        (start, min(start + chunk_size, size)) for start in range(0, size, chunk_size)
    ]
    if workers <= 1:
        chunks = (_evaluate_range(context, start, stop) for start, stop in bounds)
        for start, chunk_values, chunk_feasible in chunks:
            values[start : start + len(chunk_values)] = chunk_values
            feasible[start : start + len(chunk_values)] = chunk_feasible
    else:
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=multiprocessing.get_context("spawn"),
            initializer=_init_grid_worker,
            initargs=(context,),
        ) as pool:
            for start, chunk_values, chunk_feasible in pool.map(_grid_worker, bounds):
                values[start : start + len(chunk_values)] = chunk_values
                feasible[start : start + len(chunk_values)] = chunk_feasible
    return TrueGrid(values, feasible, time.perf_counter() - started, max(1, workers))


# --------------------------------------------------------------------------- scoring


class TrueObjectiveScorer:
    """Chấm bitstring bằng true objective và đếm số trạng thái UNIQUE đã chấm.

    Có ``grid`` thì tra bảng (cùng giá trị — grid được tính bằng đúng hàm này) nhưng vẫn tính
    phí như một lần đánh giá, để accounting giữa các track không phụ thuộc cache.
    """

    def __init__(
        self, context: ObjectiveContext, *, grid: TrueGrid | None = None
    ) -> None:
        self.context = context
        self.grid = grid
        self._cache: dict[str, tuple[float, bool]] = {}

    @property
    def evaluations(self) -> int:
        return len(self._cache)

    def is_scored(self, bitstring: str) -> bool:
        return bitstring in self._cache

    def score(self, bitstring: str) -> tuple[float, bool]:
        cached = self._cache.get(bitstring)
        if cached is not None:
            return cached
        if self.grid is not None:
            index = int(bitstring, 2)
            outcome = (float(self.grid.values[index]), bool(self.grid.feasible[index]))
        else:
            result = self.context.evaluate(
                self.context.reductions_from_bitstring(bitstring)
            )
            outcome = (float(result.value), not result.constraint_violations)
        self._cache[bitstring] = outcome
        return outcome

    def score_proposals(
        self, proposals: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in proposals:
            value, feasible = self.score(str(item["bitstring"]))
            rows.append(
                {**dict(item), "true_objective": value, "true_feasible": feasible}
            )
        return rows


def true_coordinate_search_pool(
    scorer: TrueObjectiveScorer,
    *,
    predicate_mask: np.ndarray,
    budget: int,
    seed: int,
    max_restarts: int = 100_000,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Multistart best-improvement coordinate search trên lưới 4 mức, true objective.

    Mỗi bước thử mọi (mã, mức) khác mức hiện tại, chỉ trong predicate-feasible domain. Pool = mọi
    trạng thái unique đã chấm, theo thứ tự chấm, dừng đúng khi đủ ``budget``.
    """
    if budget < 0:
        raise ValueError(f"budget must be non-negative, got {budget}.")
    mask = np.asarray(predicate_mask, dtype=bool)
    width = scorer.context.bit_count
    if mask.shape != (1 << width,):
        raise ValueError(
            f"predicate_mask must have shape ({1 << width},), got {mask.shape}."
        )
    feasible_indices = np.flatnonzero(mask)
    target = min(budget, len(feasible_indices))
    rng = np.random.default_rng(seed)
    start_count = scorer.evaluations
    order: dict[str, None] = {}
    restarts = 0
    local_minima = 0

    def key(bitstring: str) -> tuple[bool, float]:
        value, feasible = scorer.score(bitstring)
        order.setdefault(bitstring, None)
        return (not feasible, value)

    def exhausted() -> bool:
        return scorer.evaluations - start_count >= target

    while not exhausted() and restarts < max_restarts:
        restarts += 1
        current = format(int(rng.choice(feasible_indices)), f"0{width}b")
        if not scorer.is_scored(current) and exhausted():
            break
        current_key = key(current)
        while not exhausted():
            levels = levels_from_bitstring(current)
            best: tuple[tuple[bool, float], str] | None = None
            for candidate in rng.permutation(len(levels)):
                for level in _LEVELS:
                    if level == levels[candidate]:
                        continue
                    trial = levels.copy()
                    trial[candidate] = level
                    trial_bits = bitstring_from_levels(trial)
                    if not mask[int(trial_bits, 2)]:
                        continue
                    if not scorer.is_scored(trial_bits) and exhausted():
                        continue
                    trial_key = key(trial_bits)
                    if trial_key < (best[0] if best else current_key):
                        best = (trial_key, trial_bits)
            if best is None:
                local_minima += 1
                break
            current, current_key = best[1], best[0]
    rows = [
        {
            "bitstring": bits,
            "source_method": "classical_true",
            "source_rank": rank,
            "source_seed": seed,
        }
        for rank, bits in enumerate(order, start=1)
    ]
    return rows, {"restarts": restarts, "local_minima_reached": local_minima}


# --------------------------------------------------------------------------- polishing


def objective_snapshot(
    result: FinancialObjective, config: Mapping[str, Any]
) -> dict[str, Any]:
    """Các đại lượng tài chính báo cáo cho một nghiệm (loss dương = lỗ; CVaR cao = xấu)."""
    total_weight = float(result.trade.stock_weights.sum() + result.trade.cash_weight)
    if abs(total_weight - 1.0) > 1e-8:
        raise ValueError(
            f"[risk.hybrid] post-trade weights sum to {total_weight}, not 1.0."
        )
    primary = alpha_key(required_float(config, "cvar_alpha"))
    return {
        "true_objective": float(result.value),
        "true_cvar": float(result.after.cvar[primary]),
        "cvar_before": float(result.before.cvar[primary]),
        "cvar_by_level_after": {k: float(v) for k, v in result.after.cvar.items()},
        "return_sacrifice": float(result.components["return_sacrifice"].raw),
        "transaction_cost": float(result.components["transaction_cost"].raw),
        "liquidity_penalty": float(result.components["liquidity_penalty"].raw),
        "turnover": float(result.components["turnover"].raw),
        "cash_budget_deviation": float(result.components["cash_budget_deviation"].raw),
        "cash_weight_after": float(result.trade.cash_weight),
        "worst_drawdown_after": float(result.after.worst_scenario_max_drawdown),
        "constraint_violation_count": len(result.constraint_violations),
        "status": result.status,
    }


def rank_scored(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            not row["true_feasible"],
            row["true_objective"],
            row["bitstring"],
        ),
    )


def polish_top_candidates(
    context: ObjectiveContext,
    scored: Sequence[Mapping[str, Any]],
    *,
    top_k: int,
    max_adjustment: float,
    max_evaluations: int,
) -> list[dict[str, Any]]:
    """Polish top-k (true objective) của MỘT pool với cùng operator/budget cho mọi nguồn."""
    maximum = required_float(context.config, "maximum_reduction")
    traces: list[dict[str, Any]] = []
    for rank, row in enumerate(rank_scored(scored)[:top_k], start=1):
        start = context.reductions_from_bitstring(str(row["bitstring"]))
        result = polish_reductions(
            start,
            None,
            context.tickers,
            context.weights,
            context.cash_weight,
            context.config,
            max_adjustment=max_adjustment,
            maximum_reduction=maximum,
            growth_paths=context.growth,
            max_evaluations=max_evaluations,
        )
        start_value = float(result.quantum_objective.value)
        if abs(start_value - float(row["true_objective"])) > 1e-9 * max(
            1.0, abs(start_value)
        ):
            raise ValueError(
                f"[risk.hybrid] scored objective {row['true_objective']} != polish start "
                f"{start_value} for {row['bitstring']} — grid/scorer inconsistency."
            )
        polished = np.asarray(result.polished_reductions)
        quantum = np.asarray(result.quantum_reductions)
        indices = list(context.candidate_indices)
        traces.append(
            {
                "start_rank": rank,
                "start_bitstring": str(row["bitstring"]),
                "start_source_method": row.get("source_method"),
                "start_source_seed": row.get("source_seed"),
                "start_true_objective": start_value,
                "start_feasible": not result.quantum_objective.constraint_violations,
                "final_true_objective": float(result.polished_objective.value),
                "objective_improvement": start_value
                - float(result.polished_objective.value),
                "polishing_dependency": float(result.polishing_dependency),
                "true_objective_evaluations": int(result.evaluations),
                "iterations": int(result.iterations),
                "wall_seconds": float(result.wall_seconds),
                "active_set_changed": not np.array_equal(
                    np.flatnonzero(polished > 0.0), np.flatnonzero(quantum > 0.0)
                ),
                "zero_action_lock_respected": bool(
                    np.all(polished[quantum == 0.0] == 0.0)
                ),
                "max_adjustment_respected": bool(
                    np.all(np.abs(polished - quantum) <= max_adjustment + 1e-12)
                ),
                "stop_reason": result.stop_reason,
                "final_feasible": not result.polished_objective.constraint_violations,
                "final_reductions_pct": [float(100.0 * polished[i]) for i in indices],
                "final_snapshot": objective_snapshot(
                    result.polished_objective, context.config
                ),
            }
        )
    return traces
