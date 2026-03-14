from datetime import datetime


class _RecordingAnalysisPlugin:
    def __init__(self, output: object) -> None:
        self.output = output
        self.calls: list[tuple[str, str]] = []

    def analyze(self, *, monitor, profile_name, profile) -> object:
        self.calls.append((monitor.id, profile_name))
        return self.output


def _sequence_now_provider(*values: datetime):
    iterator = iter(values)

    def provider() -> datetime:
        return next(iterator)

    return provider
