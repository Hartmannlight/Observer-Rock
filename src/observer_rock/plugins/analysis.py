from typing import TYPE_CHECKING, Protocol, runtime_checkable

from observer_rock.config.models import AnalysisProfileConfig, MonitorConfig

if TYPE_CHECKING:
    from observer_rock.application.monitoring import MonitorSourceData


@runtime_checkable
class AnalysisPlugin(Protocol):
    def analyze(
        self,
        *,
        monitor: MonitorConfig,
        profile_name: str,
        profile: AnalysisProfileConfig,
        source_data: "MonitorSourceData | None" = None,
    ) -> object:
        """Execute one configured monitor analysis and return a serializable output."""
