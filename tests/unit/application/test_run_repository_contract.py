from datetime import UTC, datetime

import pytest

from observer_rock.application.repositories import RunRecord
from observer_rock.application.testing import InMemoryRunRepository


def test_in_memory_run_repository_can_create_and_read_run_records() -> None:
    repository = InMemoryRunRepository()
    created = repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )

    assert created == RunRecord(
        run_id="run-001", monitor_id="monitor-123", status="started"
    )
    assert repository.get("run-001") == created
    assert repository.get("missing-run") is None


def test_in_memory_run_repository_lists_runs_in_insertion_order() -> None:
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

    assert repository.list_runs() == [first, second]


def test_in_memory_run_repository_rejects_duplicate_run_ids_on_create() -> None:
    repository = InMemoryRunRepository()
    original = repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )
    duplicate = RunRecord(
        run_id="run-001",
        monitor_id="monitor-999",
        status="completed",
        ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
    )

    with pytest.raises(KeyError, match="run-001"):
        repository.create(duplicate)

    assert repository.get("run-001") == original


def test_in_memory_run_repository_rejects_unknown_run_ids_on_save() -> None:
    repository = InMemoryRunRepository()

    with pytest.raises(KeyError, match="run-404"):
        repository.save(
            RunRecord(
                run_id="run-404",
                monitor_id="monitor-123",
                status="completed",
                ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            )
        )
