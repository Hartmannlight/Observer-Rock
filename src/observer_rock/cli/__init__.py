import argparse
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from observer_rock.cli.runtime import run_monitor_command, run_scheduler_command
from observer_rock.config.models import ConfigValidationError


def main(
    argv: Sequence[str] | None = None,
    *,
    source_plugins: Mapping[str, object] | None = None,
    analysis_plugins: Mapping[str, object] | None = None,
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
            )
        elif args.command == "run-scheduler":
            scheduler_result = run_scheduler_command(
                workspace_root=args.workspace,
                source_plugins=source_plugins,
                analysis_plugins=analysis_plugins,
                tick=args.tick,
            )
            if scheduler_result.configured_monitor_count == 0:
                raise ValueError("Workspace config does not define any monitors")
            for monitor_result in scheduler_result.monitor_results:
                execution = monitor_result.execution
                if execution.error is not None:
                    print(
                        f"{execution.monitor.id} FAILED: {execution.error}",
                        file=sys.stderr,
                    )
                    return 1
            for monitor_result in scheduler_result.monitor_results:
                execution = monitor_result.execution
                print(
                    f"{execution.monitor.id} {execution.outcome.name} "
                    f"{monitor_result.state_root / 'artifacts'}"
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
    if execution.error is not None:
        print(f"{execution.monitor.id} FAILED: {execution.error}", file=sys.stderr)
        return 1

    print(
        f"{execution.monitor.id} {execution.outcome.name} "
        f"{result.state_root / 'artifacts'}"
    )
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
            "Analysis profile '",
            "Monitor '",
        )
    )
