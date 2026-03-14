from observer_rock.application.repositories import RunRecord
from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.application.use_cases import has_run


def test_has_run_returns_true_for_existing_run_and_false_for_unknown_ids() -> None:
    repository = InMemoryRunRepository()
    repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )

    assert has_run(repository, run_id="run-001") is True
    assert has_run(repository, run_id="missing-run") is False


def test_has_run_preserves_monitor_id_filtering() -> None:
    repository = InMemoryRunRepository()
    repository.create(
        RunRecord(run_id="run-001", monitor_id="monitor-123", status="started")
    )

    assert has_run(repository, run_id="run-001", monitor_id="monitor-123") is True
    assert has_run(repository, run_id="run-001", monitor_id="monitor-999") is False
