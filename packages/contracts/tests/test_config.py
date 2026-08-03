# Đỗ Ngọc Tân - test Config.load: merge includes, key của base_yaml đè lên include.
from pathlib import Path

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
    assert cfg["expected_ticker_count"] == 8
