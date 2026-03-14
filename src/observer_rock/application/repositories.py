from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class RunStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {RunStatus.COMPLETED, RunStatus.FAILED}

    def can_transition_to(self, target: "RunStatus") -> bool:
        return self is RunStatus.STARTED and target in {
            RunStatus.COMPLETED,
            RunStatus.FAILED,
        }


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    monitor_id: str
    status: RunStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", RunStatus(self.status))
        if self.status is RunStatus.STARTED and self.ended_at is not None:
            raise ValueError("started run cannot define ended_at")
        if self.status.is_terminal and self.ended_at is None:
            raise ValueError("terminal run must define ended_at")


class RunRepository(Protocol):
    def create(self, run: RunRecord) -> RunRecord:
        """Persist a run record."""

    def save(self, run: RunRecord) -> RunRecord:
        """Persist changes to a run record."""

    def get(self, run_id: str) -> RunRecord | None:
        """Return a run record by id, if present."""

    def list_runs(self) -> list[RunRecord]:
        """Return all run records in deterministic order."""
