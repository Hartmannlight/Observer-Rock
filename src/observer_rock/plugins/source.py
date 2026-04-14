from typing import Protocol, runtime_checkable

from observer_rock.config.models import MonitorConfig


@runtime_checkable
class SourcePlugin(Protocol):
    def fetch(self, *, monitor: MonitorConfig) -> object:
        """Fetch raw source payloads for one monitor."""
