from datetime import UTC, datetime

from observer_rock.application.repositories import RunRecord
from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.application.use_cases import get_latest_run_for_monitor


def test_get_latest_run_for_monitor_returns_newest_matching_run_in_insertion_order() -> None:
    repository = InMemoryRunRepository()
    first = repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )
    repository.create(
        RunRecord(run_id="run-002", monitor_id="monitor-456", status="started")
    )
    latest = repository.create(
        RunRecord(
            run_id="run-003",
            monitor_id="monitor-123",
            status="completed",
            ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
        )
    )

    assert first.run_id == "run-001"
    assert get_latest_run_for_monitor(repository, monitor_id="monitor-123") == latest


def test_get_latest_run_for_monitor_returns_none_when_monitor_has_no_runs() -> None:
    repository = InMemoryRunRepository()
    repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )

    assert get_latest_run_for_monitor(repository, monitor_id="monitor-999") is None


def test_get_latest_run_for_monitor_filters_by_status_when_requested() -> None:
    repository = InMemoryRunRepository()
    repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )
    expected = repository.create(
        RunRecord(
            run_id="run-002",
            monitor_id="monitor-123",
            status="completed",
            ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
        )
    )
    repository.create(
        RunRecord(run_id="run-003", monitor_id="monitor-123", status="started")
    )

    assert (
        get_latest_run_for_monitor(
            repository, monitor_id="monitor-123", status="completed"
        )
        == expected
    )
