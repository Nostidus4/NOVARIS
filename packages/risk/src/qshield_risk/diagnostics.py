"""Chẩn đoán hình dạng hàm mục tiêu — công cụ ĐO cho owner, không tự đổi tham số.

Bối cảnh (P0-1): trên dữ liệu evidence hiện tại, nghiệm tối ưu luôn là all-ones (bán 30% mọi mã).
Đo được `corr(objective, tổng mức bán) = -0.9993` trên 711 mẫu train — hàm mục tiêu gần như TUYẾN
TÍNH ĐƠN ĐIỆU theo tổng lượng bán, nên không tồn tại bài toán tổ hợp để giải và mọi solver
(exact / classical / QAOA) đều trả cùng một đáp án.

Module này KHÔNG sửa chữa hiện tượng đó. Sửa nghĩa là đổi `target_cash_increment` hoặc
`financial_objective.components.*.weight/scale` — tham số tài chính thuộc quyền Phúc/Ngọc
(CLAUDE.md: `configs/` do Ngọc duyệt; docs/decisions/2026-08-31-phan-hoi-bao-cao-15-08.md CR-WF2-002 owner Phúc+Tú→Ngọc). Tự hạ trọng số để
nghiệm hết degenerate chính là loại rủi ro cần tránh: đổi số cho ra kết quả mong muốn.

Thay vào đó module trả về BẰNG CHỨNG để owner quyết:
- `component_ablation`  — tắt từng thành phần objective, xem nghiệm dịch đi đâu.
- `target_cash_sweep`   — quét target cash, xem nghiệm đổi từ mức nào.
- `landscape`           — tương quan/biên độ/số local minimum của bề mặt tối ưu.
- `economic_sanity`     — cờ đỏ khi bán cổ phiếu sang tiền mặt mà kỳ vọng lợi nhuận lại TĂNG.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd  # type: ignore[import-untyped]

from qshield_risk.objective import COMPONENT_NAMES, financial_objective_from_growth
from qshield_risk.paths import asset_growth_paths, validate_scenario_cube
from qshield_risk.portfolio import validate_ticker_order
from qshield_risk.sampling import decode_four_level_bits, structured_bit_vectors

_ACTION_STEP_PCT = (0.0, 0.10, 0.20, 0.30)


def _config_without_component(config: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Bản sao config với `weight` của MỘT thành phần đặt về 0 — không chạm config gốc."""
    clone = copy.deepcopy(dict(config))
    components = clone.setdefault("financial_objective", {}).setdefault(
        "components", {}
    )
    if name not in components:
        raise KeyError(
            f"[risk.diagnostics] financial_objective.components.{name} không tồn tại."
        )
    components[name] = {**dict(components[name]), "weight": 0.0}
    return clone


def _evaluate(
    reductions: npt.ArrayLike,
    growth: np.ndarray,
    tickers: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
) -> float:
    return financial_objective_from_growth(
        reductions, growth, tickers, weights, cash_weight, config
    ).value


