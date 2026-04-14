import json
from dataclasses import asdict, dataclass
from collections.abc import Mapping
from typing import Callable, TypeVar

from observer_rock.application.artifacts import ArtifactRef, ArtifactStore
from observer_rock.application.documents import DocumentRecord, DocumentRepository
from observer_rock.application.services import RunExecutionResult, RunService
from observer_rock.config.models import (
    AnalysisProfileConfig,
    MonitorConfig,
    MonitorOutputConfig,
    ServiceConfig,
)
from observer_rock.config.workspace import WorkspaceConfig
from observer_rock.plugins.registry import PluginRegistry

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class MonitorSnapshot:
    monitor_id: str
    schedule: str
    source_plugin: str
    analysis_profiles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MonitorAnalysisPlanEntry:
    profile_name: str
    plugin: str
    model_service: str


@dataclass(frozen=True, slots=True)
class MonitorAnalysisPlan:
    monitor_id: str
    analyses: tuple[MonitorAnalysisPlanEntry, ...]


@dataclass(frozen=True, slots=True)
class MonitorAnalysisOutputEntry:
    profile_name: str
    plugin: str
    output: object


@dataclass(frozen=True, slots=True)
class MonitorAnalysis:
    monitor_id: str
    outputs: tuple[MonitorAnalysisOutputEntry, ...]


@dataclass(frozen=True, slots=True)
class MonitorNotificationDelivery:
    profile_name: str
    renderer: str
    service_name: str
    notifier_plugin: str
    payload: str


@dataclass(frozen=True, slots=True)
class MonitorNotifications:
    monitor_id: str
    deliveries: tuple[MonitorNotificationDelivery, ...]


@dataclass(frozen=True, slots=True)
class MonitorSourceRecord:
    source_id: str
    content: str


@dataclass(frozen=True, slots=True)
class MonitorSourceData:
    monitor_id: str
    source_plugin: str
    records: tuple[MonitorSourceRecord, ...]


@dataclass(frozen=True, slots=True)
class MonitorDefinition:
    snapshot: MonitorSnapshot
    analysis_plan: MonitorAnalysisPlan


@dataclass(frozen=True, slots=True)
class MonitorExecutionPlanBinding:
    profile_name: str
    service_name: str
    service_plugin: str


@dataclass(frozen=True, slots=True)
class MonitorExecutionPlan:
    definition: MonitorDefinition
    analysis_bindings: tuple[MonitorExecutionPlanBinding, ...]


@dataclass(frozen=True, slots=True)
class PersistedMonitorArtifact:
    document: DocumentRecord
    artifact: ArtifactRef


@dataclass(frozen=True, slots=True)
class PersistedMonitorAnalysisArtifact:
    document: DocumentRecord
    artifact: ArtifactRef
    analysis: MonitorAnalysis


@dataclass(frozen=True, slots=True)
class PersistedMonitorSourceArtifact:
    document: DocumentRecord
    artifact: ArtifactRef
    source: MonitorSourceData


@dataclass(frozen=True, slots=True)
class PersistedMonitorSourceToAnalysisArtifacts:
    source: PersistedMonitorArtifact
    analysis: PersistedMonitorArtifact
    notifications: PersistedMonitorArtifact | None = None


@dataclass(frozen=True, slots=True)
class MonitorAnalysisArtifactReader:
    document_repository: DocumentRepository
    artifact_store: ArtifactStore

    def load_latest(self, *, monitor_id: str) -> PersistedMonitorAnalysisArtifact:
        document_id = f"{monitor_id}-analysis-output"
        latest_document = self.document_repository.get_latest(document_id)
        if latest_document is None:
            raise KeyError(f"Unknown document_id: {document_id}")

        loaded_artifact = self.artifact_store.load(
            document_id=latest_document.document_id,
            version=latest_document.version,
            artifact_name="monitor_analysis.json",
            content_type="application/json",
        )
        return PersistedMonitorAnalysisArtifact(
            document=latest_document,
            artifact=loaded_artifact.artifact,
            analysis=_deserialize_monitor_analysis(loaded_artifact.data),
        )


