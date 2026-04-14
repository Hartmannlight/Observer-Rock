from typing import Protocol, runtime_checkable

from observer_rock.config.models import MonitorConfig, MonitorOutputConfig

if False:  # pragma: no cover
    from observer_rock.application.monitoring import MonitorAnalysisOutputEntry, MonitorSourceData


@runtime_checkable
class RendererPlugin(Protocol):
    def render(
        self,
        *,
        monitor: MonitorConfig,
        output: MonitorOutputConfig,
        analysis_output: "MonitorAnalysisOutputEntry",
        source_data: "MonitorSourceData | None" = None,
    ) -> str:
        """Render one analysis output into a notifier-ready payload."""
