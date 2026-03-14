from datetime import UTC, datetime

from observer_rock.application.repositories import RunRecord, RunRepository, RunStatus


def start_run(
    repository: RunRepository,
    *,
    run_id: str,
    monitor_id: str,
    at: datetime | None = None,
) -> RunRecord:
    return repository.create(
        RunRecord(
            run_id=run_id,
            monitor_id=monitor_id,
            status=RunStatus.STARTED,
            started_at=_resolve_timestamp(at),
        )
    )


def get_run(
    repository: RunRepository, *, run_id: str, monitor_id: str | None = None
) -> RunRecord | None:
    run = repository.get(run_id)
    if run is None:
        return None
    if monitor_id is not None and run.monitor_id != monitor_id:
        return None
    return run


def has_run(
    repository: RunRepository, *, run_id: str, monitor_id: str | None = None
) -> bool:
    return get_run(repository, run_id=run_id, monitor_id=monitor_id) is not None


def get_latest_run_for_monitor(
    repository: RunRepository, *, monitor_id: str, status: str | None = None
) -> RunRecord | None:
    latest: RunRecord | None = None
    for run in repository.list_runs():
        if run.monitor_id == monitor_id and (status is None or run.status == status):
            latest = run
    return latest


def list_runs(
    repository: RunRepository,
    *,
    status: str | None = None,
    monitor_id: str | None = None,
) -> list[RunRecord]:
    runs = repository.list_runs()
    if status is not None:
        runs = [run for run in runs if run.status == status]
    if monitor_id is not None:
        runs = [run for run in runs if run.monitor_id == monitor_id]
    return runs


def count_runs(
    repository: RunRepository,
    *,
    status: str | None = None,
    monitor_id: str | None = None,
) -> int:
    return len(list_runs(repository, status=status, monitor_id=monitor_id))


def finish_run(
    repository: RunRepository,
    *,
    run_id: str,
    at: datetime | None = None,
) -> RunRecord:
    existing = repository.get(run_id)
    if existing is None:
        msg = f"Unknown run_id: {run_id}"
        raise KeyError(msg)
    if not existing.status.can_transition_to(RunStatus.COMPLETED):
        msg = (
            f"Cannot transition run '{run_id}' from "
            f"{existing.status!s} to {RunStatus.COMPLETED!s}"
        )
        raise ValueError(msg)

    return repository.save(
        RunRecord(
            run_id=existing.run_id,
            monitor_id=existing.monitor_id,
            status=RunStatus.COMPLETED,
            started_at=existing.started_at,
            ended_at=_resolve_timestamp(at),
        )
    )


def fail_run(
    repository: RunRepository,
    *,
    run_id: str,
    at: datetime | None = None,
) -> RunRecord:
    existing = repository.get(run_id)
    if existing is None:
        msg = f"Unknown run_id: {run_id}"
        raise KeyError(msg)
    if not existing.status.can_transition_to(RunStatus.FAILED):
        msg = (
            f"Cannot transition run '{run_id}' from "
            f"{existing.status!s} to {RunStatus.FAILED!s}"
        )
        raise ValueError(msg)

    return repository.save(
        RunRecord(
            run_id=existing.run_id,
            monitor_id=existing.monitor_id,
            status=RunStatus.FAILED,
            started_at=existing.started_at,
            ended_at=_resolve_timestamp(at),
        )
    )


def _resolve_timestamp(at: datetime | None) -> datetime:
    return at if at is not None else datetime.now(UTC)
