# Đỗ Ngọc Tân - test Config.load: merge includes, key của base_yaml đè lên include.
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
    assert cfg["y"] == 3  # b.yaml (include sau) đè a.yaml (include trước)
    assert cfg["z"] == 4
    assert cfg["seed"] == 42
    assert "includes" not in cfg


def test_base_yaml_keys_override_includes(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("x: 1\n", encoding="utf-8")
    base = tmp_path / "base.yaml"
    base.write_text("includes:\n  - a.yaml\nx: 999\n", encoding="utf-8")

    cfg = Config.load(base)

    assert cfg["x"] == 999  # key của base_yaml đè include


def test_config_is_dict_like(tmp_path: Path) -> None:
    base = tmp_path / "base.yaml"
    base.write_text("seed: 7\n", encoding="utf-8")

    cfg = Config.load(base)

    assert isinstance(cfg, dict)
    assert cfg.get("missing_key", "default") == "default"


def test_load_real_base_yaml() -> None:
    """Đối chiếu với configs/base.yaml thật của repo — phải load được, không lỗi."""
    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config.load(repo_root / "configs" / "base.yaml")

    assert "date_range" in cfg
    assert cfg["expected_ticker_count"] == 30


def test_load_provisional_downstream_runtime() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config.load(
        repo_root / "configs" / "provisional" / "workflow_update_downstream.yaml"
    )

    runtime = cfg.workflow_runtime()

    assert runtime.profile_id == "workflow_update_downstream"
    assert runtime.profile_status == "NON_BASELINE_RUN"
    assert runtime.candidate_count == 10
    assert runtime.total_decision_bits == 20
    assert runtime.minimum_structured_samples == 211
    assert runtime.structured_sample_count == 211


def test_load_profiled_deep_merges_provisional_override() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config.load_profiled(
        repo_root / "configs" / "base.yaml",
        repo_root / "configs" / "profiles" / "workflow_update.yaml",
        repo_root / "configs" / "provisional" / "workflow_update_downstream.yaml",
    )

    runtime = cfg.workflow_runtime()
    assert runtime.profile_id == "workflow_update_downstream"
    assert runtime.profile_status == "NON_BASELINE_RUN"
    assert runtime.candidate_count == 10
    assert runtime.total_decision_bits == 20
    assert runtime.structured_sample_count == 211
    assert runtime.minimum_structured_samples == 211
    assert cfg["quantum"]["input_candidates"] == 10
    assert cfg["quantum"]["bit_encoding"]["total_decision_bits"] == 20
    assert cfg["transaction_cost"]["fee"] is not None
    assert cfg["financial_objective"]["components"]["cvar"]["weight"] == 1.0
    assert cfg["date_range"]["test_end"] == "2026-07-31"


def test_load_profiled_carries_decision_package_keys() -> None:
    """Decision-package TL-007…018 / TL-012 must survive load_profiled merge."""
    from qshield_contracts.schemas.downstream import (
        validate_transaction_cost_excludes_liquidity,
    )

    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config.load_profiled(
        repo_root / "configs" / "base.yaml",
        repo_root / "configs" / "profiles" / "workflow_update.yaml",
        repo_root / "configs" / "provisional" / "workflow_update_downstream.yaml",
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
    assert cfg["quantum"]["qaoa"]["NON_FINAL_CONFIG"] is True
    assert cfg["quantum"]["qaoa"]["dev_mode"]["enabled"] is True
    assert "cost_sensitivity" in cfg
    assert "performance_budget" in cfg
    assert cfg["benchmark"]["require_same_qubo_hash"] is True
    validate_transaction_cost_excludes_liquidity(cfg)


def test_load_profiled_override_extends_chain() -> None:
    """Delta-only bakeoff override must inherit Decision-package keys via ``extends``."""
    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config.load_profiled(
        repo_root / "configs" / "base.yaml",
        repo_root / "configs" / "profiles" / "workflow_update.yaml",
        repo_root / "configs" / "provisional" / "qaoa_benchmark_10bit.yaml",
    )

    runtime = cfg.workflow_runtime()
    assert runtime.profile_id == "qaoa_benchmark_10bit"
    assert runtime.candidate_count == 5
    assert runtime.total_decision_bits == 10
    assert runtime.structured_sample_count == 56
    # Inherited from workflow_update_downstream.yaml — not re-copied in the 10-bit file.
    assert cfg["transaction_cost"]["fee"] == 0.0015
    assert cfg["weight_sum_tolerance"] == 1e-8
    assert cfg["financial_objective"]["priority"] == "cvar_first"
    assert cfg["quantum"]["input_candidates"] == 5
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
    assert cfg["artifacts"]["root"] == "artifacts_bench"
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
