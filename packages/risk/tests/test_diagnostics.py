"""P0-1: chẩn đoán objective phải ĐO đúng, và tuyệt đối không tự đổi tham số tài chính."""

from __future__ import annotations

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import pytest
from qshield_risk.diagnostics import (
    _config_without_component,
    build_objective_diagnostics,
    economic_sanity,
    landscape_diagnostics,
    target_cash_sweep,
)
from qshield_risk.paths import asset_growth_paths

_TICKERS = ("AAA", "BBB", "CCC")
_CANDIDATES = ("AAA", "BBB")


def _config(**overrides: object) -> dict:
    base = {
        "horizon_days": 4,
        "cvar_alpha": 0.95,
        "confidence_levels": [0.95],
        "weight_sum_tolerance": 1e-8,
        "maximum_reduction": 0.30,
        "target_cash_increment": 0.10,
        "transaction_cost": {
            "fee": 0.0015,
            "spread": 0.001,
            "liquidity_penalty": 0.0005,
        },
        "financial_objective": {
            "components": {
                "cvar": {"weight": 1.0, "scale": 0.1},
                "return_sacrifice": {"weight": 0.25, "scale": 0.05},
                "transaction_cost": {"weight": 0.25, "scale": 0.01},
                "turnover": {"weight": 0.05, "scale": 0.2},
                "liquidity_penalty": {"weight": 0.25, "scale": 0.01},
                "cash_budget_deviation": {"weight": 0.35, "scale": 0.1},
            }
        },
    }
    base.update(overrides)
    return base


