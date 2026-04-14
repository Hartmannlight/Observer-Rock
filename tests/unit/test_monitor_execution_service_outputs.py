from datetime import UTC, datetime
from pathlib import Path

from observer_rock.application.documents import DocumentRecord
from observer_rock.application.monitoring import MonitorExecutionService
from observer_rock.application.repositories import RunStatus
from observer_rock.application.services import RunService
from observer_rock.application.testing import InMemoryRunRepository
from observer_rock.config.models import AnalysisProfilesConfig, MonitorsConfig, ServicesConfig
from observer_rock.config.workspace import WorkspaceConfig
from observer_rock.infrastructure.artifacts import FilesystemArtifactStore
from observer_rock.infrastructure.sqlite import SqliteDocumentRepository
from observer_rock.plugins.registry import PluginRegistry
from tests._helpers import (
    _RecordingNotifierPlugin,
    _RecordingRendererPlugin,
    _RecordingSourcePlugin,
    _SourceAwareAnalysisPlugin,
    _sequence_now_provider,
)


def test_monitor_execution_service_delivers_rendered_outputs_and_persists_notifications(
    tmp_path: Path,
) -> None:
    source_plugin = _RecordingSourcePlugin(
        payload=[{"source_id": "item-001", "content": "first post"}]
    )
    analysis_plugin = _SourceAwareAnalysisPlugin()
    renderer_plugin = _RecordingRendererPlugin()
    notifier_plugin = _RecordingNotifierPlugin()

    registry = PluginRegistry()
    registry.register_source_plugin("reddit_fetch", source_plugin)
    registry.register_analysis_plugin("llm_extract", analysis_plugin)
    registry.register_renderer_plugin("digest_renderer", renderer_plugin)
    registry.register_notifier_plugin("capture_notifier", notifier_plugin)

    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
            services=ServicesConfig.validate_payload(
                {
                    "services": {
                        "local_model": {"plugin": "noop_model"},
                        "local_output": {"plugin": "capture_notifier"},
                    }
                }
            ),
            analysis_profiles=AnalysisProfilesConfig.validate_payload(
                {
                    "analysis_profiles": {
                        "summary_v2": {
                            "plugin": "llm_extract",
                            "model_service": "local_model",
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
                            "outputs": [
                                {
                                    "profile": "summary_v2",
                                    "renderer": "digest_renderer",
                                    "service": "local_output",
                                }
                            ],
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
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-output-001",
        plugin_registry=registry,
    )
    document_repository = SqliteDocumentRepository(tmp_path / "documents.db")
    artifact_store = FilesystemArtifactStore(tmp_path / "artifacts")

    execution = service.execute_monitor_source_to_analysis_artifacts(
        monitor_id="monitor-123",
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.notifications is not None
    assert execution.value.notifications.document == DocumentRecord(
        document_id="monitor-123-notifications",
        version=1,
    )
    assert (
        tmp_path / "artifacts" / "monitor-123-notifications" / "v1" / "monitor_notifications.json"
    ).exists()
    assert analysis_plugin.calls == [("monitor-123", "summary_v2")]
    assert renderer_plugin.calls == [("monitor-123", "summary_v2")]
    assert notifier_plugin.calls == [("monitor-123", "local_output", "monitor-123|summary_v2|1")]
