from datetime import UTC, datetime

from observer_rock.application.repositories import RunRecord
from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.application.use_cases import count_runs


def test_count_runs_supports_status_and_monitor_filters() -> None:
    repository = InMemoryRunRepository()
    repository.create(
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

    assert count_runs(repository) == 3
    assert count_runs(repository, status="started") == 2
    assert count_runs(repository, monitor_id="monitor-123") == 2
    assert count_runs(repository, status="started", monitor_id="monitor-123") == 1
