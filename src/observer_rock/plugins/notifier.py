from typing import Protocol, runtime_checkable

from observer_rock.config.models import MonitorConfig, ServiceConfig


@runtime_checkable
class NotifierPlugin(Protocol):
    def notify(
        self,
        *,
        monitor: MonitorConfig,
        service_name: str,
        service: ServiceConfig,
        payload: str,
    ) -> object:
        """Deliver one rendered payload through a configured service."""