def _best_by_coordinate_descent(
    growth: np.ndarray,
    tickers: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
    candidate_indices: Sequence[int],
    *,
    restarts: int,
    seed: int,
) -> tuple[np.ndarray, float]:
    """Multi-start coordinate descent trên lưới 4 mức — deterministic theo `seed`.

    Dùng thay vì duyệt hết 4^M vì diagnostic phải chạy được ở mọi M; `restarts` gồm hai góc
    (không hành động / bán hết mức) cộng các điểm ngẫu nhiên có seed cố định.
    """
    rng = np.random.default_rng(seed)
    n_assets = len(tickers)
    n_candidates = len(candidate_indices)
    starts: list[np.ndarray] = [
        np.zeros(n_candidates, dtype=float),
        np.full(n_candidates, _ACTION_STEP_PCT[-1], dtype=float),
    ]
    starts.extend(
        rng.choice(_ACTION_STEP_PCT, size=n_candidates)
        for _ in range(max(0, restarts - len(starts)))
    )

    def full_vector(levels: np.ndarray) -> np.ndarray:
        reductions = np.zeros(n_assets, dtype=float)
        reductions[list(candidate_indices)] = levels
        return reductions

    best: tuple[float, tuple[float, ...]] | None = None
    for start in starts:
        current = np.asarray(start, dtype=float).copy()
        current_value = _evaluate(
            full_vector(current), growth, tickers, weights, cash_weight, config
        )
        improved = True
        while improved:
            improved = False
            for position in range(n_candidates):
                original = current[position]
                for level in _ACTION_STEP_PCT:
                    if level == original:
                        continue
                    current[position] = level
                    value = _evaluate(
                        full_vector(current),
                        growth,
                        tickers,
                        weights,
                        cash_weight,
                        config,
                    )
                    if value < current_value - 1e-15:
                        current_value, original, improved = value, level, True
                current[position] = original
        candidate = (current_value, tuple(float(v) for v in current))
        if best is None or candidate < best:
            best = candidate
    if best is None:
        raise RuntimeError(
            "[risk.diagnostics] coordinate descent không có điểm xuất phát nào."
        )
    return np.asarray(best[1], dtype=float), best[0]


def component_ablation(
    growth: np.ndarray,
    tickers: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
    candidate_indices: Sequence[int],
    *,
    restarts: int = 12,
    seed: int = 0,
) -> list[dict[str, Any]]:
    """Tắt từng thành phần objective rồi tìm lại nghiệm — trả lời "thành phần nào ép all-ones".

    `hamming_to_max_sell` = số candidate KHÔNG ở mức 30%. Bằng 0 nghĩa là nghiệm vẫn dính biên.
    """
    maximum = float(config.get("maximum_reduction", 0.30))
    rows: list[dict[str, Any]] = []
    for name in ("__none__", *COMPONENT_NAMES):
        variant = (
            dict(config)
            if name == "__none__"
            else _config_without_component(config, name)
        )
        levels, value = _best_by_coordinate_descent(
            growth,
            tickers,
            weights,
            cash_weight,
            variant,
            candidate_indices,
            restarts=restarts,
            seed=seed,
        )
        rows.append(
            {
                "disabled_component": None if name == "__none__" else name,
                "objective": value,
                "levels_pct": [round(float(v) * 100, 4) for v in levels],
                "reduction_sum_pct": round(float(levels.sum()) * 100, 4),
                "active_candidates": int(np.count_nonzero(levels)),
                "hamming_to_max_sell": int(np.count_nonzero(levels < maximum - 1e-12)),
                "is_max_sell": bool(np.all(levels >= maximum - 1e-12)),
                "is_no_action": bool(np.all(levels <= 1e-12)),
            }
        )
    return rows


def target_cash_sweep(
    growth: np.ndarray,
    tickers: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
    candidate_indices: Sequence[int],
    *,
    targets: Sequence[float] = (0.02, 0.04, 0.06, 0.08, 0.10),
    restarts: int = 12,
    seed: int = 0,
) -> list[dict[str, Any]]:
    """Quét `target_cash_increment` qua override CỤC BỘ — file config trên đĩa không bị chạm.

    `max_reachable_cash` là trần vật lý: bán hết mức mọi candidate. Khi target >= trần này thì chỉ
    còn ĐÚNG MỘT nghiệm đưa `cash_budget_deviation` về 0, và nghiệm đó luôn là bán hết mức.
    """
    maximum = float(config.get("maximum_reduction", 0.30))
    reachable = sum(float(weights[tickers[i]]) for i in candidate_indices) * maximum
    rows: list[dict[str, Any]] = []
    for target in targets:
        variant = {**dict(config), "target_cash_increment": float(target)}
        levels, value = _best_by_coordinate_descent(
            growth,
            tickers,
            weights,
            cash_weight,
            variant,
            candidate_indices,
            restarts=restarts,
            seed=seed,
        )
        rows.append(
            {
                "target_cash_increment": float(target),
                "max_reachable_cash": float(reachable),
                "target_at_or_above_ceiling": bool(target >= reachable - 1e-12),
                "objective": value,
                "levels_pct": [round(float(v) * 100, 4) for v in levels],
                "reduction_sum_pct": round(float(levels.sum()) * 100, 4),
                "is_max_sell": bool(np.all(levels >= maximum - 1e-12)),
            }
        )
    return rows