@dataclass(frozen=True, slots=True)
class MonitorSourceArtifactReader:
    document_repository: DocumentRepository
    artifact_store: ArtifactStore

    def load_latest(self, *, monitor_id: str) -> PersistedMonitorSourceArtifact:
        document_id = f"{monitor_id}-source-data"
        latest_document = self.document_repository.get_latest(document_id)
        if latest_document is None:
            raise KeyError(f"Unknown document_id: {document_id}")

        loaded_artifact = self.artifact_store.load(
            document_id=latest_document.document_id,
            version=latest_document.version,
            artifact_name="monitor_source_data.json",
            content_type="application/json",
        )
        return PersistedMonitorSourceArtifact(
            document=latest_document,
            artifact=loaded_artifact.artifact,
            source=_deserialize_monitor_source_data(loaded_artifact.data),
        )


@dataclass(frozen=True, slots=True)
class MonitorExecutionResult[T]:
    monitor: MonitorConfig
    execution: RunExecutionResult[T]

    @property
    def run(self):
        return self.execution.run

    @property
    def outcome(self):
        return self.execution.outcome

    @property
    def value(self):
        return self.execution.value

    @property
    def error(self):
        return self.execution.error


@dataclass(frozen=True, slots=True)
class MonitorExecutionService:
    workspace: WorkspaceConfig
    run_service: RunService
    run_id_factory: Callable[[str], str]
    plugin_registry: PluginRegistry | None = None

    def execute_monitor(
        self,
        *,
        monitor_id: str,
        operation: Callable[[MonitorConfig], T],
    ) -> MonitorExecutionResult[T]:
        monitor = self.get_monitor(monitor_id=monitor_id)
        run_id = self.run_id_factory(monitor.id)
        execution = self.run_service.execute_run(
            run_id=run_id,
            monitor_id=monitor.id,
            operation=lambda: operation(monitor),
        )
        return MonitorExecutionResult(monitor=monitor, execution=execution)

    def execute_monitor_snapshot(
        self,
        *,
        monitor_id: str,
    ) -> MonitorExecutionResult[MonitorSnapshot]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=self._build_monitor_snapshot,
        )

    def execute_monitor_analysis_plan(
        self,
        *,
        monitor_id: str,
    ) -> MonitorExecutionResult[MonitorAnalysisPlan]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=self._build_monitor_analysis_plan,
        )

    def execute_monitor_analysis(
        self,
        *,
        monitor_id: str,
    ) -> MonitorExecutionResult[MonitorAnalysis]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=self._build_monitor_analysis,
        )

    def execute_monitor_source(
        self,
        *,
        monitor_id: str,
    ) -> MonitorExecutionResult[MonitorSourceData]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=self._build_monitor_source_data,
        )

    def execute_monitor_definition(
        self,
        *,
        monitor_id: str,
    ) -> MonitorExecutionResult[MonitorDefinition]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=self._build_monitor_definition,
        )

    def execute_monitor_execution_plan(
        self,
        *,
        monitor_id: str,
    ) -> MonitorExecutionResult[MonitorExecutionPlan]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=self._build_monitor_execution_plan,
        )

    def execute_monitor_snapshot_artifact(
        self,
        *,
        monitor_id: str,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> MonitorExecutionResult[PersistedMonitorArtifact]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=lambda monitor: self._persist_monitor_snapshot_artifact(
                monitor=monitor,
                document_repository=document_repository,
                artifact_store=artifact_store,
            ),
        )

    def execute_monitor_execution_plan_artifact(
        self,
        *,
        monitor_id: str,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> MonitorExecutionResult[PersistedMonitorArtifact]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=lambda monitor: self._persist_monitor_execution_plan_artifact(
                monitor=monitor,
                document_repository=document_repository,
                artifact_store=artifact_store,
            ),
        )

    def execute_monitor_analysis_plan_artifact(
        self,
        *,
        monitor_id: str,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> MonitorExecutionResult[PersistedMonitorArtifact]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=lambda monitor: self._persist_monitor_analysis_plan_artifact(
                monitor=monitor,
                document_repository=document_repository,
                artifact_store=artifact_store,
            ),
        )

    def execute_monitor_analysis_artifact(
        self,
        *,
        monitor_id: str,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> MonitorExecutionResult[PersistedMonitorArtifact]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=lambda monitor: self._persist_monitor_analysis_artifact(
                monitor=monitor,
                document_repository=document_repository,
                artifact_store=artifact_store,
            ),
        )

    def execute_monitor_analysis_artifact_from_latest_source_data(
        self,
        *,
        monitor_id: str,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> MonitorExecutionResult[PersistedMonitorArtifact]:
        source_reader = MonitorSourceArtifactReader(
            document_repository=document_repository,
            artifact_store=artifact_store,
        )
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=lambda monitor: self._persist_monitor_analysis_artifact(
                monitor=monitor,
                document_repository=document_repository,
                artifact_store=artifact_store,
                source_data=source_reader.load_latest(monitor_id=monitor.id).source,
            ),
        )

    def execute_monitor_source_artifact(
        self,
        *,
        monitor_id: str,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> MonitorExecutionResult[PersistedMonitorArtifact]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=lambda monitor: self._persist_monitor_source_artifact(
                monitor=monitor,
                document_repository=document_repository,
                artifact_store=artifact_store,
            ),
        )

    def execute_monitor_source_to_analysis_artifacts(
        self,
        *,
        monitor_id: str,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> MonitorExecutionResult[PersistedMonitorSourceToAnalysisArtifacts]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=lambda monitor: self._persist_monitor_source_to_analysis_artifacts(
                monitor=monitor,
                document_repository=document_repository,
                artifact_store=artifact_store,
            ),
        )

    def execute_monitor_definition_artifact(
        self,
        *,
        monitor_id: str,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> MonitorExecutionResult[PersistedMonitorArtifact]:
        return self.execute_monitor(
            monitor_id=monitor_id,
            operation=lambda monitor: self._persist_monitor_definition_artifact(
                monitor=monitor,
                document_repository=document_repository,
                artifact_store=artifact_store,
            ),
        )

    def get_monitor(self, *, monitor_id: str) -> MonitorConfig:
        if self.workspace.monitors is None:
            raise ValueError("Workspace config does not define any monitors")
        for monitor in self.workspace.monitors.monitors:
            if monitor.id == monitor_id:
                return monitor
        raise KeyError(f"Unknown monitor_id: {monitor_id}")

    def _build_monitor_snapshot(self, monitor: MonitorConfig) -> MonitorSnapshot:
        return MonitorSnapshot(
            monitor_id=monitor.id,
            schedule=monitor.schedule,
            source_plugin=monitor.source.plugin,
            analysis_profiles=tuple(
                analysis.profile for analysis in (monitor.analyses or [])
            ),
        )

    def _build_monitor_analysis_plan(self, monitor: MonitorConfig) -> MonitorAnalysisPlan:
        configured_profiles = (
            self.workspace.analysis_profiles.analysis_profiles
            if self.workspace.analysis_profiles is not None
            else {}
        )
        analyses = tuple(
            self._build_monitor_analysis_plan_entry(
                profile_name=analysis.profile,
                profile=configured_profiles[analysis.profile],
            )
            for analysis in (monitor.analyses or [])
        )
        return MonitorAnalysisPlan(monitor_id=monitor.id, analyses=analyses)

    def _build_monitor_definition(self, monitor: MonitorConfig) -> MonitorDefinition:
        return MonitorDefinition(
            snapshot=self._build_monitor_snapshot(monitor),
            analysis_plan=self._build_monitor_analysis_plan(monitor),
        )

    def _build_monitor_analysis(
        self,
        monitor: MonitorConfig,
        *,
        source_data: MonitorSourceData | None = None,
    ) -> MonitorAnalysis:
        configured_profiles = (
            self.workspace.analysis_profiles.analysis_profiles
            if self.workspace.analysis_profiles is not None
            else {}
        )
        source_data = (
            self._build_monitor_source_data(monitor) if source_data is None else source_data
        )
        outputs = tuple(
            self._build_monitor_analysis_output_entry(
                monitor=monitor,
                profile_name=analysis.profile,
                profile=configured_profiles[analysis.profile],
                source_data=source_data,
            )
            for analysis in (monitor.analyses or [])
        )
        return MonitorAnalysis(monitor_id=monitor.id, outputs=outputs)

    def _build_monitor_notifications(
        self,
        monitor: MonitorConfig,
        *,
        analysis: MonitorAnalysis,
        source_data: MonitorSourceData | None = None,
    ) -> MonitorNotifications | None:
        if not monitor.outputs:
            return None
        if self.plugin_registry is None:
            raise ValueError(
                "MonitorExecutionService requires a plugin_registry for output delivery"
            )

        analysis_outputs = {
            output_entry.profile_name: output_entry for output_entry in analysis.outputs
        }
        deliveries = tuple(
            self._build_monitor_notification_delivery(
                monitor=monitor,
                output=output,
                analysis_output=analysis_outputs[output.profile],
                source_data=source_data,
            )
            for output in monitor.outputs
        )
        return MonitorNotifications(monitor_id=monitor.id, deliveries=deliveries)

    def _build_monitor_source_data(self, monitor: MonitorConfig) -> MonitorSourceData:
        if self.plugin_registry is None:
            raise ValueError(
                "MonitorExecutionService requires a plugin_registry for source execution"
            )

        plugin = self.plugin_registry.resolve_source_plugin(monitor.source.plugin)
        payload = plugin.fetch(monitor=monitor)
        return MonitorSourceData(
            monitor_id=monitor.id,
            source_plugin=monitor.source.plugin,
            records=tuple(_normalize_monitor_source_record(entry) for entry in payload),
        )

    def _build_monitor_execution_plan(self, monitor: MonitorConfig) -> MonitorExecutionPlan:
        definition = self._build_monitor_definition(monitor)
        configured_services = self.workspace.services.services
        analysis_bindings = tuple(
            self._build_monitor_execution_plan_binding(
                analysis=analysis,
                configured_profiles=self.workspace.analysis_profiles.analysis_profiles
                if self.workspace.analysis_profiles is not None
                else {},
                configured_services=configured_services,
            )
            for analysis in definition.analysis_plan.analyses
        )
        return MonitorExecutionPlan(
            definition=definition,
            analysis_bindings=analysis_bindings,
        )

    def _persist_monitor_snapshot_artifact(
        self,
        *,
        monitor: MonitorConfig,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> PersistedMonitorArtifact:
        snapshot = self._build_monitor_snapshot(monitor)
        document_id = f"{monitor.id}-snapshot"
        latest_document = document_repository.get_latest(document_id)
        document = document_repository.save(
            DocumentRecord(
                document_id=document_id,
                version=1 if latest_document is None else latest_document.version + 1,
            )
        )
        artifact = artifact_store.save(
            document_id=document.document_id,
            version=document.version,
            artifact_name="monitor_snapshot.json",
            content_type="application/json",
            data=json.dumps(asdict(snapshot), separators=(",", ":")).encode("utf-8"),
        )
        return PersistedMonitorArtifact(document=document, artifact=artifact)

    def _persist_monitor_execution_plan_artifact(
        self,
        *,
        monitor: MonitorConfig,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> PersistedMonitorArtifact:
        execution_plan = self._build_monitor_execution_plan(monitor)
        document_id = f"{monitor.id}-execution-plan"
        latest_document = document_repository.get_latest(document_id)
        document = document_repository.save(
            DocumentRecord(
                document_id=document_id,
                version=1 if latest_document is None else latest_document.version + 1,
            )
        )
        artifact = artifact_store.save(
            document_id=document.document_id,
            version=document.version,
            artifact_name="monitor_execution_plan.json",
            content_type="application/json",
            data=json.dumps(asdict(execution_plan), separators=(",", ":")).encode("utf-8"),
        )
        return PersistedMonitorArtifact(document=document, artifact=artifact)

    def _persist_monitor_analysis_plan_artifact(
        self,
        *,
        monitor: MonitorConfig,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> PersistedMonitorArtifact:
        analysis_plan = self._build_monitor_analysis_plan(monitor)
        document_id = f"{monitor.id}-analysis-plan"
        latest_document = document_repository.get_latest(document_id)
        document = document_repository.save(
            DocumentRecord(
                document_id=document_id,
                version=1 if latest_document is None else latest_document.version + 1,
            )
        )
        artifact = artifact_store.save(
            document_id=document.document_id,
            version=document.version,
            artifact_name="monitor_analysis_plan.json",
            content_type="application/json",
            data=json.dumps(asdict(analysis_plan), separators=(",", ":")).encode("utf-8"),
        )
        return PersistedMonitorArtifact(document=document, artifact=artifact)

    def _persist_monitor_analysis_artifact(
        self,
        *,
        monitor: MonitorConfig,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
        source_data: MonitorSourceData | None = None,
    ) -> PersistedMonitorArtifact:
        analysis = self._build_monitor_analysis(monitor, source_data=source_data)
        return self._persist_built_monitor_analysis_artifact(
            monitor=monitor,
            analysis=analysis,
            document_repository=document_repository,
            artifact_store=artifact_store,
        )

    def _persist_built_monitor_analysis_artifact(
        self,
        *,
        monitor: MonitorConfig,
        analysis: MonitorAnalysis,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> PersistedMonitorArtifact:
        document_id = f"{monitor.id}-analysis-output"
        latest_document = document_repository.get_latest(document_id)
        document = document_repository.save(
            DocumentRecord(
                document_id=document_id,
                version=1 if latest_document is None else latest_document.version + 1,
            )
        )
        artifact = artifact_store.save(
            document_id=document.document_id,
            version=document.version,
            artifact_name="monitor_analysis.json",
            content_type="application/json",
            data=json.dumps(asdict(analysis), separators=(",", ":")).encode("utf-8"),
        )
        return PersistedMonitorArtifact(document=document, artifact=artifact)

    def _persist_monitor_source_artifact(
        self,
        *,
        monitor: MonitorConfig,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> PersistedMonitorArtifact:
        persisted = self._persist_monitor_source_data_artifact(
            monitor=monitor,
            document_repository=document_repository,
            artifact_store=artifact_store,
        )
        return PersistedMonitorArtifact(
            document=persisted.document,
            artifact=persisted.artifact,
        )

    def _persist_monitor_source_data_artifact(
        self,
        *,
        monitor: MonitorConfig,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> PersistedMonitorSourceArtifact:
        source_data = self._build_monitor_source_data(monitor)
        document_id = f"{monitor.id}-source-data"
        latest_document = document_repository.get_latest(document_id)
        document = document_repository.save(
            DocumentRecord(
                document_id=document_id,
                version=1 if latest_document is None else latest_document.version + 1,
            )
        )
        artifact = artifact_store.save(
            document_id=document.document_id,
            version=document.version,
            artifact_name="monitor_source_data.json",
            content_type="application/json",
            data=json.dumps(asdict(source_data), separators=(",", ":")).encode("utf-8"),
        )
        return PersistedMonitorSourceArtifact(
            document=document,
            artifact=artifact,
            source=source_data,
        )

    def _persist_monitor_source_to_analysis_artifacts(
        self,
        *,
        monitor: MonitorConfig,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> PersistedMonitorSourceToAnalysisArtifacts:
        persisted_source = self._persist_monitor_source_data_artifact(
            monitor=monitor,
            document_repository=document_repository,
            artifact_store=artifact_store,
        )
        built_analysis = self._build_monitor_analysis(monitor, source_data=persisted_source.source)
        analysis_artifact = self._persist_built_monitor_analysis_artifact(
            monitor=monitor,
            analysis=built_analysis,
            document_repository=document_repository,
            artifact_store=artifact_store,
        )
        persisted_notifications = self._persist_monitor_notifications_artifact(
            monitor=monitor,
            document_repository=document_repository,
            artifact_store=artifact_store,
            analysis=built_analysis,
            source_data=persisted_source.source,
        )
        return PersistedMonitorSourceToAnalysisArtifacts(
            source=PersistedMonitorArtifact(
                document=persisted_source.document,
                artifact=persisted_source.artifact,
            ),
            analysis=analysis_artifact,
            notifications=persisted_notifications,
        )

    def _persist_monitor_definition_artifact(
        self,
        *,
        monitor: MonitorConfig,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
    ) -> PersistedMonitorArtifact:
        definition = self._build_monitor_definition(monitor)
        document_id = f"{monitor.id}-definition"
        latest_document = document_repository.get_latest(document_id)
        document = document_repository.save(
            DocumentRecord(
                document_id=document_id,
                version=1 if latest_document is None else latest_document.version + 1,
            )
        )
        artifact = artifact_store.save(
            document_id=document.document_id,
            version=document.version,
            artifact_name="monitor_definition.json",
            content_type="application/json",
            data=json.dumps(asdict(definition), separators=(",", ":")).encode("utf-8"),
        )
        return PersistedMonitorArtifact(document=document, artifact=artifact)

    def _build_monitor_analysis_plan_entry(
        self,
        *,
        profile_name: str,
        profile: AnalysisProfileConfig,
    ) -> MonitorAnalysisPlanEntry:
        if self.plugin_registry is not None:
            self.plugin_registry.resolve_analysis_plugin(profile.plugin)
        return MonitorAnalysisPlanEntry(
            profile_name=profile_name,
            plugin=profile.plugin,
            model_service=profile.model_service,
        )

    def _build_monitor_analysis_output_entry(
        self,
        *,
        monitor: MonitorConfig,
        profile_name: str,
        profile: AnalysisProfileConfig,
        source_data: MonitorSourceData | None = None,
    ) -> MonitorAnalysisOutputEntry:
        if self.plugin_registry is None:
            raise ValueError(
                "MonitorExecutionService requires a plugin_registry for analysis execution"
            )

        plugin = self.plugin_registry.resolve_analysis_plugin(profile.plugin)
        return MonitorAnalysisOutputEntry(
            profile_name=profile_name,
            plugin=profile.plugin,
            output=plugin.analyze(
                monitor=monitor,
                profile_name=profile_name,
                profile=profile,
                source_data=source_data,
            ),
        )

    def _build_monitor_notification_delivery(
        self,
        *,
        monitor: MonitorConfig,
        output: MonitorOutputConfig,
        analysis_output: MonitorAnalysisOutputEntry,
        source_data: MonitorSourceData | None = None,
    ) -> MonitorNotificationDelivery:
        if self.plugin_registry is None:
            raise ValueError(
                "MonitorExecutionService requires a plugin_registry for output delivery"
            )

        service = self.workspace.services.services[output.service]
        renderer = self.plugin_registry.resolve_renderer_plugin(output.renderer)
        payload = renderer.render(
            monitor=monitor,
            output=output,
            analysis_output=analysis_output,
            source_data=source_data,
        )
        notifier = self.plugin_registry.resolve_notifier_plugin(service.plugin)
        notifier.notify(
            monitor=monitor,
            service_name=output.service,
            service=service,
            payload=payload,
        )
        return MonitorNotificationDelivery(
            profile_name=output.profile,
            renderer=output.renderer,
            service_name=output.service,
            notifier_plugin=service.plugin,
            payload=payload,
        )

    def _persist_monitor_notifications_artifact(
        self,
        *,
        monitor: MonitorConfig,
        document_repository: DocumentRepository,
        artifact_store: ArtifactStore,
        analysis: MonitorAnalysis,
        source_data: MonitorSourceData | None = None,
    ) -> PersistedMonitorArtifact | None:
        notifications = self._build_monitor_notifications(
            monitor,
            analysis=analysis,
            source_data=source_data,
        )
        if notifications is None:
            return None

        document_id = f"{monitor.id}-notifications"
        latest_document = document_repository.get_latest(document_id)
        document = document_repository.save(
            DocumentRecord(
                document_id=document_id,
                version=1 if latest_document is None else latest_document.version + 1,
            )
        )
        artifact = artifact_store.save(
            document_id=document.document_id,
            version=document.version,
            artifact_name="monitor_notifications.json",
            content_type="application/json",
            data=json.dumps(asdict(notifications), separators=(",", ":")).encode("utf-8"),
        )
        return PersistedMonitorArtifact(document=document, artifact=artifact)

    def _build_monitor_execution_plan_binding(
        self,
        *,
        analysis: MonitorAnalysisPlanEntry,
        configured_profiles: dict[str, AnalysisProfileConfig],
        configured_services: dict[str, ServiceConfig],
    ) -> MonitorExecutionPlanBinding:
        profile = configured_profiles[analysis.profile_name]
        service = configured_services[profile.model_service]
        return MonitorExecutionPlanBinding(
            profile_name=analysis.profile_name,
            service_name=profile.model_service,
            service_plugin=service.plugin,
        )


def _deserialize_monitor_analysis(payload: bytes) -> MonitorAnalysis:
    raw = json.loads(payload)
    return MonitorAnalysis(
        monitor_id=raw["monitor_id"],
        outputs=tuple(
            MonitorAnalysisOutputEntry(
                profile_name=entry["profile_name"],
                plugin=entry["plugin"],
                output=entry["output"],
            )
            for entry in raw["outputs"]
        ),
    )


def _deserialize_monitor_source_data(payload: bytes) -> MonitorSourceData:
    raw = json.loads(payload)
    return MonitorSourceData(
        monitor_id=raw["monitor_id"],
        source_plugin=raw["source_plugin"],
        records=tuple(
            MonitorSourceRecord(
                source_id=entry["source_id"],
                content=entry["content"],
            )
            for entry in raw["records"]
        ),
    )


def _normalize_monitor_source_record(payload: object) -> MonitorSourceRecord:
    if not isinstance(payload, Mapping):
        raise TypeError("Monitor source payload entries must be mappings")

    source_id = payload.get("source_id")
    content = payload.get("content")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("Monitor source payload entries must define a non-blank source_id")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Monitor source payload entries must define non-blank content")

    return MonitorSourceRecord(source_id=source_id.strip(), content=content.strip())
