from datetime import UTC, datetime
from pathlib import Path

from observer_rock.application.monitoring import MonitorExecutionService
from observer_rock.application.repositories import RunStatus
from observer_rock.application.services import RunService
from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.config.models import AnalysisProfilesConfig, MonitorsConfig, ServicesConfig
from observer_rock.config.workspace import WorkspaceConfig
from observer_rock.plugins.registry import PluginRegistry
from tests._helpers import _RecordingAnalysisPlugin, _sequence_now_provider


def test_monitor_execution_service_executes_analysis_plugins_for_a_monitor() -> None:
    plugin = _RecordingAnalysisPlugin(output={"summary": "ok"})
    registry = PluginRegistry()
    registry.register_analysis_plugin("llm_extract", plugin)
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=Path("C:/workspace"),
            services=ServicesConfig.validate_payload({"services": {}}),
            analysis_profiles=AnalysisProfilesConfig.validate_payload(
                {
                    "analysis_profiles": {
                        "summary_v2": {
                            "plugin": "llm_extract",
                            "model_service": "openai_strong",
                        }
                    }
                }
            ),
            monitors=MonitorsConfig.validate_payload(
                {
                    "monitors": [
                        {
                            "id": "monitor-123",
                            "schedule": "*/5 * * * *",
                            "source": {"plugin": "reddit"},
                            "analyses": [{"profile": "summary_v2"}],
                        }
                    ]
                }
            ),
        ),
        run_service=RunService(
            InMemoryRunRepository(),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-analysis-001",
        plugin_registry=registry,
    )

    execution = service.execute_monitor_analysis(monitor_id="monitor-123")

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.monitor_id == "monitor-123"
    assert len(execution.value.outputs) == 1
    assert execution.value.outputs[0].profile_name == "summary_v2"
    assert execution.value.outputs[0].plugin == "llm_extract"
    assert execution.value.outputs[0].output == {"summary": "ok"}
    assert plugin.calls == [("monitor-123", "summary_v2")]
