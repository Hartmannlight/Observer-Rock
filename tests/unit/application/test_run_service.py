from datetime import UTC, datetime

from observer_rock.application.repositories import RunStatus
from observer_rock.application.services import RunService
from observer_rock.application.testing import InMemoryRunRepository
from tests._helpers import _sequence_now_provider


def test_run_service_wraps_run_lifecycle_and_read_operations() -> None:
    repository = InMemoryRunRepository()
    service = RunService(repository)
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    ended_at = datetime(2026, 3, 14, 12, 30, tzinfo=UTC)

    started = service.start_run(
        run_id="run-001",
        monitor_id="monitor-123",
        at=started_at,
    )
    finished = service.finish_run(run_id="run-001", at=ended_at)

    assert started.started_at == started_at
    assert finished.ended_at == ended_at
    assert service.get_run(run_id="run-001") == finished
    assert service.has_run(run_id="run-001") is True
    assert service.count_runs() == 1
    assert service.list_runs() == [finished]
    assert service.get_latest_run_for_monitor(monitor_id="monitor-123") == finished


def test_run_service_execute_run_marks_successful_operations_completed() -> None:
    repository = InMemoryRunRepository()
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    ended_at = datetime(2026, 3, 14, 12, 30, tzinfo=UTC)
    service = RunService(repository, now_provider=_sequence_now_provider(started_at, ended_at))

    execution = service.execute_run(
        run_id="run-001",
        monitor_id="monitor-123",
        operation=lambda: "ok",
    )

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value == "ok"
    assert execution.error is None
    assert execution.run.status is RunStatus.COMPLETED
    assert execution.run.started_at == started_at
    assert execution.run.ended_at == ended_at
    assert service.get_run(run_id="run-001") == execution.run


def test_run_service_execute_run_marks_failed_operations_failed_without_reraising() -> None:
    repository = InMemoryRunRepository()
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    ended_at = datetime(2026, 3, 14, 12, 30, tzinfo=UTC)
    service = RunService(repository, now_provider=_sequence_now_provider(started_at, ended_at))

    execution = service.execute_run(
        run_id="run-001",
        monitor_id="monitor-123",
        operation=_raise_runtime_error,
    )

    assert execution.outcome is RunStatus.FAILED
    assert execution.value is None
    assert isinstance(execution.error, RuntimeError)
    assert str(execution.error) == "boom"
    assert execution.run.status is RunStatus.FAILED
    assert execution.run.started_at == started_at
    assert execution.run.ended_at == ended_at


def _raise_runtime_error() -> str:
    raise RuntimeError("boom")
