from datetime import UTC, datetime
from pathlib import Path

from observer_rock.application.repositories import RunStatus
from observer_rock.application.services import RunService
from observer_rock.infrastructure.sqlite import SqliteRunRepository
from tests._helpers import _sequence_now_provider


def test_run_service_works_against_sqlite_run_repository(tmp_path: Path) -> None:
    service = RunService(SqliteRunRepository(tmp_path / "runs.db"))
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    ended_at = datetime(2026, 3, 14, 12, 30, tzinfo=UTC)

    started = service.start_run(
        run_id="run-001",
        monitor_id="monitor-123",
        at=started_at,
    )
    finished = service.finish_run(run_id="run-001", at=ended_at)

    assert started.started_at == started_at
    assert finished.started_at == started_at
    assert finished.ended_at == ended_at
    assert service.get_run(run_id="run-001") == finished
    assert service.list_runs() == [finished]


def test_run_service_execute_run_persists_failed_status_in_sqlite(tmp_path: Path) -> None:
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    ended_at = datetime(2026, 3, 14, 12, 30, tzinfo=UTC)
    service = RunService(
        SqliteRunRepository(tmp_path / "runs.db"),
        now_provider=_sequence_now_provider(started_at, ended_at),
    )

    execution = service.execute_run(
        run_id="run-001",
        monitor_id="monitor-123",
        operation=_raise_runtime_error,
    )

    assert execution.outcome is RunStatus.FAILED
    assert isinstance(execution.error, RuntimeError)
    stored = service.get_run(run_id="run-001")
    assert stored == execution.run
    assert stored is not None
    assert stored.status is RunStatus.FAILED
    assert stored.started_at == started_at
    assert stored.ended_at == ended_at


def _raise_runtime_error() -> str:
    raise RuntimeError("boom")

