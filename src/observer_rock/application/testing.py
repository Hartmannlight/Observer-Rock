from observer_rock.application.repositories import RunRecord, RunRepository


class InMemoryRunRepository(RunRepository):
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def create(self, run: RunRecord) -> RunRecord:
        if run.run_id in self._runs:
            raise KeyError(run.run_id)
        self._runs[run.run_id] = run
        return run

    def save(self, run: RunRecord) -> RunRecord:
        if run.run_id not in self._runs:
            raise KeyError(run.run_id)
        self._runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[RunRecord]:
        return list(self._runs.values())
