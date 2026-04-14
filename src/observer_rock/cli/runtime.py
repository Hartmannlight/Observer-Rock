import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import difflib
import os
from pathlib import Path
import sys

from observer_rock.application.document_intelligence import (
    DocumentHistoryEntry,
    QueryableDocumentMatch,
    DocumentIntelligenceIndexer,
)
from observer_rock.application.monitoring import (
    MonitorSourceRecord,
    MonitorExecutionStageError,
    MonitorExecutionResult,
    PersistedMonitorSourceToAnalysisArtifacts,
    MonitorExecutionService,
)
from observer_rock.application.services import RunService
from observer_rock.config.workspace import load_workspace_config
from observer_rock.infrastructure.artifacts import FilesystemArtifactStore
from observer_rock.infrastructure.sqlite import (
    SqliteDocumentIntelligenceRepository,
    SqliteDocumentRepository,
    SqliteMonitorChangeTrackingRepository,
    SqliteRunRepository,
)
from observer_rock.plugins.registry import PluginRegistry
from observer_rock.plugins.source import RecentDocumentReference, SourceFetchContext


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
    schedule_evaluations: tuple["SchedulerMonitorEvaluation", ...]
    monitor_results: tuple[RunMonitorCommandResult, ...]


@dataclass(frozen=True, slots=True)
class SchedulerMonitorEvaluation:
    monitor_id: str
    schedule: str
    due: bool


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


@dataclass(frozen=True, slots=True)
class InspectArtifactsStageResult:
    stage: str
    status: str
    document_id: str | None = None
    version: int | None = None
    artifact_path: Path | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    payload: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class InspectArtifactsCommandResult:
    workspace_root: Path
    state_root: Path
    monitor_id: str
    stages: tuple[InspectArtifactsStageResult, ...]


@dataclass(frozen=True, slots=True)
class QueryDocumentsCommandResult:
    workspace_root: Path
    profile_name: str
    contains_text: str
    monitor_id: str | None
    latest_only: bool
    matches: tuple[QueryableDocumentMatch, ...]


