from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, TypeVar

from observer_rock.application.repositories import RunRecord, RunRepository, RunStatus
from observer_rock.application.use_cases import (
    count_runs,
    fail_run,
    finish_run,
    get_latest_run_for_monitor,
    get_run,
    has_run,
    list_runs,
    start_run,
)

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RunExecutionResult[T]:
    run: RunRecord
    outcome: RunStatus
    value: T | None = None
    error: Exception | None = None


@dataclass(frozen=True, slots=True)
class RunService:
    repository: RunRepository
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC)

    def start_run(
        self,
        *,
        run_id: str,
        monitor_id: str,
        at: datetime | None = None,
    ) -> RunRecord:
        return start_run(self.repository, run_id=run_id, monitor_id=monitor_id, at=at)

    def finish_run(self, *, run_id: str, at: datetime | None = None) -> RunRecord:
        return finish_run(self.repository, run_id=run_id, at=at)

    def fail_run(self, *, run_id: str, at: datetime | None = None) -> RunRecord:
        return fail_run(self.repository, run_id=run_id, at=at)

    def get_run(self, *, run_id: str, monitor_id: str | None = None) -> RunRecord | None:
        return get_run(self.repository, run_id=run_id, monitor_id=monitor_id)

    def has_run(self, *, run_id: str, monitor_id: str | None = None) -> bool:
        return has_run(self.repository, run_id=run_id, monitor_id=monitor_id)

    def list_runs(
        self,
        *,
        status: str | None = None,
        monitor_id: str | None = None,
    ) -> list[RunRecord]:
        return list_runs(self.repository, status=status, monitor_id=monitor_id)

    def count_runs(
        self,
        *,
        status: str | None = None,
        monitor_id: str | None = None,
    ) -> int:
        return count_runs(self.repository, status=status, monitor_id=monitor_id)

    def get_latest_run_for_monitor(
        self,
        *,
        monitor_id: str,
        status: str | None = None,
    ) -> RunRecord | None:
        return get_latest_run_for_monitor(self.repository, monitor_id=monitor_id, status=status)

    def execute_run(
        self,
        *,
        run_id: str,
        monitor_id: str,
        operation: Callable[[], T],
    ) -> RunExecutionResult[T]:
        self.start_run(run_id=run_id, monitor_id=monitor_id, at=self.now_provider())
        try:
            result = operation()
        except Exception as exc:
            failed_run = self.fail_run(run_id=run_id, at=self.now_provider())
            return RunExecutionResult(run=failed_run, outcome=failed_run.status, error=exc)
        finished_run = self.finish_run(run_id=run_id, at=self.now_provider())
        return RunExecutionResult(run=finished_run, outcome=finished_run.status, value=result)