def landscape_diagnostics(samples: pd.DataFrame, *, bit_count: int) -> dict[str, Any]:
    """Đo hình dạng bề mặt từ mẫu true-objective đã có (không cần chạy lại risk).

    `objective_vs_reduction_correlation` gần -1 nghĩa là objective gần như hàm tuyến tính đơn điệu
    của tổng lượng bán ⇒ không có cấu trúc tổ hợp, QUBO/QAOA không có gì để đóng góp.
    """
    if "objective" not in samples.columns or "bitstring" not in samples.columns:
        raise ValueError(
            "[risk.diagnostics] samples cần cột `objective` và `bitstring`."
        )
    frame = samples.copy()
    bits = np.vstack(
        [
            np.fromiter((int(ch) for ch in str(value).zfill(bit_count)), dtype=np.int8)
            for value in frame["bitstring"]
        ]
    )
    levels = np.vstack(
        [decode_four_level_bits(row, candidate_count=bit_count // 2) for row in bits]
    )
    reduction_sum = levels.sum(axis=1)
    objective = frame["objective"].to_numpy(dtype=float)
    correlation = (
        float(np.corrcoef(objective, reduction_sum)[0, 1])
        if objective.std() > 0 and reduction_sum.std() > 0
        else float("nan")
    )

    spans = {
        name: float(
            frame[f"{name}_contribution"].max() - frame[f"{name}_contribution"].min()
        )
        for name in COMPONENT_NAMES
        if f"{name}_contribution" in frame.columns
    }
    dominant = max(spans, key=lambda key: spans[key]) if spans else None

    # Local minimum theo 1-bit-flip, chỉ tính trên tập mẫu (không duyệt 2^d).
    energy_by_bitstring = {
        str(value).zfill(bit_count): float(score)
        for value, score in zip(frame["bitstring"], objective, strict=True)
    }
    local_minima = 0
    comparable = 0
    for bitstring, energy in energy_by_bitstring.items():
        neighbours = []
        for index in range(bit_count):
            flipped = list(bitstring)
            flipped[index] = "0" if flipped[index] == "1" else "1"
            neighbour = energy_by_bitstring.get("".join(flipped))
            if neighbour is not None:
                neighbours.append(neighbour)
        if not neighbours:
            continue
        comparable += 1
        if all(energy <= neighbour + 1e-15 for neighbour in neighbours):
            local_minima += 1

    return {
        "sample_count": len(frame),
        "objective_vs_reduction_correlation": correlation,
        "component_contribution_span": spans,
        "dominant_component": dominant,
        "dominant_span_over_cvar": (
            float(spans[dominant] / spans["cvar"])
            if dominant and spans.get("cvar", 0.0) > 0.0
            else None
        ),
        "local_minima_in_sample": local_minima,
        "states_with_sampled_neighbours": comparable,
        "note": (
            "local_minima đếm TRÊN TẬP MẪU, không phải toàn bộ 2^d — chỉ so được giữa các run "
            "dùng cùng bộ mẫu."
        ),
    }


def economic_sanity(
    growth: np.ndarray,
    tickers: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    config: Mapping[str, Any],
    candidate_indices: Sequence[int],
) -> dict[str, Any]:
    """Cờ đỏ: bán cổ phiếu sang tiền mặt (yield 0%) mà kỳ vọng lợi nhuận TĂNG.

    Điều đó chỉ xảy ra khi scenario cube cho kỳ vọng lợi nhuận ÂM ở các mã bị bán — tức nghiệm
    "bán hết mức" đến từ hình dạng cube, không phải từ đánh đổi rủi ro–lợi nhuận. Khi cờ này bật,
    vấn đề nằm ở scenario generation chứ không ở optimizer.
    """
    maximum = float(config.get("maximum_reduction", 0.30))
    n_assets = len(tickers)
    zero = np.zeros(n_assets, dtype=float)
    max_sell = zero.copy()
    max_sell[list(candidate_indices)] = maximum

    before = financial_objective_from_growth(
        zero, growth, tickers, weights, cash_weight, config
    )
    after = financial_objective_from_growth(
        max_sell, growth, tickers, weights, cash_weight, config
    )
    expected_before = float(before.after.expected_horizon_return)
    expected_after = float(after.after.expected_horizon_return)

    # Kỳ vọng lợi nhuận horizon của TỪNG tài sản, để chỉ đích danh mã có kỳ vọng âm.
    horizon_return = growth.prod(axis=1) - 1.0
    mean_by_asset = horizon_return.mean(axis=0)
    negative = {
        str(tickers[i]): float(mean_by_asset[i])
        for i in candidate_indices
        if mean_by_asset[i] < 0.0
    }
    return {
        "expected_return_no_action": expected_before,
        "expected_return_max_sell": expected_after,
        "selling_increases_expected_return": bool(expected_after > expected_before),
        "candidates_with_negative_expected_return": negative,
        "candidate_count": len(candidate_indices),
        "flag": (
            "SELLING_INCREASES_EXPECTED_RETURN"
            if expected_after > expected_before
            else None
        ),
        "note": (
            "Cash yield giả định 0% (CR-WF2-003 chưa duyệt). Nếu cờ bật, điều tra scenario cube "
            "trước khi điều chỉnh objective."
        ),
    }


def build_objective_diagnostics(
    scenarios: npt.ArrayLike,
    ticker_order: Sequence[str],
    weights: Mapping[str, float],
    cash_weight: float,
    candidates: Sequence[str],
    config: Mapping[str, Any],
    *,
    samples: pd.DataFrame | None = None,
    restarts: int = 12,
    seed: int = 0,
) -> dict[str, Any]:
    """Gộp bốn chẩn đoán thành một payload artifact."""
    tickers = validate_ticker_order(ticker_order)
    ordered = tuple(str(ticker) for ticker in candidates)
    missing = sorted(set(ordered) - set(tickers))
    if missing:
        raise ValueError(
            f"[risk.diagnostics] candidates absent from ticker_order: {missing}."
        )
    indices = [tickers.index(ticker) for ticker in ordered]
    cube = validate_scenario_cube(
        scenarios,
        expected_horizon=int(config.get("horizon_days", 20)),
        expected_assets=len(tickers),
    )
    growth = asset_growth_paths(cube)
    bit_count = 2 * len(ordered)

    payload: dict[str, Any] = {
        "candidate_order": list(ordered),
        "bit_count": bit_count,
        "structured_sample_count": len(structured_bit_vectors(len(ordered))[0]),
        "component_ablation": component_ablation(
            growth,
            tickers,
            weights,
            cash_weight,
            config,
            indices,
            restarts=restarts,
            seed=seed,
        ),
        "target_cash_sweep": target_cash_sweep(
            growth,
            tickers,
            weights,
            cash_weight,
            config,
            indices,
            restarts=restarts,
            seed=seed,
        ),
        "economic_sanity": economic_sanity(
            growth, tickers, weights, cash_weight, config, indices
        ),
        "landscape": (
            landscape_diagnostics(samples, bit_count=bit_count)
            if samples is not None
            else {"status": "NO_SAMPLES_PROVIDED"}
        ),
        "status": "DIAGNOSTIC_ONLY_NON_BASELINE_RUN",
        "note": (
            "Chẩn đoán để owner (Phúc/Ngọc) chốt tham số tài chính. Module này KHÔNG đổi "
            "target_cash_increment hay weight/scale — xem docs/decisions/2026-08-31-phan-hoi-bao-cao-15-08.md CR-WF2-002."
        ),
    }
    return payload
