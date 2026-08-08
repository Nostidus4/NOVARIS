# Đỗ Ngọc Tân - test Config.load / load_profiled với bộ configs tối giản (3 file).
from pathlib import Path

import pytest
from qshield_contracts.config import Config


def test_load_merges_includes(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("x: 1\ny: 2\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("y: 3\nz: 4\n", encoding="utf-8")
    base = tmp_path / "base.yaml"
    base.write_text("includes:\n  - a.yaml\n  - b.yaml\nseed: 42\n", encoding="utf-8")

    cfg = Config.load(base)

    assert cfg["x"] == 1
    assert cfg["y"] == 3
    assert cfg["z"] == 4
    assert cfg["seed"] == 42
    assert "includes" not in cfg


def test_base_yaml_keys_override_includes(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("x: 1\n", encoding="utf-8")
    base = tmp_path / "base.yaml"
    base.write_text("includes:\n  - a.yaml\nx: 999\n", encoding="utf-8")

    cfg = Config.load(base)

    assert cfg["x"] == 999


def test_config_is_dict_like(tmp_path: Path) -> None:
    base = tmp_path / "base.yaml"
    base.write_text("seed: 7\n", encoding="utf-8")

    cfg = Config.load(base)

    assert isinstance(cfg, dict)
    assert cfg.get("missing_key", "default") == "default"


def test_load_real_base_yaml() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config.load(repo_root / "configs" / "base.yaml")

    assert "date_range" in cfg
    assert cfg["expected_ticker_count"] == 30
    assert cfg["transaction_cost"]["fee"] == 0.0015
    assert cfg["weight_sum_tolerance"] == 1e-8
    assert cfg["target_cash_increment"] == 0.10
    assert cfg["qaoa"]["seeds"][0] == 101
    assert cfg["penalty"]["lambda_1"] == 1.0
    assert cfg["penalty"]["P"] is None


def test_load_workflow_update_profile() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config.load_profiled(
        repo_root / "configs" / "base.yaml",
        repo_root / "configs" / "workflow_update.yaml",
    )

    runtime = cfg.workflow_runtime()
    assert runtime.profile_id == "workflow_update"
    assert runtime.profile_status == "NON_BASELINE_RUN"
    assert runtime.candidate_count == 10
    assert runtime.total_decision_bits == 20
    assert runtime.structured_sample_count == 211
    assert runtime.minimum_structured_samples == 211
    assert cfg["quantum"]["input_candidates"] == 10
    assert cfg["quantum"]["bit_encoding"]["total_decision_bits"] == 20
    assert cfg["transaction_cost"]["fee"] == 0.0015
    assert cfg["financial_objective"]["components"]["cvar"]["weight"] == 1.0
    assert cfg["date_range"]["test_end"] == "2026-07-31"


def test_load_profiled_carries_decision_package_keys() -> None:
    from qshield_contracts.schemas.downstream import (
        validate_transaction_cost_excludes_liquidity,
    )

    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config.load_profiled(
        repo_root / "configs" / "base.yaml",
        repo_root / "configs" / "workflow_update.yaml",
    )

    assert cfg["transaction_cost"]["fee"] == 0.0015
    assert cfg["transaction_cost"]["spread"] == 0.0010
    assert cfg["transaction_cost"]["liquidity_penalty"] == 0.0005
    assert cfg["weight_sum_tolerance"] == 1e-8
    assert cfg["target_cash_increment"] == 0.10
    assert cfg["maximum_reduction"] == 0.30
    assert cfg["financial_objective"]["priority"] == "cvar_first"
    assert cfg["reranking"]["top_distinct_feasible"] == 20
    assert cfg["local_polishing"]["max_adjustment_pp"] == 5
    assert cfg["materiality"]["true_cvar_relative_reduction_min"] == 0.01
    assert cfg["quantum"]["qaoa"]["seeds"] == [
        101,
        202,
        303,
        404,
        505,
        606,
        707,
        808,
        909,
        1001,
    ]
    assert cfg["quantum"]["qaoa"]["warm_start"] is True
    assert "cost_sensitivity" in cfg
    assert "performance_budget" in cfg
    assert cfg["benchmark"]["require_same_qubo_hash"] is True
    validate_transaction_cost_excludes_liquidity(cfg)


def test_load_profiled_override_extends_chain(tmp_path: Path) -> None:
    """Override có ``extends`` phải inherit key từ profile đã gộp."""
    repo_root = Path(__file__).resolve().parents[3]
    wu = (repo_root / "configs" / "workflow_update.yaml").resolve()
    delta = tmp_path / "delta_runtime.yaml"
    delta.write_text(
        f"extends: {wu}\n"
        "profile:\n"
        "  id: delta_test\n"
        "  status: NON_BASELINE_RUN\n"
        "runtime:\n"
        "  candidate_count: 5\n"
        "  bits_per_candidate: 2\n"
        "  total_decision_bits: 10\n"
        "  structured_sample_count: 56\n"
        "  action_levels_pct: [0, 10, 20, 30]\n"
        "quantum:\n"
        "  input_candidates: 5\n",
        encoding="utf-8",
    )
    cfg = Config.load_profiled(
        repo_root / "configs" / "base.yaml",
        repo_root / "configs" / "workflow_update.yaml",
        delta,
    )

    runtime = cfg.workflow_runtime()
    assert runtime.profile_id == "delta_test"
    assert runtime.candidate_count == 5
    assert runtime.total_decision_bits == 10
    assert runtime.structured_sample_count == 56
    assert cfg["transaction_cost"]["fee"] == 0.0015
    assert cfg["weight_sum_tolerance"] == 1e-8
    assert cfg["financial_objective"]["priority"] == "cvar_first"
    assert cfg["quantum"]["input_candidates"] == 5
    assert "extends" not in cfg


def test_override_extends_cycle_raises(tmp_path: Path) -> None:
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    a.write_text("extends: b.yaml\nx: 1\n", encoding="utf-8")
    b.write_text("extends: a.yaml\ny: 2\n", encoding="utf-8")
    base = tmp_path / "base.yaml"
    base.write_text("seed: 1\n", encoding="utf-8")
    profile = tmp_path / "profile.yaml"
    profile.write_text(
        "profile:\n  id: t\n  status: NON_BASELINE_RUN\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="extends cycle"):
        Config.load_profiled(base, profile, a)
    cfg = Config(
        {
            "profile": {"id": "test", "status": "NON_BASELINE_RUN"},
            "runtime": {
                "candidate_count": 8,
                "bits_per_candidate": 2,
                "total_decision_bits": 20,
                "structured_sample_count": 211,
                "action_levels_pct": [0, 10, 20, 30],
            },
        }
    )

    with pytest.raises(ValueError, match="expected 16"):
        cfg.workflow_runtime()


def test_workflow_runtime_supports_10_candidate_target() -> None:
    cfg = Config(
        {
            "profile": {"id": "workflow_update", "status": "BASELINE_TARGET"},
            "runtime": {
                "candidate_count": 10,
                "bits_per_candidate": 2,
                "total_decision_bits": 20,
                "structured_sample_count": 211,
                "action_levels_pct": [0, 10, 20, 30],
            },
        }
    )

    runtime = cfg.workflow_runtime()

    assert runtime.minimum_structured_samples == 211
