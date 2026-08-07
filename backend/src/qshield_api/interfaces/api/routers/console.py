"""Page-shaped console API mapped to the NOVARIS frontend routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from qshield_api.application.console.dto import (
    ConsoleDataDTO,
    ConsoleOverviewDTO,
    ConsoleQuantumDTO,
    ConsoleRegimeDTO,
    ConsoleReportDTO,
    ConsoleRiskDTO,
    ConsoleScenariosDTO,
    ConsoleShellDTO,
)
from qshield_api.application.console.use_cases import (
    get_console_data,
    get_console_overview,
    get_console_quantum,
    get_console_regime,
    get_console_report,
    get_console_risk,
    get_console_scenarios,
    get_console_shell,
)
from qshield_api.deps import (
    get_benchmark_repository,
    get_regime_repository,
    get_run_repository,
    get_scenario_repository,
    get_workflow_repository,
)
from qshield_api.domain.benchmark.repository import BenchmarkRepository
from qshield_api.domain.regime.repository import RegimeRepository
from qshield_api.domain.runs.repository import RunRepository
from qshield_api.domain.scenarios.repository import ScenarioRepository
from qshield_api.domain.workflow.repository import WorkflowRepository

router = APIRouter(prefix="/console", tags=["console"])


@router.get("/shell", response_model=ConsoleShellDTO)
def console_shell(
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
) -> ConsoleShellDTO:
    return get_console_shell(workflow_repo)


@router.get("/overview", response_model=ConsoleOverviewDTO)
def console_overview(
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
) -> ConsoleOverviewDTO:
    return get_console_overview(workflow_repo)


@router.get("/data", response_model=ConsoleDataDTO)
def console_data(
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
) -> ConsoleDataDTO:
    return get_console_data(workflow_repo)


@router.get("/regime", response_model=ConsoleRegimeDTO)
def console_regime(
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    regime_repo: RegimeRepository = Depends(get_regime_repository),
) -> ConsoleRegimeDTO:
    return get_console_regime(workflow_repo, regime_repo)


@router.get("/scenarios", response_model=ConsoleScenariosDTO)
def console_scenarios(
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    scenario_repo: ScenarioRepository = Depends(get_scenario_repository),
) -> ConsoleScenariosDTO:
    return get_console_scenarios(workflow_repo, scenario_repo)


@router.get("/risk", response_model=ConsoleRiskDTO)
def console_risk(
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
) -> ConsoleRiskDTO:
    return get_console_risk(workflow_repo)


@router.get("/quantum", response_model=ConsoleQuantumDTO)
def console_quantum(
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    benchmark_repo: BenchmarkRepository = Depends(get_benchmark_repository),
) -> ConsoleQuantumDTO:
    return get_console_quantum(workflow_repo, benchmark_repo)


@router.get("/report", response_model=ConsoleReportDTO)
def console_report(
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    run_repo: RunRepository = Depends(get_run_repository),
) -> ConsoleReportDTO:
    return get_console_report(workflow_repo, run_repo)
