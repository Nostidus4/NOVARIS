# Đỗ Ngọc Tân - P0-5: personalization_status/note/hashes phải chảy từ runner ra tới response API.
from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from qshield_api.deps import get_optimize_job_repository, get_optimize_runner
from qshield_api.domain.optimize.entities import (
    OptimizeJob,
    OptimizeJobRequest,
    OptimizeJobStatus,
    OptimizeResult,
)
from qshield_api.main import app


class _InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, OptimizeJob] = {}

    def save(self, job: OptimizeJob) -> None:
        self._jobs[job.job_id] = job

    def get(self, job_id: str) -> OptimizeJob | None:
        return self._jobs.get(job_id)

    def list(self) -> list[OptimizeJob]:
        return list(self._jobs.values())


def _make_result(*, status: str, note: str | None) -> OptimizeResult:
    return OptimizeResult(
        bitstring="11111111111111111111",
        requested_solver="qaoa",
        actual_solver="exact",
        exact_energy=0.62,
        classical_energy=0.62,
        optimality_gap=None,
        qaoa_beats_classical=False,
        runtime_seconds=40.0,
        shots=None,
        backend="StatevectorSampler",
        fallback_reason="QAOA skipped/timeout in NON_FINAL_CONFIG",
        profile_id="workflow_update",
        qubo_hash="deadbeef",
        true_cvar_before=0.07,
        true_cvar_after=0.06,
        source_artifact="workflow_benchmark.json",
        personalization_status=status,
        personalization_note=note,
        requested_portfolio_hash="requested-hash",
        evaluated_portfolio_hash="evaluated-hash",
    )


class _FakeRunnerNotApplied:
    def run(self, job_id: str, request: OptimizeJobRequest) -> OptimizeResult:
        assert request.weights == {"FPT": 1.0}
        return _make_result(
            status="NOT_APPLIED",
            note="Kết quả được tính trên danh mục handoff Risk, KHÔNG phải danh mục người dùng.",
        )


class _FakeRunnerMatched:
    def run(self, job_id: str, request: OptimizeJobRequest) -> OptimizeResult:
        return _make_result(status="MATCHED_HANDOFF", note=None)


def test_submit_job_reports_not_applied_when_weights_mismatch_handoff() -> None:
    repo = _InMemoryJobRepository()
    app.dependency_overrides[get_optimize_job_repository] = lambda: repo
    app.dependency_overrides[get_optimize_runner] = lambda: _FakeRunnerNotApplied()
    try:
        client = TestClient(app)
        submit = client.post(
            "/optimize/jobs", json={"weights": {"FPT": 1.0}, "cash_weight": 0.0}
        )
        assert submit.status_code == 202
        job_id = submit.json()["job_id"]

        status = client.get(f"/optimize/jobs/{job_id}")
    finally:
        app.dependency_overrides.clear()

    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "done"
    result = body["result"]
    assert result["personalization_status"] == "NOT_APPLIED"
    assert result["personalization_note"] is not None
    assert "KHÔNG phải danh mục người dùng" in result["personalization_note"]
    assert result["requested_portfolio_hash"] == "requested-hash"
    assert result["evaluated_portfolio_hash"] == "evaluated-hash"
    assert result["requested_portfolio_hash"] != result["evaluated_portfolio_hash"]


def test_submit_job_reports_matched_handoff_when_weights_match() -> None:
    repo = _InMemoryJobRepository()
    app.dependency_overrides[get_optimize_job_repository] = lambda: repo
    app.dependency_overrides[get_optimize_runner] = lambda: _FakeRunnerMatched()
    try:
        client = TestClient(app)
        submit = client.post(
            "/optimize/jobs", json={"weights": {"FPT": 0.5}, "cash_weight": 0.5}
        )
        job_id = submit.json()["job_id"]
        status = client.get(f"/optimize/jobs/{job_id}")
    finally:
        app.dependency_overrides.clear()

    result = status.json()["result"]
    assert result["personalization_status"] == "MATCHED_HANDOFF"
    assert result["personalization_note"] is None


def test_job_repository_round_trips_request_and_personalization(tmp_path) -> None:
    from qshield_contracts.config import Config

    from qshield_api.infrastructure.jobs.file_job_store import FileOptimizeJobRepository

    repo = FileOptimizeJobRepository(cfg=Config({"artifacts": {"root": str(tmp_path)}}))
    job = OptimizeJob(
        job_id="job1",
        status=OptimizeJobStatus.DONE,
        created_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        request=OptimizeJobRequest(weights={"FPT": 0.4, "MWG": 0.6}, cash_weight=0.0),
        result=_make_result(status="NOT_APPLIED", note="mismatch"),
        error=None,
    )
    repo.save(job)
    loaded = repo.get("job1")
    assert loaded is not None
    assert loaded.request.weights == {"FPT": 0.4, "MWG": 0.6}
    assert loaded.request.cash_weight == 0.0
    assert loaded.result is not None
    assert loaded.result.personalization_status == "NOT_APPLIED"
    assert loaded.result.requested_portfolio_hash == "requested-hash"
