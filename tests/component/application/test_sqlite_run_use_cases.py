from datetime import UTC, datetime
from pathlib import Path

from observer_rock.application.repositories import RunStatus
from observer_rock.application.use_cases import (
    fail_run,
    finish_run,
    get_run,
    list_runs,
    start_run,
)
from observer_rock.infrastructure.sqlite import SqliteRunRepository


def test_run_use_cases_work_against_sqlite_run_repository(tmp_path: Path) -> None:
    repository = SqliteRunRepository(tmp_path / "runs.db")
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    ended_at = datetime(2026, 3, 14, 12, 30, tzinfo=UTC)

    started = start_run(
        repository,
        run_id="run-001",
        monitor_id="monitor-123",
        at=started_at,
    )
    finished = finish_run(repository, run_id="run-001", at=ended_at)

    assert started.status is RunStatus.STARTED
    assert started.started_at == started_at
    assert started.ended_at is None
    assert finished.status is RunStatus.COMPLETED
    assert finished.started_at == started_at
    assert finished.ended_at == ended_at
    assert get_run(repository, run_id="run-001") == finished
    assert list_runs(repository) == [finished]


def test_fail_run_works_against_sqlite_run_repository(tmp_path: Path) -> None:
    repository = SqliteRunRepository(tmp_path / "runs.db")
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    ended_at = datetime(2026, 3, 14, 12, 30, tzinfo=UTC)

    started = start_run(
        repository,
        run_id="run-001",
        monitor_id="monitor-123",
        at=started_at,
    )
    failed = fail_run(repository, run_id="run-001", at=ended_at)

    assert started.status is RunStatus.STARTED
    assert started.started_at == started_at
    assert failed.status is RunStatus.FAILED
    assert failed.started_at == started_at
    assert failed.ended_at == ended_at
    assert get_run(repository, run_id="run-001") == failed
