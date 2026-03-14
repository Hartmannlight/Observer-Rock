from typing import Protocol, runtime_checkable

from observer_rock.config.models import AnalysisProfileConfig, MonitorConfig


@runtime_checkable
class AnalysisPlugin(Protocol):
    def analyze(
        self,
        *,
        monitor: MonitorConfig,
        profile_name: str,
        profile: AnalysisProfileConfig,
    ) -> object:
        """Execute one configured monitor analysis and return a serializable output."""
