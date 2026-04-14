from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from observer_rock.application.documents import DocumentRecord
from observer_rock.application.monitoring import (
    MonitorAnalysisArtifactReader,
    MonitorExecutionService,
    MonitorSourceArtifactReader,
)
from observer_rock.application.repositories import RunStatus
from observer_rock.application.services import RunService
from observer_rock.config.models import AnalysisProfilesConfig, MonitorsConfig, ServicesConfig
from observer_rock.config.workspace import WorkspaceConfig
from observer_rock.infrastructure.artifacts import FilesystemArtifactStore
from observer_rock.infrastructure.sqlite import SqliteDocumentRepository, SqliteRunRepository
from observer_rock.plugins.registry import PluginRegistry
from tests._helpers import (
    _RecordingAnalysisPlugin,
    _RecordingSourcePlugin,
    _SourceAwareAnalysisPlugin,
    _sequence_now_provider,
)


def test_monitor_execution_service_persists_monitor_runs_in_sqlite(tmp_path: Path) -> None:
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
            services=ServicesConfig.validate_payload({"services": {}}),
            monitors=MonitorsConfig.validate_payload(
                {
                    "monitors": [
                        {
                            "id": "monitor-123",
                            "schedule": "*/5 * * * *",
                            "source": {"plugin": "reddit"},
                        }
                    ]
                }
            ),
        ),
        run_service=RunService(
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-001",
    )

    execution = service.execute_monitor(
        monitor_id="monitor-123",
        operation=lambda monitor: monitor.schedule,
    )

    assert execution.monitor.id == "monitor-123"
    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value == "*/5 * * * *"
    assert service.run_service.get_run(run_id="monitor-123-run-001") == execution.run


def test_monitor_execution_service_persists_monitor_snapshot_runs_in_sqlite(
    tmp_path: Path,
) -> None:
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
            services=ServicesConfig.validate_payload({"services": {}}),
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
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-snapshot-001",
    )

    execution = service.execute_monitor_snapshot(monitor_id="monitor-123")

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.monitor_id == "monitor-123"
    assert execution.value.analysis_profiles == ("summary_v2",)
    assert service.run_service.get_run(run_id="monitor-123-run-snapshot-001") == execution.run


def test_monitor_execution_service_persists_monitor_analysis_plan_runs_in_sqlite(
    tmp_path: Path,
) -> None:
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
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
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-plan-001",
    )

    execution = service.execute_monitor_analysis_plan(monitor_id="monitor-123")

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.monitor_id == "monitor-123"
    assert len(execution.value.analyses) == 1
    assert execution.value.analyses[0].profile_name == "summary_v2"
    assert service.run_service.get_run(run_id="monitor-123-run-plan-001") == execution.run


def test_monitor_execution_service_persists_monitor_definition_runs_in_sqlite(
    tmp_path: Path,
) -> None:
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
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
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-definition-001",
    )

    execution = service.execute_monitor_definition(monitor_id="monitor-123")

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.snapshot.monitor_id == "monitor-123"
    assert execution.value.analysis_plan.analyses[0].profile_name == "summary_v2"
    assert (
        service.run_service.get_run(run_id="monitor-123-run-definition-001") == execution.run
    )


def test_monitor_execution_service_persists_monitor_execution_plan_runs_in_sqlite(
    tmp_path: Path,
) -> None:
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
            services=ServicesConfig.validate_payload(
                {"services": {"openai_strong": {"plugin": "openai"}}}
            ),
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
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-execution-001",
    )

    execution = service.execute_monitor_execution_plan(monitor_id="monitor-123")

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.definition.snapshot.monitor_id == "monitor-123"
    assert execution.value.analysis_bindings[0].service_name == "openai_strong"
    assert (
        service.run_service.get_run(run_id="monitor-123-run-execution-001") == execution.run
    )