@dataclass(frozen=True, slots=True)
class DocumentHistoryComparison:
    from_version: int
    to_version: int
    source_changed: bool
    analysis_changed: bool
    source_diff: tuple[str, ...]
    analysis_diff: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DocumentHistoryCommandResult:
    workspace_root: Path
    document_id: str
    profile_name: str
    entries: tuple[DocumentHistoryEntry, ...]
    comparison: DocumentHistoryComparison | None


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
        source_fetch_context_provider=_build_source_fetch_context_provider(
            workspace_config=workspace_config,
            state_root=state_root,
        ),
    )
    execution = service.execute_monitor_source_to_analysis_artifacts(
        monitor_id=monitor_id,
        document_repository=SqliteDocumentRepository(state_root / "documents.db"),
        artifact_store=FilesystemArtifactStore(state_root / "artifacts"),
    )
    if execution.error is None:
        persisted = execution.value
        DocumentIntelligenceIndexer(
            repository=SqliteDocumentIntelligenceRepository(state_root / "documents.db")
        ).index_monitor_result(
            monitor_id=monitor_id,
            source_data=_load_source_data_payload(
                state_root=state_root,
                monitor_id=monitor_id,
            ),
            analysis=_load_analysis_payload(
                state_root=state_root,
                monitor_id=monitor_id,
            ),
        )
        _update_monitor_change_tracking_state(
            workspace_config=workspace_config,
            state_root=state_root,
            monitor_id=monitor_id,
            source_data=_load_source_data_payload(
                state_root=state_root,
                monitor_id=monitor_id,
            ),
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
    schedule_evaluations = tuple(
        SchedulerMonitorEvaluation(
            monitor_id=monitor.id,
            schedule=monitor.schedule,
            due=_is_schedule_due(monitor.schedule, effective_tick),
        )
        for monitor in configured_monitors
    )
    due_monitor_ids = {evaluation.monitor_id for evaluation in schedule_evaluations if evaluation.due}
    due_monitors = tuple(
        monitor for monitor in configured_monitors if monitor.id in due_monitor_ids
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
        schedule_evaluations=schedule_evaluations,
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


def inspect_artifacts_command(
    *,
    workspace_root: Path,
    monitor_id: str,
) -> InspectArtifactsCommandResult:
    workspace_config = load_workspace_config(workspace_root, env=dict(os.environ))
    _require_monitor(workspace_config=workspace_config, monitor_id=monitor_id)
    state_root = workspace_root / ".observer_rock"
    document_repository = SqliteDocumentRepository(state_root / "documents.db")
    artifact_store = FilesystemArtifactStore(state_root / "artifacts")

    return InspectArtifactsCommandResult(
        workspace_root=workspace_root,
        state_root=state_root,
        monitor_id=monitor_id,
        stages=(
            _inspect_latest_artifact(
                document_repository=document_repository,
                artifact_store=artifact_store,
                stage="source",
                document_id=f"{monitor_id}-source-data",
                artifact_name="monitor_source_data.json",
                content_type="application/json",
            ),
            _inspect_latest_artifact(
                document_repository=document_repository,
                artifact_store=artifact_store,
                stage="analysis",
                document_id=f"{monitor_id}-analysis-output",
                artifact_name="monitor_analysis.json",
                content_type="application/json",
            ),
            _inspect_latest_artifact(
                document_repository=document_repository,
                artifact_store=artifact_store,
                stage="notifications",
                document_id=f"{monitor_id}-notifications",
                artifact_name="monitor_notifications.json",
                content_type="application/json",
            ),
        ),
    )


def query_documents_command(
    *,
    workspace_root: Path,
    profile_name: str,
    contains_text: str,
    monitor_id: str | None = None,
    latest_only: bool = True,
) -> QueryDocumentsCommandResult:
    load_workspace_config(workspace_root, env=dict(os.environ))
    state_root = workspace_root / ".observer_rock"
    repository = SqliteDocumentIntelligenceRepository(state_root / "documents.db")
    return QueryDocumentsCommandResult(
        workspace_root=workspace_root,
        profile_name=profile_name,
        contains_text=contains_text,
        monitor_id=monitor_id,
        latest_only=latest_only,
        matches=tuple(
            repository.query_documents(
                profile_name=profile_name,
                contains_text=contains_text,
                monitor_id=monitor_id,
                latest_only=latest_only,
            )
        ),
    )


def document_history_command(
    *,
    workspace_root: Path,
    document_id: str,
    profile_name: str,
) -> DocumentHistoryCommandResult:
    load_workspace_config(workspace_root, env=dict(os.environ))
    state_root = workspace_root / ".observer_rock"
    repository = SqliteDocumentIntelligenceRepository(state_root / "documents.db")
    entries = tuple(
        repository.get_document_history(
            document_id=document_id,
            profile_name=profile_name,
        )
    )
    comparison = None
    if len(entries) >= 2:
        current = entries[0]
        previous = entries[1]
        comparison = DocumentHistoryComparison(
            from_version=previous.version,
            to_version=current.version,
            source_changed=current.source_content != previous.source_content,
            analysis_changed=current.analysis_text != previous.analysis_text,
            source_diff=_build_diff(previous.source_content, current.source_content),
            analysis_diff=_build_diff(previous.analysis_text, current.analysis_text),
        )
    return DocumentHistoryCommandResult(
        workspace_root=workspace_root,
        document_id=document_id,
        profile_name=profile_name,
        entries=entries,
        comparison=comparison,
    )


def _build_run_id(monitor_id: str) -> str:
    return f"{monitor_id}-{uuid.uuid4().hex}"


def _build_source_fetch_context_provider(*, workspace_config, state_root: Path):
    repository = SqliteMonitorChangeTrackingRepository(state_root / "documents.db")

    def provider(monitor) -> SourceFetchContext:
        run_iteration, recheck_cursor, recent_documents = repository.get_state(monitor.id)
        next_run_iteration = run_iteration + 1
        tracking = monitor.change_tracking
        recheck_document_ids: tuple[str, ...] = ()
        recheck_enabled = False
        if (
            tracking is not None
            and tracking.recheck_recent_documents > 0
            and tracking.recheck_budget_per_run > 0
            and next_run_iteration % tracking.recheck_every_n_runs == 0
        ):
            capped_recent_documents = recent_documents[: tracking.recheck_recent_documents]
            recheck_document_ids, _ = _select_recheck_document_ids(
                recent_documents=capped_recent_documents,
                budget_per_run=tracking.recheck_budget_per_run,
                cursor=recheck_cursor,
            )
            recheck_enabled = bool(recheck_document_ids)
        return SourceFetchContext(
            run_iteration=next_run_iteration,
            recheck_enabled=recheck_enabled,
            recheck_document_ids=recheck_document_ids,
            recent_documents=tuple(
                RecentDocumentReference(source_id=source_id, identity_key=identity_key)
                for source_id, identity_key in recent_documents
            ),
        )

    return provider


def _require_monitor(*, workspace_config, monitor_id: str) -> None:
    if workspace_config.monitors is None:
        raise ValueError("Workspace config does not define any monitors")
    for monitor in workspace_config.monitors.monitors:
        if monitor.id == monitor_id:
            return
    raise KeyError(f"Unknown monitor_id: {monitor_id}")


def _update_monitor_change_tracking_state(
    *,
    workspace_config,
    state_root: Path,
    monitor_id: str,
    source_data,
) -> None:
    repository = SqliteMonitorChangeTrackingRepository(state_root / "documents.db")
    monitor = _get_monitor_config(workspace_config=workspace_config, monitor_id=monitor_id)
    run_iteration, recheck_cursor, recent_documents = repository.get_state(monitor_id)
    updated_recent_documents = _merge_recent_documents(
        existing=recent_documents,
        fetched_records=source_data.records,
        recent_limit=(
            monitor.change_tracking.recheck_recent_documents
            if monitor.change_tracking is not None
            else 0
        ),
    )
    next_cursor = recheck_cursor
    tracking = monitor.change_tracking
    if (
        tracking is not None
        and tracking.recheck_recent_documents > 0
        and tracking.recheck_budget_per_run > 0
        and (run_iteration + 1) % tracking.recheck_every_n_runs == 0
        and updated_recent_documents
    ):
        _, next_cursor = _select_recheck_document_ids(
            recent_documents=updated_recent_documents[: tracking.recheck_recent_documents],
            budget_per_run=tracking.recheck_budget_per_run,
            cursor=recheck_cursor,
        )
    repository.save_state(
        monitor_id=monitor_id,
        run_iteration=run_iteration + 1,
        recheck_cursor=next_cursor,
        recent_documents=updated_recent_documents,
    )


def _get_monitor_config(*, workspace_config, monitor_id: str):
    if workspace_config.monitors is None:
        raise ValueError("Workspace config does not define any monitors")
    for monitor in workspace_config.monitors.monitors:
        if monitor.id == monitor_id:
            return monitor
    raise KeyError(f"Unknown monitor_id: {monitor_id}")


def _resolve_identity_key_from_source_record(source_record: MonitorSourceRecord) -> str:
    if source_record.document_identity is not None:
        return source_record.document_identity
    if source_record.title is not None:
        return source_record.title
    return source_record.source_id


def _merge_recent_documents(
    *,
    existing: tuple[tuple[str, str], ...],
    fetched_records: tuple[MonitorSourceRecord, ...],
    recent_limit: int,
) -> tuple[tuple[str, str], ...]:
    if recent_limit <= 0:
        return ()
    merged: list[tuple[str, str]] = [
        (record.source_id, _resolve_identity_key_from_source_record(record))
        for record in fetched_records
    ]
    seen_identity_keys = {identity_key for _, identity_key in merged}
    for source_id, identity_key in existing:
        if identity_key in seen_identity_keys:
            continue
        merged.append((source_id, identity_key))
    return tuple(merged[:recent_limit])


def _select_recheck_document_ids(
    *,
    recent_documents: tuple[tuple[str, str], ...],
    budget_per_run: int,
    cursor: int,
) -> tuple[tuple[str, ...], int]:
    if not recent_documents or budget_per_run <= 0:
        return (), cursor
    total = len(recent_documents)
    selected: list[str] = []
    next_cursor = cursor
    for _ in range(min(budget_per_run, total)):
        selected.append(recent_documents[next_cursor % total][0])
        next_cursor = (next_cursor + 1) % total
    return tuple(selected), next_cursor


def _inspect_latest_artifact(
    *,
    document_repository: SqliteDocumentRepository,
    artifact_store: FilesystemArtifactStore,
    stage: str,
    document_id: str,
    artifact_name: str,
    content_type: str,
) -> InspectArtifactsStageResult:
    latest_document = document_repository.get_latest(document_id)
    if latest_document is None:
        return InspectArtifactsStageResult(
            stage=stage,
            status="MISSING",
            detail="no persisted artifact",
        )

    try:
        loaded_artifact = artifact_store.load(
            document_id=latest_document.document_id,
            version=latest_document.version,
            artifact_name=artifact_name,
            content_type=content_type,
        )
    except FileNotFoundError as exc:
        return InspectArtifactsStageResult(
            stage=stage,
            status="BROKEN",
            document_id=latest_document.document_id,
            version=latest_document.version,
            detail=str(exc),
        )

    return InspectArtifactsStageResult(
        stage=stage,
        status="AVAILABLE",
        document_id=loaded_artifact.artifact.document_id,
        version=loaded_artifact.artifact.version,
        artifact_path=loaded_artifact.artifact.path,
        content_type=loaded_artifact.artifact.content_type,
        size_bytes=loaded_artifact.artifact.size_bytes,
        payload=loaded_artifact.data.decode("utf-8"),
    )


def _load_source_data_payload(*, state_root: Path, monitor_id: str):
    from observer_rock.application.monitoring import MonitorSourceArtifactReader

    return MonitorSourceArtifactReader(
        document_repository=SqliteDocumentRepository(state_root / "documents.db"),
        artifact_store=FilesystemArtifactStore(state_root / "artifacts"),
    ).load_latest(monitor_id=monitor_id).source


def _load_analysis_payload(*, state_root: Path, monitor_id: str):
    from observer_rock.application.monitoring import MonitorAnalysisArtifactReader

    return MonitorAnalysisArtifactReader(
        document_repository=SqliteDocumentRepository(state_root / "documents.db"),
        artifact_store=FilesystemArtifactStore(state_root / "artifacts"),
    ).load_latest(monitor_id=monitor_id).analysis


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


def _build_diff(previous: str, current: str) -> tuple[str, ...]:
    return tuple(
        line
        for line in difflib.unified_diff(
            previous.splitlines(),
            current.splitlines(),
            fromfile="previous",
            tofile="current",
            lineterm="",
        )
        if not line.startswith(("---", "+++"))
    )
