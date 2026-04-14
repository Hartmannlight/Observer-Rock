import argparse
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from observer_rock.application.monitoring import MonitorExecutionStageError, PersistedMonitorArtifact
from observer_rock.cli.runtime import (
    ListMonitorsCommandEntry,
    ValidateWorkspaceAnalysisProfileEntry,
    ValidateWorkspaceMonitorEntry,
    ValidateWorkspaceServiceEntry,
    list_monitors_command,
    run_monitor_command,
    run_scheduler_command,
    validate_workspace_command,
)
from observer_rock.config.models import ConfigValidationError
from observer_rock.scaffold import initialize_workspace


@dataclass(frozen=True, slots=True)
class _RunFailureSummary:
    stage: str
    attempts: int = 1
    target: str | None = None
    source_artifact: PersistedMonitorArtifact | None = None
    analysis_artifact: PersistedMonitorArtifact | None = None


def main(
    argv: Sequence[str] | None = None,
    *,
    source_plugins: Mapping[str, object] | None = None,
    analysis_plugins: Mapping[str, object] | None = None,
    renderer_plugins: Mapping[str, object] | None = None,
    notifier_plugins: Mapping[str, object] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="observer-rock")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_monitor_parser = subparsers.add_parser("run-monitor")
    run_monitor_parser.add_argument("monitor_id")
    run_monitor_parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
    )
    run_scheduler_parser = subparsers.add_parser("run-scheduler")
    run_scheduler_parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
    )
    run_scheduler_parser.add_argument(
        "--tick",
        type=datetime.fromisoformat,
        default=None,
        help="Optional ISO timestamp to evaluate schedules against.",
    )
    list_monitors_parser = subparsers.add_parser("list-monitors")
    list_monitors_parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
    )
    list_monitors_parser.add_argument(
        "--tick",
        type=datetime.fromisoformat,
        default=None,
        help="Optional ISO timestamp to evaluate schedules against.",
    )
    validate_workspace_parser = subparsers.add_parser("validate-workspace")
    validate_workspace_parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
    )
    validate_workspace_parser.add_argument(
        "--tick",
        type=datetime.fromisoformat,
        default=None,
        help="Optional ISO timestamp to evaluate schedules against.",
    )
    init_workspace_parser = subparsers.add_parser("init-workspace")
    init_workspace_parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        if args.command == "run-monitor":
            result = run_monitor_command(
                workspace_root=args.workspace,
                monitor_id=args.monitor_id,
                source_plugins=source_plugins,
                analysis_plugins=analysis_plugins,
                renderer_plugins=renderer_plugins,
                notifier_plugins=notifier_plugins,
            )
        elif args.command == "run-scheduler":
            scheduler_result = run_scheduler_command(
                workspace_root=args.workspace,
                source_plugins=source_plugins,
                analysis_plugins=analysis_plugins,
                renderer_plugins=renderer_plugins,
                notifier_plugins=notifier_plugins,
                tick=args.tick,
            )
            if scheduler_result.configured_monitor_count == 0:
                raise ValueError("Workspace config does not define any monitors")
            print(
                "scheduler status=STARTED "
                f"workspace={scheduler_result.workspace_root} "
                f"tick={scheduler_result.tick.isoformat()} "
                f"services={scheduler_result.service_count} "
                f"analysis_profiles={scheduler_result.analysis_profile_count} "
                f"configured={scheduler_result.configured_monitor_count} "
                f"due={scheduler_result.due_monitor_count} "
                f"skipped={scheduler_result.skipped_monitor_count}"
            )
            if not scheduler_result.monitor_results:
                print(
                    "No monitors due at "
                    f"{scheduler_result.tick.isoformat()} "
                    f"({scheduler_result.configured_monitor_count} configured)"
                )
                print(
                    "Scheduler summary "
                    f"tick={scheduler_result.tick.isoformat()} "
                    f"configured={scheduler_result.configured_monitor_count} "
                    f"due={scheduler_result.due_monitor_count} "
                    f"skipped={scheduler_result.skipped_monitor_count} "
                    "completed=0 failed=0"
                )
                return 0
            for monitor_result in scheduler_result.monitor_results:
                for line in _format_run_monitor_observability_lines(monitor_result):
                    print(line)
            failed_results = tuple(
                monitor_result
                for monitor_result in scheduler_result.monitor_results
                if monitor_result.execution.error is not None
            )
            print(
                "Scheduler summary "
                f"tick={scheduler_result.tick.isoformat()} "
                f"configured={scheduler_result.configured_monitor_count} "
                f"due={scheduler_result.due_monitor_count} "
                f"skipped={scheduler_result.skipped_monitor_count} "
                f"completed={len(scheduler_result.monitor_results) - len(failed_results)} "
                f"failed={len(failed_results)}"
            )
            if failed_results:
                for monitor_result in failed_results:
                    execution = monitor_result.execution
                    failure_summary = _summarize_failure(monitor_result)
                    print(
                        f"{execution.monitor.id} FAILED "
                        f"stage={failure_summary.stage} "
                        f"{_format_failure_detail_suffix(failure_summary)}: {execution.error}",
                        file=sys.stderr,
                    )
                return 1
            return 0
        elif args.command == "list-monitors":
            list_result = list_monitors_command(
                workspace_root=args.workspace,
                tick=args.tick,
            )
            if list_result.configured_monitor_count == 0:
                raise ValueError("Workspace config does not define any monitors")
            print(
                "Configured monitors "
                f"({list_result.configured_monitor_count}) "
                f"at {list_result.tick.isoformat()}"
            )
            for monitor in list_result.monitors:
                print(_format_list_monitors_line(monitor))
            return 0
        elif args.command == "validate-workspace":
            validation_result = validate_workspace_command(
                workspace_root=args.workspace,
                tick=args.tick,
            )
            print(
                "Workspace VALID "
                f"root={validation_result.workspace_root} "
                f"tick={validation_result.tick.isoformat()}"
            )
            print(
                "Summary "
                f"plugin_imports={len(validation_result.plugin_import_paths)} "
                f"services={len(validation_result.services)} "
                f"analysis_profiles={len(validation_result.analysis_profiles)} "
                f"monitors={len(validation_result.monitors)}"
            )
            for plugin_import_path in validation_result.plugin_import_paths:
                print(f"plugin-import {plugin_import_path}")
            for service in validation_result.services:
                print(_format_validate_workspace_service_line(service))
            for analysis_profile in validation_result.analysis_profiles:
                print(_format_validate_workspace_analysis_profile_line(analysis_profile))
            for monitor in validation_result.monitors:
                print(_format_validate_workspace_monitor_line(monitor))
            return 0
        elif args.command == "init-workspace":
            initialized = initialize_workspace(workspace_root=args.workspace)
            print(
                "Workspace initialized "
                f"root={initialized.workspace_root} "
                f"monitor_id={initialized.monitor_id}"
            )
            print("Next steps:")
            print(
                f"  python -m observer_rock validate-workspace --workspace {initialized.workspace_root}"
            )
            print(
                f"  python -m observer_rock list-monitors --workspace {initialized.workspace_root}"
            )
            print(
                "  python -m observer_rock run-monitor "
                f"{initialized.monitor_id} --workspace {initialized.workspace_root}"
            )
            return 0
        else:
            return 0
    except KeyError as exc:
        if exc.args and str(exc.args[0]) == f"Unknown monitor_id: {args.monitor_id}":
            print(f"Error: unknown monitor '{args.monitor_id}'", file=sys.stderr)
            return 2
        raise
    except ValueError as exc:
        if _is_operator_configuration_error(exc):
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        raise
    execution = result.execution
    for line in _format_run_monitor_observability_lines(result):
        print(line)
    if execution.error is not None:
        failure_summary = _summarize_failure(result)
        print(
            f"{execution.monitor.id} FAILED "
            f"stage={failure_summary.stage} "
            f"{_format_failure_detail_suffix(failure_summary)}: {execution.error}",
            file=sys.stderr,
        )
        return 1

    return 0