def _cube(*, drift: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(drift, 0.01, size=(200, 4, len(_TICKERS)))


def _weights() -> dict[str, float]:
    return {ticker: 1.0 / len(_TICKERS) for ticker in _TICKERS}


def test_disabling_a_component_never_mutates_the_caller_config() -> None:
    """Ablation phải làm trên BẢN SAO — nếu nó sửa config gốc thì mọi bước sau chạy sai tham số."""
    config = _config()
    original = config["financial_objective"]["components"]["cvar"]["weight"]

    clone = _config_without_component(config, "cvar")

    assert clone["financial_objective"]["components"]["cvar"]["weight"] == 0.0
    assert config["financial_objective"]["components"]["cvar"]["weight"] == original
    assert (
        config["financial_objective"]["components"]["return_sacrifice"]["weight"]
        == clone["financial_objective"]["components"]["return_sacrifice"]["weight"]
    )


def test_unknown_component_is_rejected_instead_of_silently_ignored() -> None:
    with pytest.raises(KeyError, match="khong_ton_tai"):
        _config_without_component(_config(), "khong_ton_tai")


def test_target_cash_sweep_flags_the_ceiling_and_leaves_config_untouched() -> None:
    """Target >= trần vật lý ⇒ chỉ còn đúng một nghiệm đưa deviation về 0 (bán hết mức)."""
    config = _config()
    growth = asset_growth_paths(_cube(drift=-0.001))
    weights = _weights()
    # Trần = tổng weight candidate * 0.30 = (2/3) * 0.30 = 0.20
    rows = target_cash_sweep(
        growth,
        _TICKERS,
        weights,
        0.0,
        config,
        [0, 1],
        targets=(0.05, 0.20, 0.30),
        restarts=4,
        seed=0,
    )

    by_target = {row["target_cash_increment"]: row for row in rows}
    assert by_target[0.05]["max_reachable_cash"] == pytest.approx(0.20)
    assert by_target[0.05]["target_at_or_above_ceiling"] is False
    assert by_target[0.20]["target_at_or_above_ceiling"] is True
    assert by_target[0.30]["target_at_or_above_ceiling"] is True
    # Sweep dùng override cục bộ — config gốc không được đổi.
    assert config["target_cash_increment"] == 0.10


def test_economic_sanity_flags_when_selling_raises_expected_return() -> None:
    """Bán cổ phiếu sang tiền mặt yield 0% mà kỳ vọng lợi nhuận TĂNG ⇒ cube có kỳ vọng âm."""
    config = _config()
    weights = _weights()
    negative = economic_sanity(
        asset_growth_paths(_cube(drift=-0.002)), _TICKERS, weights, 0.0, config, [0, 1]
    )
    assert negative["flag"] == "SELLING_INCREASES_EXPECTED_RETURN"
    assert negative["selling_increases_expected_return"] is True
    assert set(negative["candidates_with_negative_expected_return"]) <= set(_CANDIDATES)

    positive = economic_sanity(
        asset_growth_paths(_cube(drift=0.002)), _TICKERS, weights, 0.0, config, [0, 1]
    )
    assert positive["flag"] is None
    assert positive["candidates_with_negative_expected_return"] == {}


def test_landscape_reports_monotone_objective_as_near_perfect_correlation() -> None:
    """Objective tuyến tính đơn điệu theo tổng bán ⇒ |corr| ~ 1 ⇒ không có cấu trúc tổ hợp."""
    bitstrings, objectives, contributions = [], [], []
    for value in range(16):
        bits = format(value, "04b")
        levels = (
            10 * int(bits[0])
            + 20 * int(bits[1])
            + 10 * int(bits[2])
            + 20 * int(bits[3])
        )
        bitstrings.append(bits)
        objectives.append(-float(levels))
        contributions.append(float(levels))
    frame = pd.DataFrame(
        {
            "bitstring": bitstrings,
            "objective": objectives,
            "cvar_contribution": contributions,
            "cash_budget_deviation_contribution": [v * 3 for v in contributions],
        }
    )

    result = landscape_diagnostics(frame, bit_count=4)

    assert result["objective_vs_reduction_correlation"] == pytest.approx(-1.0, abs=1e-9)
    assert result["dominant_component"] == "cash_budget_deviation"
    assert result["dominant_span_over_cvar"] == pytest.approx(3.0)


def test_landscape_rejects_frames_without_the_required_columns() -> None:
    with pytest.raises(ValueError, match="objective"):
        landscape_diagnostics(pd.DataFrame({"bitstring": ["0000"]}), bit_count=4)


def test_build_objective_diagnostics_is_marked_diagnostic_only() -> None:
    """Artifact phải tự khai là chẩn đoán — không được lẫn vào chuỗi bằng chứng baseline."""
    payload = build_objective_diagnostics(
        _cube(drift=-0.001),
        _TICKERS,
        _weights(),
        0.0,
        _CANDIDATES,
        _config(),
        samples=None,
        restarts=3,
        seed=0,
    )

    assert payload["status"] == "DIAGNOSTIC_ONLY_NON_BASELINE_RUN"
    assert payload["bit_count"] == 2 * len(_CANDIDATES)
    assert payload["landscape"] == {"status": "NO_SAMPLES_PROVIDED"}
    assert {row["disabled_component"] for row in payload["component_ablation"]} == {
        None,
        "cvar",
        "return_sacrifice",
        "transaction_cost",
        "turnover",
        "liquidity_penalty",
        "cash_budget_deviation",
    }


def test_build_objective_diagnostics_rejects_candidates_outside_the_universe() -> None:
    with pytest.raises(ValueError, match="absent from ticker_order"):
        build_objective_diagnostics(
            _cube(drift=-0.001),
            _TICKERS,
            _weights(),
            0.0,
            ("AAA", "ZZZ"),
            _config(),
            restarts=2,
        )


def test_diagnostic_descent_matches_brute_force_on_a_small_grid() -> None:
    """Coordinate descent của chẩn đoán phải tìm đúng nghiệm mà duyệt hết 4^M tìm được.

    Khoá hành vi vì vòng lặp trong `_best_by_coordinate_descent` dùng chung biến `original` vừa
    làm cờ bỏ qua mức đang giữ, vừa làm "mức tốt nhất tới giờ" — đúng nhưng dễ gãy nếu ai đó
    sửa lại sau này mà không có test đối chiếu độc lập.
    """
    import itertools

    from qshield_risk.diagnostics import _best_by_coordinate_descent, _evaluate

    config = _config()
    growth = asset_growth_paths(_cube(drift=-0.0005, seed=42))
    weights = _weights()
    indices = [0, 1]

    levels, value = _best_by_coordinate_descent(
        growth, _TICKERS, weights, 0.0, config, indices, restarts=8, seed=0
    )

    best_brute: tuple[float, tuple[float, ...]] | None = None
    for combo in itertools.product((0.0, 0.10, 0.20, 0.30), repeat=len(indices)):
        reductions = np.zeros(len(_TICKERS), dtype=float)
        reductions[indices] = combo
        candidate = (
            _evaluate(reductions, growth, _TICKERS, weights, 0.0, config),
            combo,
        )
        if best_brute is None or candidate < best_brute:
            best_brute = candidate

    assert best_brute is not None
    assert value == pytest.approx(best_brute[0])
    assert tuple(float(v) for v in levels) == pytest.approx(best_brute[1])
