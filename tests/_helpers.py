from datetime import datetime


class _RecordingAnalysisPlugin:
    def __init__(self, output: object) -> None:
        self.output = output
        self.calls: list[tuple[str, str]] = []
        self.received_source_data: list[object | None] = []

    def analyze(self, *, monitor, profile_name, profile, source_data=None) -> object:
        self.calls.append((monitor.id, profile_name))
        self.received_source_data.append(source_data)
        return self.output


class _SourceAwareAnalysisPlugin:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.received_source_data: list[object | None] = []

    def analyze(self, *, monitor, profile_name, profile, source_data=None) -> object:
        self.calls.append((monitor.id, profile_name))
        self.received_source_data.append(source_data)
        records = getattr(source_data, "records", ())
        return {
            "record_count": len(records),
            "source_ids": [record.source_id for record in records],
            "contents": [record.content for record in records],
        }


class _RecordingSourcePlugin:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def fetch(self, *, monitor) -> object:
        self.calls.append(monitor.id)
        return self.payload


class _RecordingRendererPlugin:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def render(self, *, monitor, output, analysis_output, source_data=None) -> str:
        self.calls.append((monitor.id, output.profile))
        return (
            f"{monitor.id}|{analysis_output.profile_name}|"
            f"{analysis_output.output['record_count']}"
        )


class _RecordingNotifierPlugin:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def notify(self, *, monitor, service_name, service, payload: str) -> object:
        self.calls.append((monitor.id, service_name, payload))
        return {"service_name": service_name, "payload": payload}


def _sequence_now_provider(*values: datetime):
    iterator = iter(values)

    def provider() -> datetime:
        return next(iterator)

    return provider
