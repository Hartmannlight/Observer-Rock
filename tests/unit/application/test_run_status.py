from datetime import UTC, datetime

import pytest

from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.application.use_cases import fail_run, finish_run, start_run


def test_start_finish_and_fail_run_use_typed_run_status_values() -> None:
    from observer_rock.application.repositories import RunStatus

    repository = InMemoryRunRepository()
    failing_repository = InMemoryRunRepository()

    started = start_run(repository, run_id="run-001", monitor_id="monitor-123")
    finished = finish_run(repository, run_id="run-001")
    start_run(failing_repository, run_id="run-002", monitor_id="monitor-456")
    failed = fail_run(failing_repository, run_id="run-002")

    assert started.status is RunStatus.STARTED
    assert finished.status is RunStatus.COMPLETED
    assert failed.status is RunStatus.FAILED


def test_run_status_marks_completed_and_failed_as_terminal() -> None:
    from observer_rock.application.repositories import RunStatus

    assert RunStatus.STARTED.is_terminal is False
    assert RunStatus.COMPLETED.is_terminal is True
    assert RunStatus.FAILED.is_terminal is True


def test_run_status_allows_transitions_from_started_to_terminal_states_only() -> None:
    from observer_rock.application.repositories import RunStatus

    assert RunStatus.STARTED.can_transition_to(RunStatus.COMPLETED) is True
    assert RunStatus.STARTED.can_transition_to(RunStatus.FAILED) is True
    assert RunStatus.COMPLETED.can_transition_to(RunStatus.COMPLETED) is False
    assert RunStatus.COMPLETED.can_transition_to(RunStatus.FAILED) is False
    assert RunStatus.FAILED.can_transition_to(RunStatus.COMPLETED) is False


def test_run_record_rejects_unknown_status_values() -> None:
    from observer_rock.application.repositories import RunRecord

    with pytest.raises(ValueError):
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="unknown")


def test_started_run_record_rejects_ended_at_timestamp() -> None:
    from observer_rock.application.repositories import RunRecord

    with pytest.raises(ValueError, match="started run cannot define ended_at"):
        RunRecord(
            run_id="run-001",
            monitor_id="monitor-123",
            status="started",
            ended_at=datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
        )


def test_terminal_run_record_requires_ended_at_timestamp() -> None:
    from observer_rock.application.repositories import RunRecord

    with pytest.raises(ValueError, match="terminal run must define ended_at"):
        RunRecord(
            run_id="run-001",
            monitor_id="monitor-123",
            status="completed",
            started_at=datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
        )