def test_monitor_execution_service_persists_monitor_execution_plan_artifact(
    tmp_path: Path,
) -> None:
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
            services=ServicesConfig.validate_payload(
                {"services": {"openai_strong": {"plugin": "openai"}}}
            ),
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
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-execution-artifact-001",
    )

    execution = service.execute_monitor_execution_plan_artifact(
        monitor_id="monitor-123",
        document_repository=SqliteDocumentRepository(tmp_path / "documents.db"),
        artifact_store=FilesystemArtifactStore(tmp_path / "artifacts"),
    )

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.document.document_id == "monitor-123-execution-plan"
    assert execution.value.document.version == 1
    assert execution.value.artifact.document_id == "monitor-123-execution-plan"
    assert execution.value.artifact.version == 1
    assert execution.value.artifact.artifact_name == "monitor_execution_plan.json"
    assert execution.value.artifact.content_type == "application/json"
    assert execution.value.artifact.path.read_text(encoding="utf-8") == (
        '{"definition":{"snapshot":{"monitor_id":"monitor-123","schedule":"*/5 * * * *",'
        '"source_plugin":"reddit","analysis_profiles":["summary_v2"]},"analysis_plan":'
        '{"monitor_id":"monitor-123","analyses":[{"profile_name":"summary_v2",'
        '"plugin":"llm_extract","model_service":"openai_strong"}]}},'
        '"analysis_bindings":[{"profile_name":"summary_v2","service_name":"openai_strong",'
        '"service_plugin":"openai"}]}'
    )
    assert (
        service.run_service.get_run(run_id="monitor-123-run-execution-artifact-001")
        == execution.run
    )


def test_monitor_execution_service_persists_monitor_definition_artifact(
    tmp_path: Path,
) -> None:
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
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
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-definition-artifact-001",
    )

    execution = service.execute_monitor_definition_artifact(
        monitor_id="monitor-123",
        document_repository=SqliteDocumentRepository(tmp_path / "documents.db"),
        artifact_store=FilesystemArtifactStore(tmp_path / "artifacts"),
    )

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.document.document_id == "monitor-123-definition"
    assert execution.value.document.version == 1
    assert execution.value.artifact.document_id == "monitor-123-definition"
    assert execution.value.artifact.version == 1
    assert execution.value.artifact.artifact_name == "monitor_definition.json"
    assert execution.value.artifact.content_type == "application/json"
    assert execution.value.artifact.path.read_text(encoding="utf-8") == (
        '{"snapshot":{"monitor_id":"monitor-123","schedule":"*/5 * * * *",'
        '"source_plugin":"reddit","analysis_profiles":["summary_v2"]},"analysis_plan":'
        '{"monitor_id":"monitor-123","analyses":[{"profile_name":"summary_v2",'
        '"plugin":"llm_extract","model_service":"openai_strong"}]}}'
    )
    assert (
        service.run_service.get_run(run_id="monitor-123-run-definition-artifact-001")
        == execution.run
    )


def test_monitor_execution_service_persists_monitor_analysis_plan_artifact(
    tmp_path: Path,
) -> None:
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
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
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-analysis-plan-artifact-001",
    )

    execution = service.execute_monitor_analysis_plan_artifact(
        monitor_id="monitor-123",
        document_repository=SqliteDocumentRepository(tmp_path / "documents.db"),
        artifact_store=FilesystemArtifactStore(tmp_path / "artifacts"),
    )

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.document.document_id == "monitor-123-analysis-plan"
    assert execution.value.document.version == 1
    assert execution.value.artifact.document_id == "monitor-123-analysis-plan"
    assert execution.value.artifact.version == 1
    assert execution.value.artifact.artifact_name == "monitor_analysis_plan.json"
    assert execution.value.artifact.content_type == "application/json"
    assert execution.value.artifact.path.read_text(encoding="utf-8") == (
        '{"monitor_id":"monitor-123","analyses":[{"profile_name":"summary_v2",'
        '"plugin":"llm_extract","model_service":"openai_strong"}]}'
    )
    assert (
        service.run_service.get_run(run_id="monitor-123-run-analysis-plan-artifact-001")
        == execution.run
    )