def _is_operator_configuration_error(exc: ValueError) -> bool:
    if isinstance(exc, ConfigValidationError):
        return True

    message = str(exc)
    return message.startswith(
        (
            "Could not import plugin module '",
            "Plugin module '",
            "Workspace config ",
            "Workspace path ",
            "Analysis profile '",
            "Monitor '",
        )
    )


def _format_run_monitor_success_line(result) -> str:
    execution = result.execution
    persisted = execution.value
    notifications_summary = (
        f"{persisted.notifications.document.document_id}@v{persisted.notifications.document.version}"
        if persisted.notifications is not None
        else "none"
    )
    return (
        f"{execution.monitor.id} {execution.outcome.name} "
        f"source={persisted.source.document.document_id}@v{persisted.source.document.version} "
        f"analysis={persisted.analysis.document.document_id}@v{persisted.analysis.document.version} "
        f"notifications={notifications_summary} "
        f"artifacts={result.state_root / 'artifacts'}"
    )


def _format_run_monitor_observability_lines(result) -> list[str]:
    execution = result.execution
    lines = [
        (
            "workspace status=LOADED "
            f"root={result.workspace_root} "
            f"services={result.service_count} "
            f"analysis_profiles={result.analysis_profile_count} "
            f"monitors={result.configured_monitor_count}"
        ),
        (
            "run status=STARTED "
            f"monitor={execution.monitor.id} "
            f"run_id={execution.run.run_id} "
            f"started_at={execution.run.started_at.isoformat() if execution.run.started_at else 'unknown'}"
        ),
    ]
    if execution.error is None:
        persisted = execution.value
        if any(attempts > 1 for _, attempts in persisted.analysis_attempts):
            lines.append(_format_attempts_line("analysis", persisted.analysis_attempts))
        lines.append(_format_stage_completed_line("source", persisted.source))
        lines.append(_format_stage_completed_line("analysis", persisted.analysis))
        if any(attempts > 1 for _, attempts in persisted.notification_attempts):
            lines.append(_format_attempts_line("notifications", persisted.notification_attempts))
        if persisted.notifications is None:
            lines.append("notifications status=SKIPPED reason=no_outputs")
        else:
            lines.append(_format_stage_completed_line("notifications", persisted.notifications))
        lines.append(
            "run status=COMPLETED "
            f"monitor={execution.monitor.id} "
            f"run_id={execution.run.run_id} "
            f"ended_at={execution.run.ended_at.isoformat() if execution.run.ended_at else 'unknown'} "
            f"artifacts={result.state_root / 'artifacts'}"
        )
        lines.append(_format_run_monitor_success_line(result))
        return lines

    failure_summary = _summarize_failure(result)
    if failure_summary.source_artifact is not None:
        lines.append(_format_stage_completed_line("source", failure_summary.source_artifact))
    if failure_summary.analysis_artifact is not None:
        lines.append(_format_stage_completed_line("analysis", failure_summary.analysis_artifact))
    lines.append(
        f"{failure_summary.stage} status=FAILED "
        f"{_format_failure_detail_suffix(failure_summary)} "
        f"error={execution.error}"
    )
    lines.append(
        "run status=FAILED "
        f"monitor={execution.monitor.id} "
        f"run_id={execution.run.run_id} "
        f"ended_at={execution.run.ended_at.isoformat() if execution.run.ended_at else 'unknown'} "
        f"artifacts={result.state_root / 'artifacts'}"
    )
    return lines


