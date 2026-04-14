from datetime import UTC, datetime
from pathlib import Path

from observer_rock.application.monitoring import (
    MonitorExecutionService,
    MonitorSourceData,
    MonitorSourceRecord,
)
from observer_rock.application.repositories import RunStatus
from observer_rock.application.services import RunService
from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.config.models import MonitorsConfig, ServicesConfig
from observer_rock.config.workspace import WorkspaceConfig
from observer_rock.plugins.registry import PluginRegistry
from tests._helpers import _RecordingSourcePlugin, _sequence_now_provider


def test_monitor_execution_service_fetches_and_normalizes_source_records() -> None:
    plugin = _RecordingSourcePlugin(
        payload=[
            {
                "source_id": " item-001 ",
                "content": "  first post  ",
                "document_identity": "  council/2026-03-14/protocol  ",
                "title": "  Council protocol  ",
            },
            {"source_id": "item-002", "content": "second post"},
        ]
    )
    registry = PluginRegistry()
    registry.register_source_plugin("reddit_fetch", plugin)
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=Path("C:/workspace"),
            services=ServicesConfig.validate_payload({"services": {}}),
            monitors=MonitorsConfig.validate_payload(
                {
                    "monitors": [
                        {
                            "id": "monitor-123",
                            "schedule": "*/5 * * * *",
                            "source": {"plugin": "reddit_fetch"},
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
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-source-001",
        plugin_registry=registry,
    )

    execution = service.execute_monitor_source(monitor_id="monitor-123")

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.monitor_id == "monitor-123"
    assert execution.value.source_plugin == "reddit_fetch"
    assert len(execution.value.records) == 2
    assert execution.value.records[0].source_id == "item-001"
    assert execution.value.records[0].content == "first post"
    assert execution.value.records[0].document_identity == "council/2026-03-14/protocol"
    assert execution.value.records[0].title == "Council protocol"
    assert execution.value.records[1].source_id == "item-002"
    assert execution.value.records[1].content == "second post"
    assert execution.value.records[1].document_identity is None
    assert execution.value.records[1].title is None
    assert plugin.calls == ["monitor-123"]


def test_monitor_execution_service_passes_normalized_source_data_to_analysis_plugins() -> None:
    from observer_rock.config.models import AnalysisProfilesConfig
    from tests._helpers import _RecordingAnalysisPlugin

    source_plugin = _RecordingSourcePlugin(
        payload=[{"source_id": " item-001 ", "content": "  first post  "}]
    )
    analysis_plugin = _RecordingAnalysisPlugin(output={"summary": "ok"})
    registry = PluginRegistry()
    registry.register_source_plugin("reddit_fetch", source_plugin)
    registry.register_analysis_plugin("llm_extract", analysis_plugin)
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
                            "source": {"plugin": "reddit_fetch"},
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
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-analysis-002",
        plugin_registry=registry,
    )

    execution = service.execute_monitor_analysis(monitor_id="monitor-123")

    assert execution.outcome is RunStatus.COMPLETED
    assert analysis_plugin.received_source_data == [
        MonitorSourceData(
            monitor_id="monitor-123",
            source_plugin="reddit_fetch",
            records=(
                MonitorSourceRecord(
                    source_id="item-001",
                    content="first post",
                    document_identity=None,
                    title=None,
                ),
            ),
        )
    ]