def test_monitor_execution_service_persists_monitor_analysis_output_artifact() -> None:
    workspace = _make_local_component_workspace("monitor-analysis-output-artifact")
    plugin = _RecordingAnalysisPlugin(output={"summary": "ok"})
    source_plugin = _RecordingSourcePlugin(
        payload=[{"source_id": "item-001", "content": "first post"}]
    )
    registry = PluginRegistry()
    registry.register_analysis_plugin("llm_extract", plugin)
    registry.register_source_plugin("reddit", source_plugin)
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=workspace,
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
            SqliteRunRepository(workspace / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-analysis-artifact-001",
        plugin_registry=registry,
    )

    execution = service.execute_monitor_analysis_artifact(
        monitor_id="monitor-123",
        document_repository=SqliteDocumentRepository(workspace / "documents.db"),
        artifact_store=FilesystemArtifactStore(workspace / "artifacts"),
    )

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.document.document_id == "monitor-123-analysis-output"
    assert execution.value.document.version == 1
    assert execution.value.artifact.document_id == "monitor-123-analysis-output"
    assert execution.value.artifact.version == 1
    assert execution.value.artifact.artifact_name == "monitor_analysis.json"
    assert execution.value.artifact.content_type == "application/json"
    assert execution.value.artifact.path.read_text(encoding="utf-8") == (
        '{"monitor_id":"monitor-123","outputs":[{"profile_name":"summary_v2",'
        '"plugin":"llm_extract","output":{"summary":"ok"}}]}'
    )
    assert plugin.calls == [("monitor-123", "summary_v2")]
    assert (
        service.run_service.get_run(run_id="monitor-123-run-analysis-artifact-001")
        == execution.run
    )


def test_monitor_execution_service_persists_monitor_source_artifact() -> None:
    workspace = _make_local_component_workspace("monitor-source-artifact")
    plugin = _RecordingSourcePlugin(
        payload=[
            {"source_id": " item-001 ", "content": "  first post  "},
            {"source_id": "item-002", "content": "second post"},
        ]
    )
    registry = PluginRegistry()
    registry.register_source_plugin("reddit_fetch", plugin)
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=workspace,
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
            SqliteRunRepository(workspace / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-source-artifact-001",
        plugin_registry=registry,
    )

    execution = service.execute_monitor_source_artifact(
        monitor_id="monitor-123",
        document_repository=SqliteDocumentRepository(workspace / "documents.db"),
        artifact_store=FilesystemArtifactStore(workspace / "artifacts"),
    )

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.document.document_id == "monitor-123-source-data"
    assert execution.value.document.version == 1
    assert execution.value.artifact.document_id == "monitor-123-source-data"
    assert execution.value.artifact.version == 1
    assert execution.value.artifact.artifact_name == "monitor_source_data.json"
    assert execution.value.artifact.content_type == "application/json"
    assert execution.value.artifact.path.read_text(encoding="utf-8") == (
        '{"monitor_id":"monitor-123","source_plugin":"reddit_fetch","records":'
        '[{"source_id":"item-001","content":"first post"},'
        '{"source_id":"item-002","content":"second post"}]}'
    )
    assert plugin.calls == ["monitor-123"]
    assert (
        service.run_service.get_run(run_id="monitor-123-run-source-artifact-001")
        == execution.run
    )


def test_monitor_execution_service_increments_monitor_source_artifact_document_versions(
    tmp_path: Path,
) -> None:
    run_ids = iter(
        [
            "monitor-123-run-source-artifact-001",
            "monitor-123-run-source-artifact-002",
        ]
    )
    plugin = _RecordingSourcePlugin(
        payload=[
            {"source_id": "item-001", "content": "first post"},
            {"source_id": "item-002", "content": "second post"},
        ]
    )
    registry = PluginRegistry()
    registry.register_source_plugin("reddit_fetch", plugin)
    document_repository = SqliteDocumentRepository(tmp_path / "documents.db")
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
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
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
                datetime(2026, 3, 14, 13, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 13, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: next(run_ids),
        plugin_registry=registry,
    )

    first_execution = service.execute_monitor_source_artifact(
        monitor_id="monitor-123",
        document_repository=document_repository,
        artifact_store=FilesystemArtifactStore(tmp_path / "artifacts"),
    )
    second_execution = service.execute_monitor_source_artifact(
        monitor_id="monitor-123",
        document_repository=document_repository,
        artifact_store=FilesystemArtifactStore(tmp_path / "artifacts"),
    )

    persisted = SqliteDocumentRepository(tmp_path / "documents.db")

    assert first_execution.outcome is RunStatus.COMPLETED
    assert second_execution.outcome is RunStatus.COMPLETED
    assert first_execution.value is not None
    assert second_execution.value is not None
    assert first_execution.value.document == DocumentRecord(
        document_id="monitor-123-source-data",
        version=1,
    )
    assert second_execution.value.document == DocumentRecord(
        document_id="monitor-123-source-data",
        version=2,
    )
    assert persisted.get("monitor-123-source-data", version=1) == first_execution.value.document
    assert persisted.get("monitor-123-source-data", version=2) == second_execution.value.document
    assert persisted.get_latest("monitor-123-source-data") == second_execution.value.document
    assert second_execution.value.artifact.path.read_text(encoding="utf-8") == (
        '{"monitor_id":"monitor-123","source_plugin":"reddit_fetch","records":'
        '[{"source_id":"item-001","content":"first post"},'
        '{"source_id":"item-002","content":"second post"}]}'
    )


