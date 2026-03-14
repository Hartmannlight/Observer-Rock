from datetime import UTC, datetime
from pathlib import Path

import pytest

from observer_rock.application.repositories import RunRecord
from observer_rock.infrastructure.sqlite import SqliteRunRepository


def test_sqlite_run_repository_can_create_and_read_run_records(tmp_path: Path) -> None:
    repository = SqliteRunRepository(tmp_path / "runs.db")
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)

    created = repository.create(
        RunRecord(
            run_id="run-001",
            monitor_id="monitor-123",
            status="started",
            started_at=started_at,
        )
    )

    assert created == RunRecord(
        run_id="run-001",
        monitor_id="monitor-123",
        status="started",
        started_at=started_at,
    )
    assert repository.get("run-001") == created
    assert repository.get("missing-run") is None


def test_sqlite_run_repository_can_save_an_existing_run(tmp_path: Path) -> None:
    repository = SqliteRunRepository(tmp_path / "runs.db")
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    ended_at = datetime(2026, 3, 14, 12, 30, tzinfo=UTC)
    repository.create(
        RunRecord(
            run_id="run-001",
            monitor_id="monitor-123",
            status="started",
            started_at=started_at,
        )
    )

    updated = repository.save(
        RunRecord(
            run_id="run-001",
            monitor_id="monitor-123",
            status="completed",
            started_at=started_at,
            ended_at=ended_at,
        )
    )

    assert updated == RunRecord(
        run_id="run-001",
        monitor_id="monitor-123",
        status="completed",
        started_at=started_at,
        ended_at=ended_at,
    )
    assert repository.get("run-001") == updated


def test_sqlite_run_repository_rejects_unknown_run_ids_on_save(tmp_path: Path) -> None:
    repository = SqliteRunRepository(tmp_path / "runs.db")

    with pytest.raises(KeyError, match="run-404"):
        repository.save(
            RunRecord(
                run_id="run-404",
                monitor_id="monitor-123",
                status="completed",
                ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            )
        )


def test_sqlite_run_repository_rejects_duplicate_run_ids_on_create(tmp_path: Path) -> None:
    repository = SqliteRunRepository(tmp_path / "runs.db")
    repository.create(RunRecord(run_id="run-001", monitor_id="monitor-123", status="started"))

    with pytest.raises(KeyError, match="run-001"):
        repository.create(
            RunRecord(
                run_id="run-001",
                monitor_id="monitor-999",
                status="completed",
                ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            )
        )


def test_sqlite_run_repository_lists_runs_in_insertion_order(tmp_path: Path) -> None:
    repository = SqliteRunRepository(tmp_path / "runs.db")
    first_started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    second_started_at = datetime(2026, 3, 14, 13, 0, tzinfo=UTC)
    first = repository.create(
        RunRecord(
            run_id="run-001",
            monitor_id="monitor-123",
            status="started",
            started_at=first_started_at,
        )
    )
    second = repository.create(
        RunRecord(
            run_id="run-002",
            monitor_id="monitor-456",
            status="completed",
            started_at=second_started_at,
            ended_at=datetime(2026, 3, 14, 13, 30, tzinfo=UTC),
        )
    )

    assert repository.list_runs() == [first, second]


def test_sqlite_run_repository_persists_runs_across_repository_instances(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runs.db"
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    SqliteRunRepository(database_path).create(
        RunRecord(
            run_id="run-001",
            monitor_id="monitor-123",
            status="started",
            started_at=started_at,
        )
    )

    persisted = SqliteRunRepository(database_path).get("run-001")

    assert persisted == RunRecord(
        run_id="run-001",
        monitor_id="monitor-123",
        status="started",
        started_at=started_at,
    )