def _format_stage_completed_line(stage: str, artifact: PersistedMonitorArtifact) -> str:
    return (
        f"{stage} status=COMPLETED "
        f"document={artifact.document.document_id}@v{artifact.document.version} "
        f"artifact={artifact.artifact.path}"
    )


def _summarize_failure(result) -> _RunFailureSummary:
    execution = result.execution
    error = execution.error
    if isinstance(error, MonitorExecutionStageError):
        return _RunFailureSummary(
            stage=error.stage,
            attempts=error.attempts,
            target=error.target,
            source_artifact=error.source_artifact,
            analysis_artifact=error.analysis_artifact,
        )
    return _RunFailureSummary(stage="runtime")


def _format_failure_detail_suffix(summary: _RunFailureSummary) -> str:
    parts: list[str] = []
    if summary.target is not None:
        parts.append(f"target={summary.target}")
    parts.append(f"attempts={summary.attempts}")
    return " ".join(parts)


def _format_attempts_line(stage: str, attempts: tuple[tuple[str, int], ...]) -> str:
    rendered_attempts = ",".join(f"{target}={count}" for target, count in attempts)
    return f"{stage} attempts {rendered_attempts}"


def _format_list_monitors_line(monitor: ListMonitorsCommandEntry) -> str:
    analyses = ",".join(monitor.analysis_profiles) if monitor.analysis_profiles else "none"
    outputs = (
        ",".join(
            f"{profile}->{renderer}->{service}"
            for profile, renderer, service in monitor.outputs
        )
        if monitor.outputs
        else "none"
    )
    due_state = "DUE" if monitor.due else "NOT_DUE"
    return (
        f"{monitor.monitor_id} {due_state} "
        f"schedule='{monitor.schedule}' "
        f"source={monitor.source_plugin} "
        f"analyses={analyses} "
        f"outputs={outputs}"
    )


def _format_validate_workspace_service_line(service: ValidateWorkspaceServiceEntry) -> str:
    token_source = (
        f"env:{service.token_env}"
        if service.token_env is not None
        else ("inline" if service.has_token else "none")
    )
    path_summary = service.path if service.path is not None else "none"
    return (
        f"service {service.service_name} "
        f"plugin={service.plugin} "
        f"token_source={token_source} "
        f"path={path_summary}"
    )


def _format_validate_workspace_analysis_profile_line(
    analysis_profile: ValidateWorkspaceAnalysisProfileEntry,
) -> str:
    return (
        f"analysis-profile {analysis_profile.profile_name} "
        f"plugin={analysis_profile.plugin} "
        f"model_service={analysis_profile.model_service}"
    )


def _format_validate_workspace_monitor_line(monitor: ValidateWorkspaceMonitorEntry) -> str:
    analyses = ",".join(monitor.analysis_profiles) if monitor.analysis_profiles else "none"
    outputs = (
        ",".join(
            f"{profile}->{renderer}->{service}"
            for profile, renderer, service in monitor.outputs
        )
        if monitor.outputs
        else "none"
    )
    source_path = monitor.source_path if monitor.source_path is not None else "none"
    due_state = "DUE" if monitor.due else "NOT_DUE"
    return (
        f"monitor {monitor.monitor_id} "
        f"due={due_state} "
        f"schedule='{monitor.schedule}' "
        f"source={monitor.source_plugin} "
        f"source_path={source_path} "
        f"analyses={analyses} "
        f"outputs={outputs}"
    )