def test_monitor_execution_service_persists_monitor_snapshot_artifact(
    tmp_path: Path,
) -> None:
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
            services=ServicesConfig.validate_payload({"services": {}}),
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
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-artifact-001",
    )

    execution = service.execute_monitor_snapshot_artifact(
        monitor_id="monitor-123",
        document_repository=SqliteDocumentRepository(tmp_path / "documents.db"),
        artifact_store=FilesystemArtifactStore(tmp_path / "artifacts"),
    )

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.document.document_id == "monitor-123-snapshot"
    assert execution.value.document.version == 1
    assert execution.value.artifact.document_id == "monitor-123-snapshot"
    assert execution.value.artifact.version == 1
    assert execution.value.artifact.artifact_name == "monitor_snapshot.json"
    assert execution.value.artifact.content_type == "application/json"
    assert (
        execution.value.artifact.path.read_text(encoding="utf-8")
        == '{"monitor_id":"monitor-123","schedule":"*/5 * * * *",'
        '"source_plugin":"reddit","analysis_profiles":["summary_v2"]}'
    )
    assert service.run_service.get_run(run_id="monitor-123-run-artifact-001") == execution.run


def test_monitor_execution_service_increments_monitor_snapshot_artifact_document_versions(
    tmp_path: Path,
) -> None:
    run_ids = iter(
        [
            "monitor-123-run-artifact-001",
            "monitor-123-run-artifact-002",
        ]
    )
    document_repository = SqliteDocumentRepository(tmp_path / "documents.db")
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=tmp_path,
            services=ServicesConfig.validate_payload({"services": {}}),
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
            SqliteRunRepository(tmp_path / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
                datetime(2026, 3, 14, 13, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 13, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: next(run_ids),
    )

    first_execution = service.execute_monitor_snapshot_artifact(
        monitor_id="monitor-123",
        document_repository=document_repository,
        artifact_store=FilesystemArtifactStore(tmp_path / "artifacts"),
    )
    second_execution = service.execute_monitor_snapshot_artifact(
        monitor_id="monitor-123",
        document_repository=document_repository,
        artifact_store=FilesystemArtifactStore(tmp_path / "artifacts"),
    )

    persisted = SqliteDocumentRepository(tmp_path / "documents.db")

    assert first_execution.outcome is RunStatus.COMPLETED
    assert second_execution.outcome is RunStatus.COMPLETED
    assert first_execution.value is not None
    assert second_execution.value is not None
    assert first_execution.value.document == DocumentRecord(
        document_id="monitor-123-snapshot",
        version=1,
    )
    assert second_execution.value.document == DocumentRecord(
        document_id="monitor-123-snapshot",
        version=2,
    )
    assert persisted.get("monitor-123-snapshot", version=1) == first_execution.value.document
    assert persisted.get("monitor-123-snapshot", version=2) == second_execution.value.document
    assert persisted.get_latest("monitor-123-snapshot") == second_execution.value.document
    assert second_execution.value.artifact.path.read_text(encoding="utf-8") == (
        '{"monitor_id":"monitor-123","schedule":"*/5 * * * *",'
        '"source_plugin":"reddit","analysis_profiles":["summary_v2"]}'
    )


def test_reader_loads_latest_persisted_monitor_analysis_output() -> None:
    workspace = _make_local_component_workspace("monitor-analysis-output-reader")
    plugin = _RecordingAnalysisPlugin(output={"summary": "latest"})
    source_plugin = _RecordingSourcePlugin(
        payload=[{"source_id": "item-001", "content": "first post"}]
    )
    registry = PluginRegistry()
    registry.register_analysis_plugin("llm_extract", plugin)
    registry.register_source_plugin("reddit", source_plugin)
    document_repository = SqliteDocumentRepository(workspace / "documents.db")
    artifact_store = FilesystemArtifactStore(workspace / "artifacts")
    writer = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=workspace,
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
            SqliteRunRepository(workspace / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-analysis-artifact-001",
        plugin_registry=registry,
    )

    writer.execute_monitor_analysis_artifact(
        monitor_id="monitor-123",
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    reader = MonitorAnalysisArtifactReader(
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    persisted_analysis = reader.load_latest(monitor_id="monitor-123")

    assert persisted_analysis.document.document_id == "monitor-123-analysis-output"
    assert persisted_analysis.document.version == 1
    assert persisted_analysis.artifact.document_id == "monitor-123-analysis-output"
    assert persisted_analysis.artifact.version == 1
    assert persisted_analysis.artifact.artifact_name == "monitor_analysis.json"
    assert persisted_analysis.artifact.content_type == "application/json"
    assert persisted_analysis.artifact.size_bytes > 0
    assert persisted_analysis.artifact.path.exists()
    assert persisted_analysis.analysis.monitor_id == "monitor-123"
    assert len(persisted_analysis.analysis.outputs) == 1
    assert persisted_analysis.analysis.outputs[0].profile_name == "summary_v2"
    assert persisted_analysis.analysis.outputs[0].plugin == "llm_extract"
    assert persisted_analysis.analysis.outputs[0].output == {"summary": "latest"}


def test_reader_loads_latest_persisted_monitor_source_data() -> None:
    workspace = _make_local_component_workspace("monitor-source-data-reader")
    plugin = _RecordingSourcePlugin(
        payload=[
            {"source_id": " item-001 ", "content": "  first post  "},
            {"source_id": "item-002", "content": "second post"},
        ]
    )
    registry = PluginRegistry()
    registry.register_source_plugin("reddit_fetch", plugin)
    document_repository = SqliteDocumentRepository(workspace / "documents.db")
    artifact_store = FilesystemArtifactStore(workspace / "artifacts")
    writer = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=workspace,
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
            SqliteRunRepository(workspace / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-source-artifact-001",
        plugin_registry=registry,
    )

    writer.execute_monitor_source_artifact(
        monitor_id="monitor-123",
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    reader = MonitorSourceArtifactReader(
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    persisted_source = reader.load_latest(monitor_id="monitor-123")

    assert persisted_source.document.document_id == "monitor-123-source-data"
    assert persisted_source.document.version == 1
    assert persisted_source.artifact.document_id == "monitor-123-source-data"
    assert persisted_source.artifact.version == 1
    assert persisted_source.artifact.artifact_name == "monitor_source_data.json"
    assert persisted_source.artifact.content_type == "application/json"
    assert persisted_source.artifact.size_bytes > 0
    assert persisted_source.artifact.path.exists()
    assert persisted_source.source.monitor_id == "monitor-123"
    assert persisted_source.source.source_plugin == "reddit_fetch"
    assert len(persisted_source.source.records) == 2
    assert persisted_source.source.records[0].source_id == "item-001"
    assert persisted_source.source.records[0].content == "first post"
    assert persisted_source.source.records[1].source_id == "item-002"
    assert persisted_source.source.records[1].content == "second post"


def test_monitor_execution_service_executes_analysis_from_latest_persisted_source_data() -> None:
    workspace = _make_local_component_workspace("monitor-analysis-from-persisted-source")
    run_ids = iter(
        [
            "monitor-123-run-source-artifact-001",
            "monitor-123-run-persisted-analysis-001",
        ]
    )
    source_plugin = _RecordingSourcePlugin(
        payload=[{"source_id": "persisted-001", "content": "persisted post"}]
    )
    analysis_plugin = _SourceAwareAnalysisPlugin()
    registry = PluginRegistry()
    registry.register_source_plugin("reddit_fetch", source_plugin)
    registry.register_analysis_plugin("llm_extract", analysis_plugin)
    document_repository = SqliteDocumentRepository(workspace / "documents.db")
    artifact_store = FilesystemArtifactStore(workspace / "artifacts")
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=workspace,
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
            SqliteRunRepository(workspace / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
                datetime(2026, 3, 14, 13, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 13, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: next(run_ids),
        plugin_registry=registry,
    )

    source_execution = service.execute_monitor_source_artifact(
        monitor_id="monitor-123",
        document_repository=document_repository,
        artifact_store=artifact_store,
    )
    source_plugin.payload = [{"source_id": "live-002", "content": "live post"}]

    analysis_execution = service.execute_monitor_analysis_artifact_from_latest_source_data(
        monitor_id="monitor-123",
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    assert source_execution.outcome is RunStatus.COMPLETED
    assert analysis_execution.outcome is RunStatus.COMPLETED
    assert analysis_execution.value is not None
    assert analysis_execution.value.document.document_id == "monitor-123-analysis-output"
    assert analysis_execution.value.document.version == 1
    assert analysis_execution.value.artifact.path.read_text(encoding="utf-8") == (
        '{"monitor_id":"monitor-123","outputs":[{"profile_name":"summary_v2",'
        '"plugin":"llm_extract","output":{"record_count":1,"source_ids":["persisted-001"],'
        '"contents":["persisted post"]}}]}'
    )
    assert source_plugin.calls == ["monitor-123"]
    assert analysis_plugin.calls == [("monitor-123", "summary_v2")]


def test_monitor_execution_service_fails_when_persisted_source_data_is_missing() -> None:
    workspace = _make_local_component_workspace("monitor-analysis-missing-persisted-source")
    analysis_plugin = _SourceAwareAnalysisPlugin()
    registry = PluginRegistry()
    registry.register_analysis_plugin("llm_extract", analysis_plugin)
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=workspace,
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
            SqliteRunRepository(workspace / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-persisted-analysis-missing-001",
        plugin_registry=registry,
    )

    execution = service.execute_monitor_analysis_artifact_from_latest_source_data(
        monitor_id="monitor-123",
        document_repository=SqliteDocumentRepository(workspace / "documents.db"),
        artifact_store=FilesystemArtifactStore(workspace / "artifacts"),
    )

    assert execution.outcome is RunStatus.FAILED
    assert execution.value is None
    assert isinstance(execution.error, KeyError)
    assert execution.error.args[0] == "Unknown document_id: monitor-123-source-data"


def test_monitor_execution_service_executes_canonical_source_to_analysis_workflow() -> None:
    workspace = _make_local_component_workspace("monitor-source-to-analysis-workflow")
    source_plugin = _RecordingSourcePlugin(
        payload=[{"source_id": "persisted-001", "content": "persisted post"}]
    )
    analysis_plugin = _SourceAwareAnalysisPlugin()
    registry = PluginRegistry()
    registry.register_source_plugin("reddit_fetch", source_plugin)
    registry.register_analysis_plugin("llm_extract", analysis_plugin)
    document_repository = SqliteDocumentRepository(workspace / "documents.db")
    artifact_store = FilesystemArtifactStore(workspace / "artifacts")
    service = MonitorExecutionService(
        workspace=WorkspaceConfig(
            root=workspace,
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
            SqliteRunRepository(workspace / "runs.db"),
            now_provider=_sequence_now_provider(
                datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                datetime(2026, 3, 14, 12, 30, tzinfo=UTC),
            ),
        ),
        run_id_factory=lambda monitor_id: f"{monitor_id}-run-canonical-workflow-001",
        plugin_registry=registry,
    )

    execution = service.execute_monitor_source_to_analysis_artifacts(
        monitor_id="monitor-123",
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    assert execution.outcome is RunStatus.COMPLETED
    assert execution.value is not None
    assert execution.value.source.document == DocumentRecord(
        document_id="monitor-123-source-data",
        version=1,
    )
    assert execution.value.analysis.document == DocumentRecord(
        document_id="monitor-123-analysis-output",
        version=1,
    )
    assert execution.value.source.artifact.path.read_text(encoding="utf-8") == (
        '{"monitor_id":"monitor-123","source_plugin":"reddit_fetch","records":'
        '[{"source_id":"persisted-001","content":"persisted post"}]}'
    )
    assert execution.value.analysis.artifact.path.read_text(encoding="utf-8") == (
        '{"monitor_id":"monitor-123","outputs":[{"profile_name":"summary_v2",'
        '"plugin":"llm_extract","output":{"record_count":1,"source_ids":["persisted-001"],'
        '"contents":["persisted post"]}}]}'
    )
    assert source_plugin.calls == ["monitor-123"]
    assert analysis_plugin.calls == [("monitor-123", "summary_v2")]
    assert service.run_service.get_run(run_id="monitor-123-run-canonical-workflow-001") == execution.run




def _make_local_component_workspace(test_name: str) -> Path:
    workspace = Path(".tmp") / "component" / test_name / uuid4().hex
    workspace.mkdir(parents=True, exist_ok=False)
    return workspace
