from datetime import UTC, datetime

from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.application.use_cases import start_run


def test_start_run_creates_and_returns_a_run_record_with_started_at_timestamp() -> None:
    repository = InMemoryRunRepository()
    started_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)

    started = start_run(
        repository,
        run_id="run-001",
        monitor_id="monitor-123",
        at=started_at,
    )

    assert started.monitor_id == "monitor-123"
    assert started.run_id == "run-001"
    assert started.status == "started"
    assert started.started_at == started_at
    assert started.ended_at is None
    assert repository.get("run-001") == started
