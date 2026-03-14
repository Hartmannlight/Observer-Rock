from datetime import UTC, datetime

import pytest

from observer_rock.application.repositories import RunRecord
from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.application.use_cases import finish_run


def test_finish_run_updates_status_persists_the_completed_run_and_sets_ended_at() -> None:
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

    finished = finish_run(repository, run_id="run-001", at=ended_at)

    assert finished == RunRecord(
        run_id="run-001",
        monitor_id="monitor-123",
        status="completed",
        started_at=started_at,
        ended_at=ended_at,
    )
    assert repository.get("run-001") == finished


def test_finish_run_raises_key_error_for_unknown_run_and_includes_run_id() -> None:
    repository = InMemoryRunRepository()
    missing_run_id = "run-missing-404"

    with pytest.raises(KeyError) as exc_info:
        finish_run(repository, run_id=missing_run_id)

    assert exc_info.value.args[0] == f"Unknown run_id: {missing_run_id}"
