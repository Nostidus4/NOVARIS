# Đỗ Ngọc Tân - P0-5: OptimizeRunner phải đối chiếu request.weights với handoff Risk trung thực.
"""Job luôn chạy trên handoff Risk trên đĩa (không re-price theo request) — nhưng phải nói thật
khi handoff đó không khớp danh mục người dùng gửi lên, thay vì âm thầm coi như đã áp dụng.
"""

from __future__ import annotations

import json
from pathlib import Path

from qshield_contracts.config import Config
from qshield_contracts.enums import Stage
from qshield_contracts.paths import ArtifactPaths

from qshield_api.domain.optimize.entities import OptimizeJobRequest
from qshield_api.infrastructure.runner.subprocess_optimize_runner import (
    SubprocessOptimizeRunner,
    _check_personalization,
    _portfolio_hash,
    _weights_match,
)


def test_weights_match_within_tolerance() -> None:
    assert _weights_match(
        {"FPT": 0.1, "MWG": 0.2}, {"FPT": 0.1, "MWG": 0.2}, tolerance=1e-8
    )
    assert _weights_match({"FPT": 0.1}, {"FPT": 0.1 + 5e-9}, tolerance=1e-8)


def test_weights_match_detects_missing_and_extra_tickers() -> None:
    assert not _weights_match({"FPT": 0.1}, {"FPT": 0.1, "MWG": 0.2}, tolerance=1e-8)
    assert not _weights_match({"FPT": 0.1, "MWG": 0.2}, {"FPT": 0.1}, tolerance=1e-8)


def test_portfolio_hash_is_stable_regardless_of_key_order() -> None:
    a = _portfolio_hash({"MWG": 0.2, "FPT": 0.1}, 0.7)
    b = _portfolio_hash({"FPT": 0.1, "MWG": 0.2}, 0.7)
    assert a == b
    assert len(a) == 64  # sha256 hex digest


def test_portfolio_hash_changes_when_weights_differ() -> None:
    a = _portfolio_hash({"FPT": 0.1}, 0.9)
    b = _portfolio_hash({"FPT": 0.11}, 0.89)
    assert a != b


def test_check_personalization_matched_handoff() -> None:
    request = OptimizeJobRequest(weights={"FPT": 0.5, "MWG": 0.3}, cash_weight=0.2)
    result = _check_personalization(
        request,
        handoff_weights={"FPT": 0.5, "MWG": 0.3},
        handoff_cash_weight=0.2,
        tolerance=1e-8,
    )
    assert result.status == "MATCHED_HANDOFF"
    assert result.note is None
    assert result.requested_hash == result.evaluated_hash


def test_check_personalization_not_applied_when_mismatched() -> None:
    request = OptimizeJobRequest(weights={"FPT": 1.0}, cash_weight=0.0)
    result = _check_personalization(
        request,
        handoff_weights={f"T{i}": 1 / 30 for i in range(30)},
        handoff_cash_weight=0.0,
        tolerance=1e-8,
    )
    assert result.status == "NOT_APPLIED"
    assert result.note is not None
    assert "KHÔNG phải danh mục người dùng" in result.note
    assert result.requested_hash != result.evaluated_hash


def _write_risk_summary(
    job_paths: ArtifactPaths, *, weights: dict, cash_weight: float
) -> None:
    risk_dir = job_paths.stage_dir(Stage.RISK)
    risk_dir.mkdir(parents=True, exist_ok=True)
    (risk_dir / "risk_summary.json").write_text(
        json.dumps({"portfolio_weights": weights, "cash_weight": cash_weight}),
        encoding="utf-8",
    )


def test_runner_personalize_reads_handoff_and_flags_mismatch(tmp_path: Path) -> None:
    cfg = Config(
        {
            "artifacts": {"root": str(tmp_path), "mode": "runs"},
            "weight_sum_tolerance": 1e-8,
        }
    )
    job_paths = ArtifactPaths(cfg, run_id="job_abc")
    _write_risk_summary(job_paths, weights={"FPT": 1.0}, cash_weight=0.0)

    runner = SubprocessOptimizeRunner(cfg=cfg)

    matched_request = OptimizeJobRequest(weights={"FPT": 1.0}, cash_weight=0.0)
    matched = runner._personalize(job_paths, matched_request)
    assert matched.status == "MATCHED_HANDOFF"
    assert matched.note is None

    mismatched_request = OptimizeJobRequest(weights={"MWG": 1.0}, cash_weight=0.0)
    mismatched = runner._personalize(job_paths, mismatched_request)
    assert mismatched.status == "NOT_APPLIED"
    assert mismatched.note is not None


def test_runner_personalize_uses_config_tolerance(tmp_path: Path) -> None:
    cfg = Config(
        {
            "artifacts": {"root": str(tmp_path), "mode": "runs"},
            "weight_sum_tolerance": 0.05,
        }
    )
    job_paths = ArtifactPaths(cfg, run_id="job_tol")
    _write_risk_summary(job_paths, weights={"FPT": 1.0}, cash_weight=0.0)

    runner = SubprocessOptimizeRunner(cfg=cfg)
    close_request = OptimizeJobRequest(weights={"FPT": 0.98}, cash_weight=0.0)
    result = runner._personalize(job_paths, close_request)
    assert result.status == "MATCHED_HANDOFF"
