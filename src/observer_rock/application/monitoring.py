import json
from dataclasses import asdict, dataclass
from typing import Callable, TypeVar

from observer_rock.application.artifacts import ArtifactRef, ArtifactStore
from observer_rock.application.documents import DocumentRecord, DocumentRepository
from observer_rock.application.services import RunExecutionResult, RunService
from observer_rock.config.models import AnalysisProfileConfig, MonitorConfig, ServiceConfig
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

    def _build_monitor_analysis(self, monitor: MonitorConfig) -> MonitorAnalysis:
        configured_profiles = (
            self.workspace.analysis_profiles.analysis_profiles
            if self.workspace.analysis_profiles is not None
            else {}
        )
        outputs = tuple(
            self._build_monitor_analysis_output_entry(
                monitor=monitor,
                profile_name=analysis.profile,
                profile=configured_profiles[analysis.profile],
            )
            for analysis in (monitor.analyses or [])
        )
        return MonitorAnalysis(monitor_id=monitor.id, outputs=outputs)

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
    ) -> PersistedMonitorArtifact:
        analysis = self._build_monitor_analysis(monitor)
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
            ),
        )

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
