from observer_rock.application.repositories import RunRecord
from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.application.use_cases import get_run


def test_get_run_returns_existing_run_and_none_for_unknown_ids() -> None:
    repository = InMemoryRunRepository()
    stored = repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )

    assert get_run(repository, run_id="run-001") == stored
    assert get_run(repository, run_id="missing-run") is None


def test_get_run_returns_none_when_monitor_id_does_not_match() -> None:
    repository = InMemoryRunRepository()
    repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )

    assert get_run(repository, run_id="run-001", monitor_id="monitor-999") is None
