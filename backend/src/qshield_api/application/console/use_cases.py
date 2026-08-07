"""Console use cases — map artifact views into page DTOs (no finance formulas)."""

from __future__ import annotations

from qshield_api.application.console.assemble import (
    assemble_data,
    assemble_overview,
    assemble_quantum,
    assemble_regime,
    assemble_report,
    assemble_risk,
    assemble_scenarios,
    assemble_shell,
)
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
from qshield_api.domain.benchmark.repository import BenchmarkRepository
from qshield_api.domain.regime.repository import RegimeRepository
from qshield_api.domain.runs.repository import RunRepository
from qshield_api.domain.scenarios.repository import ScenarioRepository
from qshield_api.domain.workflow.repository import WorkflowRepository
from qshield_api.infrastructure.persistence.regime_repository_impl import (
    RegimeArtifactMissingError,
)
from qshield_api.infrastructure.persistence.scenario_repository_impl import (
    ScenarioArtifactMissingError,
)


def _safe_workflow(repo: WorkflowRepository):
    try:
        return repo.get_summary()
    except OSError, ValueError, KeyError, TypeError, RuntimeError, AttributeError:
        return None


def get_console_shell(workflow_repo: WorkflowRepository) -> ConsoleShellDTO:
    return assemble_shell(_safe_workflow(workflow_repo))


def get_console_overview(workflow_repo: WorkflowRepository) -> ConsoleOverviewDTO:
    return assemble_overview(_safe_workflow(workflow_repo))


def get_console_data(workflow_repo: WorkflowRepository) -> ConsoleDataDTO:
    return assemble_data(_safe_workflow(workflow_repo))


def get_console_regime(
    workflow_repo: WorkflowRepository,
    regime_repo: RegimeRepository,
) -> ConsoleRegimeDTO:
    view = _safe_workflow(workflow_repo)
    current = None
    timeline = None
    try:
        current = regime_repo.get_current()
    except RegimeArtifactMissingError:
        current = None
    try:
        timeline = regime_repo.get_timeline()
    except RegimeArtifactMissingError:
        timeline = None
    return assemble_regime(view, current=current, timeline=timeline)


def get_console_scenarios(
    workflow_repo: WorkflowRepository,
    scenario_repo: ScenarioRepository,
) -> ConsoleScenariosDTO:
    view = _safe_workflow(workflow_repo)
    scenario = None
    try:
        scenario = scenario_repo.get_summary()
    except ScenarioArtifactMissingError:
        scenario = None
    return assemble_scenarios(view, scenario=scenario)


def get_console_risk(workflow_repo: WorkflowRepository) -> ConsoleRiskDTO:
    return assemble_risk(_safe_workflow(workflow_repo))


def get_console_quantum(
    workflow_repo: WorkflowRepository,
    benchmark_repo: BenchmarkRepository,
) -> ConsoleQuantumDTO:
    view = _safe_workflow(workflow_repo)
    benchmark = benchmark_repo.get_benchmark()
    return assemble_quantum(view, benchmark=benchmark)


def get_console_report(
    workflow_repo: WorkflowRepository,
    run_repo: RunRepository,
) -> ConsoleReportDTO:
    view = _safe_workflow(workflow_repo)
    run = run_repo.get_run("dev")
    return assemble_report(view, run=run)
