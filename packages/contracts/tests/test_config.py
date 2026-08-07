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
    assert runtime.candidate_count == 8
    assert runtime.total_decision_bits == 16
    assert runtime.minimum_structured_samples == 137
    assert runtime.structured_sample_count == 137


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
    assert runtime.candidate_count == 8
    assert cfg["quantum"]["input_candidates"] == 8
    assert cfg["quantum"]["bit_encoding"]["total_decision_bits"] == 16
    assert cfg["transaction_cost"]["fee"] is not None
    assert cfg["financial_objective"]["components"]["cvar"]["weight"] == 1.0
    assert cfg["date_range"]["test_end"] == "2026-07-31"


def test_workflow_runtime_rejects_inconsistent_dimensions() -> None:
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
