from datetime import UTC, datetime

import pytest

from observer_rock.application.repositories import RunRecord
from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.application.use_cases import fail_run


def test_fail_run_updates_status_persists_the_failed_run_and_sets_ended_at() -> None:
    repository = InMemoryRunRepository()
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

    failed = fail_run(repository, run_id="run-001", at=ended_at)

    assert failed == RunRecord(
        run_id="run-001",
        monitor_id="monitor-123",
        status="failed",
        started_at=started_at,
        ended_at=ended_at,
    )
    assert repository.get("run-001") == failed


def test_fail_run_raises_key_error_for_unknown_run_and_includes_run_id() -> None:
    repository = InMemoryRunRepository()
    missing_run_id = "run-missing-404"

    with pytest.raises(KeyError) as exc_info:
        fail_run(repository, run_id=missing_run_id)

    assert exc_info.value.args[0] == f"Unknown run_id: {missing_run_id}"


def test_fail_run_rejects_transition_from_terminal_status() -> None:
    repository = InMemoryRunRepository()
    repository.create(
        RunRecord(
            run_id="run-001",
            monitor_id="monitor-123",
            status="completed",
            ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
        )
    )

    with pytest.raises(ValueError, match="Cannot transition run 'run-001'"):
        fail_run(repository, run_id="run-001")
