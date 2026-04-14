import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import sys

from observer_rock.application.monitoring import (
    MonitorExecutionStageError,
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
    workspace_root: Path
    state_root: Path
    service_count: int
    analysis_profile_count: int
    configured_monitor_count: int
    execution: MonitorExecutionResult[PersistedMonitorSourceToAnalysisArtifacts]


@dataclass(frozen=True, slots=True)
class RunSchedulerCommandResult:
    workspace_root: Path
    service_count: int
    analysis_profile_count: int
    configured_monitor_count: int
    due_monitor_count: int
    skipped_monitor_count: int
    tick: datetime
    monitor_results: tuple[RunMonitorCommandResult, ...]


@dataclass(frozen=True, slots=True)
class ListMonitorsCommandEntry:
    monitor_id: str
    schedule: str
    source_plugin: str
    analysis_profiles: tuple[str, ...]
    outputs: tuple[tuple[str, str, str], ...]
    due: bool


@dataclass(frozen=True, slots=True)
class ListMonitorsCommandResult:
    configured_monitor_count: int
    tick: datetime
    monitors: tuple[ListMonitorsCommandEntry, ...]


@dataclass(frozen=True, slots=True)
class ValidateWorkspaceServiceEntry:
    service_name: str
    plugin: str
    token_env: str | None
    has_token: bool
    path: str | None


@dataclass(frozen=True, slots=True)
class ValidateWorkspaceAnalysisProfileEntry:
    profile_name: str
    plugin: str
    model_service: str


@dataclass(frozen=True, slots=True)
class ValidateWorkspaceMonitorEntry:
    monitor_id: str
    schedule: str
    source_plugin: str
    source_path: str | None
    analysis_profiles: tuple[str, ...]
    outputs: tuple[tuple[str, str, str], ...]
    due: bool


@dataclass(frozen=True, slots=True)
class ValidateWorkspaceCommandResult:
    workspace_root: Path
    tick: datetime
    plugin_import_paths: tuple[str, ...]
    services: tuple[ValidateWorkspaceServiceEntry, ...]
    analysis_profiles: tuple[ValidateWorkspaceAnalysisProfileEntry, ...]
    monitors: tuple[ValidateWorkspaceMonitorEntry, ...]


def _scheduler_now() -> datetime:
    return datetime.now(UTC)


def run_monitor_command(
    *,
    workspace_root: Path,
    monitor_id: str,
    source_plugins: Mapping[str, object] | None = None,
    analysis_plugins: Mapping[str, object] | None = None,
    renderer_plugins: Mapping[str, object] | None = None,
    notifier_plugins: Mapping[str, object] | None = None,
) -> RunMonitorCommandResult:
    workspace_config = load_workspace_config(workspace_root, env=dict(os.environ))
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
    for plugin_name, plugin in (renderer_plugins or {}).items():
        registry.register_renderer_plugin(plugin_name, plugin)
    for plugin_name, plugin in (notifier_plugins or {}).items():
        registry.register_notifier_plugin(plugin_name, plugin)

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
    return RunMonitorCommandResult(
        workspace_root=workspace_root,
        state_root=state_root,
        service_count=len(workspace_config.services.services),
        analysis_profile_count=(
            len(workspace_config.analysis_profiles.analysis_profiles)
            if workspace_config.analysis_profiles is not None
            else 0
        ),
        configured_monitor_count=(
            len(workspace_config.monitors.monitors) if workspace_config.monitors is not None else 0
        ),
        execution=execution,
    )


def run_scheduler_command(
    *,
    workspace_root: Path,
    source_plugins: Mapping[str, object] | None = None,
    analysis_plugins: Mapping[str, object] | None = None,
    renderer_plugins: Mapping[str, object] | None = None,
    notifier_plugins: Mapping[str, object] | None = None,
    tick: datetime | None = None,
) -> RunSchedulerCommandResult:
    workspace_config = load_workspace_config(workspace_root, env=dict(os.environ))
    configured_monitors = workspace_config.monitors.monitors if workspace_config.monitors else ()
    effective_tick = tick or _scheduler_now()
    due_monitors = tuple(
        monitor for monitor in configured_monitors if _is_schedule_due(monitor.schedule, effective_tick)
    )
    monitor_results = tuple(
        run_monitor_command(
            workspace_root=workspace_root,
            monitor_id=monitor.id,
            source_plugins=source_plugins,
            analysis_plugins=analysis_plugins,
            renderer_plugins=renderer_plugins,
            notifier_plugins=notifier_plugins,
        )
        for monitor in due_monitors
    )
    return RunSchedulerCommandResult(
        workspace_root=workspace_root,
        service_count=len(workspace_config.services.services),
        analysis_profile_count=(
            len(workspace_config.analysis_profiles.analysis_profiles)
            if workspace_config.analysis_profiles is not None
            else 0
        ),
        configured_monitor_count=len(configured_monitors),
        due_monitor_count=len(due_monitors),
        skipped_monitor_count=len(configured_monitors) - len(due_monitors),
        tick=effective_tick,
        monitor_results=monitor_results,
    )


def list_monitors_command(
    *,
    workspace_root: Path,
    tick: datetime | None = None,
) -> ListMonitorsCommandResult:
    workspace_config = load_workspace_config(workspace_root, env=dict(os.environ))
    configured_monitors = workspace_config.monitors.monitors if workspace_config.monitors else ()
    effective_tick = tick or _scheduler_now()
    return ListMonitorsCommandResult(
        configured_monitor_count=len(configured_monitors),
        tick=effective_tick,
        monitors=tuple(
            ListMonitorsCommandEntry(
                monitor_id=monitor.id,
                schedule=monitor.schedule,
                source_plugin=monitor.source.plugin,
                analysis_profiles=tuple(
                    analysis.profile for analysis in (monitor.analyses or [])
                ),
                outputs=tuple(
                    (
                        output.profile,
                        output.renderer,
                        output.service,
                    )
                    for output in (monitor.outputs or [])
                ),
                due=_is_schedule_due(monitor.schedule, effective_tick),
            )
            for monitor in configured_monitors
        ),
    )


def validate_workspace_command(
    *,
    workspace_root: Path,
    tick: datetime | None = None,
) -> ValidateWorkspaceCommandResult:
    workspace_config = load_workspace_config(workspace_root, env=dict(os.environ))
    effective_tick = tick or _scheduler_now()
    configured_monitors = workspace_config.monitors.monitors if workspace_config.monitors else ()
    configured_analysis_profiles = (
        workspace_config.analysis_profiles.analysis_profiles
        if workspace_config.analysis_profiles is not None
        else {}
    )
    return ValidateWorkspaceCommandResult(
        workspace_root=workspace_config.root,
        tick=effective_tick,
        plugin_import_paths=tuple(workspace_config.services.plugin_import_paths),
        services=tuple(
            ValidateWorkspaceServiceEntry(
                service_name=service_name,
                plugin=service.plugin,
                token_env=service.token_env,
                has_token=service.token is not None,
                path=service.path,
            )
            for service_name, service in workspace_config.services.services.items()
        ),
        analysis_profiles=tuple(
            ValidateWorkspaceAnalysisProfileEntry(
                profile_name=profile_name,
                plugin=profile.plugin,
                model_service=profile.model_service,
            )
            for profile_name, profile in configured_analysis_profiles.items()
        ),
        monitors=tuple(
            ValidateWorkspaceMonitorEntry(
                monitor_id=monitor.id,
                schedule=monitor.schedule,
                source_plugin=monitor.source.plugin,
                source_path=monitor.source.config.get("path")
                if isinstance(monitor.source.config.get("path"), str)
                else None,
                analysis_profiles=tuple(
                    analysis.profile for analysis in (monitor.analyses or [])
                ),
                outputs=tuple(
                    (
                        output.profile,
                        output.renderer,
                        output.service,
                    )
                    for output in (monitor.outputs or [])
                ),
                due=_is_schedule_due(monitor.schedule, effective_tick),
            )
            for monitor in configured_monitors
        ),
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
