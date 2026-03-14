from datetime import UTC, datetime

from observer_rock.application.repositories import RunRecord
from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.application.use_cases import list_runs


def test_list_runs_returns_all_runs_in_insertion_order() -> None:
    repository = InMemoryRunRepository()
    first = repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )
    second = repository.create(
        RunRecord(
            run_id="run-002",
            monitor_id="monitor-456",
            status="completed",
            ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
        )
    )

    assert list_runs(repository) == [first, second]


def test_list_runs_filters_by_status_preserving_insertion_order() -> None:
    repository = InMemoryRunRepository()
    first = repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )
    repository.create(
        RunRecord(
            run_id="run-002",
            monitor_id="monitor-456",
            status="completed",
            ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
        )
    )
    third = repository.create(
        RunRecord(run_id="run-003", monitor_id="monitor-789", status="started")
    )

    assert list_runs(repository, status="started") == [first, third]


def test_list_runs_filters_by_monitor_id_preserving_insertion_order() -> None:
    repository = InMemoryRunRepository()
    first = repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )
    repository.create(
        RunRecord(run_id="run-002", monitor_id="monitor-456", status="started")
    )
    third = repository.create(
        RunRecord(
            run_id="run-003",
            monitor_id="monitor-123",
            status="completed",
            ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
        )
    )

    assert list_runs(repository, monitor_id="monitor-123") == [first, third]


def test_list_runs_filters_by_status_and_monitor_id_in_insertion_order() -> None:
    repository = InMemoryRunRepository()
    first = repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )
    repository.create(
        RunRecord(
            run_id="run-002",
            monitor_id="monitor-123",
            status="completed",
            ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
        )
    )
    repository.create(
        RunRecord(run_id="run-003", monitor_id="monitor-456", status="started")
    )
    fourth = repository.create(
        RunRecord(run_id="run-004", monitor_id="monitor-123", status="started")
    )

    assert list_runs(repository, status="started", monitor_id="monitor-123") == [
        first,
        fourth,
    ]
