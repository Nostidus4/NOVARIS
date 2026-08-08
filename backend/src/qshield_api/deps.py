# Đỗ Ngọc Tân - dependency injection: nơi DUY NHẤT "lắp ráp" infrastructure cụ thể cho interfaces.
"""Mỗi hàm ở đây là một FastAPI `Depends()` factory — trả về implementation THẬT của một Protocol
khai báo ở `domain/*/repository.py`/`runner.py`. Router chỉ gọi `Depends(get_x)`, không tự tạo
infrastructure. Đây là điểm "compose" duy nhất biết cả 2 lớp domain lẫn infrastructure cùng lúc,
đúng vai trò `interfaces/` trong `architecture.md` §2.4.
"""

from __future__ import annotations

from qshield_contracts.config import Config

from qshield_api.config import get_config
from qshield_api.domain.benchmark.repository import BenchmarkRepository
from qshield_api.domain.optimize.repository import OptimizeJobRepository
from qshield_api.domain.optimize.runner import OptimizeRunner
from qshield_api.domain.regime.repository import RegimeRepository
from qshield_api.domain.risk.repository import RiskCalculator
from qshield_api.domain.runs.repository import RunRepository
from qshield_api.domain.scenarios.repository import ScenarioRepository
from qshield_api.domain.workflow.repository import WorkflowRepository
from qshield_api.infrastructure.calculation.qshield_risk_calculator import (
    QshieldRiskCalculator,
)
from qshield_api.infrastructure.jobs.file_job_store import FileOptimizeJobRepository
from qshield_api.infrastructure.persistence.benchmark_repository_impl import (
    FileBenchmarkRepository,
)
from qshield_api.infrastructure.persistence.regime_repository_impl import (
    FileRegimeRepository,
)
from qshield_api.infrastructure.persistence.run_repository_impl import FileRunRepository
from qshield_api.infrastructure.persistence.scenario_repository_impl import (
    FileScenarioRepository,
)
from qshield_api.infrastructure.persistence.workflow_repository_impl import (
    FileWorkflowRepository,
    SupabaseWorkflowRepository,
)
from qshield_api.infrastructure.runner.subprocess_optimize_runner import (
    SubprocessOptimizeRunner,
)


def get_app_config() -> Config:
    return get_config()


def get_run_repository() -> RunRepository:
    return FileRunRepository(cfg=get_app_config())


def get_regime_repository() -> RegimeRepository:
    return FileRegimeRepository(cfg=get_app_config())


def get_scenario_repository() -> ScenarioRepository:
    return FileScenarioRepository(cfg=get_app_config())


def get_risk_calculator() -> RiskCalculator:
    return QshieldRiskCalculator(cfg=get_app_config())


def get_optimize_job_repository() -> OptimizeJobRepository:
    return FileOptimizeJobRepository(cfg=get_app_config())


def get_optimize_runner() -> OptimizeRunner:
    return SubprocessOptimizeRunner(cfg=get_app_config())


def get_benchmark_repository() -> BenchmarkRepository:
    return FileBenchmarkRepository(cfg=get_app_config())


def get_file_workflow_repository() -> FileWorkflowRepository:
    return FileWorkflowRepository(cfg=get_app_config())


def get_workflow_repository() -> WorkflowRepository:
    file_repo = get_file_workflow_repository()
    return SupabaseWorkflowRepository(cfg=get_app_config(), file_repo=file_repo)


def get_universe_tickers() -> list[str]:
    """Danh sách ticker đã khóa (`configs/base.yaml`) — dùng cho `portfolio.validate_
    portfolio`. Không qua `infrastructure/` riêng (feature `portfolio` không cần — xem
    docs/architecture/backend_hexagonal_design.md §1.4)."""
    cfg = get_app_config()
    return [str(entry["ticker"]) for entry in cfg["tickers"]]


def get_weight_sum_tolerance() -> float:
    return float(get_app_config()["weight_sum_tolerance"])
