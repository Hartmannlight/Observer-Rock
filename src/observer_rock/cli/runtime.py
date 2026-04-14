import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sys

from observer_rock.application.monitoring import (
    MonitorExecutionResult,
    PersistedMonitorSourceToAnalysisArtifacts,
    MonitorExecutionService,
)
from observer_rock.application.services import RunService
from observer_rock.config.workspace import load_workspace_config
from observer_rock.infrastructure.artifacts import FilesystemArtifactStore
from observer_rock.infrastructure.sqlite import SqliteDocumentRepository, SqliteRunRepository
from observer_rock.plugins.registry import PluginRegistry


@dataclass(frozen=True, slots=True)
class RunMonitorCommandResult:
    state_root: Path
    execution: MonitorExecutionResult[PersistedMonitorSourceToAnalysisArtifacts]


@dataclass(frozen=True, slots=True)
class RunSchedulerCommandResult:
    configured_monitor_count: int
    monitor_results: tuple[RunMonitorCommandResult, ...]


def _scheduler_now() -> datetime:
    return datetime.now(UTC)


def run_monitor_command(
    *,
    workspace_root: Path,
    monitor_id: str,
    source_plugins: Mapping[str, object] | None = None,
    analysis_plugins: Mapping[str, object] | None = None,
) -> RunMonitorCommandResult:
    workspace_config = load_workspace_config(workspace_root)
    state_root = workspace_root / ".observer_rock"
    registry = PluginRegistry()
    workspace_import_path = str(workspace_root)
    restore_workspace_path = workspace_import_path not in sys.path
    if restore_workspace_path:
        sys.path.insert(0, workspace_import_path)
    try:
        registry.load_plugins(workspace_config.services.plugin_import_paths)
    finally:
        if restore_workspace_path:
            sys.path.remove(workspace_import_path)
    for plugin_name, plugin in (source_plugins or {}).items():
        registry.register_source_plugin(plugin_name, plugin)
    for plugin_name, plugin in (analysis_plugins or {}).items():
        registry.register_analysis_plugin(plugin_name, plugin)

    service = MonitorExecutionService(
        workspace=workspace_config,
        run_service=RunService(SqliteRunRepository(state_root / "runs.db")),
        run_id_factory=lambda configured_monitor_id: _build_run_id(configured_monitor_id),
        plugin_registry=registry,
    )
    execution = service.execute_monitor_source_to_analysis_artifacts(
        monitor_id=monitor_id,
        document_repository=SqliteDocumentRepository(state_root / "documents.db"),
        artifact_store=FilesystemArtifactStore(state_root / "artifacts"),
    )
    return RunMonitorCommandResult(state_root=state_root, execution=execution)


def run_scheduler_command(
    *,
    workspace_root: Path,
    source_plugins: Mapping[str, object] | None = None,
    analysis_plugins: Mapping[str, object] | None = None,
    tick: datetime | None = None,
) -> RunSchedulerCommandResult:
    workspace_config = load_workspace_config(workspace_root)
    configured_monitors = workspace_config.monitors.monitors if workspace_config.monitors else ()
    effective_tick = tick or _scheduler_now()
    monitor_results = tuple(
        run_monitor_command(
            workspace_root=workspace_root,
            monitor_id=monitor.id,
            source_plugins=source_plugins,
            analysis_plugins=analysis_plugins,
        )
        for monitor in configured_monitors
        if _is_schedule_due(monitor.schedule, effective_tick)
    )
    return RunSchedulerCommandResult(
        configured_monitor_count=len(configured_monitors),
        monitor_results=monitor_results,
    )


def _build_run_id(monitor_id: str) -> str:
    return f"{monitor_id}-{uuid.uuid4().hex}"


def _is_schedule_due(schedule: str, tick: datetime) -> bool:
    fields = schedule.split()
    if len(fields) != 5:
        return True

    minute, hour, day_of_month, month, day_of_week = fields
    return all(
        (
            _matches_schedule_field(minute, tick.minute),
            _matches_schedule_field(hour, tick.hour),
            _matches_schedule_field(day_of_month, tick.day),
            _matches_schedule_field(month, tick.month),
            _matches_schedule_field(day_of_week, (tick.weekday() + 1) % 7),
        )
    )


def _matches_schedule_field(field: str, value: int) -> bool:
    if field == "*":
        return True
    if field.startswith("*/"):
        step = field[2:]
        if step.isdigit() and int(step) > 0:
            return value % int(step) == 0
        return True
    if field.isdigit():
        return int(field) == value
    return True
