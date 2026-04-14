import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any
from typing import Protocol, runtime_checkable

from observer_rock.application.monitoring import MonitorAnalysis, MonitorSourceData, MonitorSourceRecord


@dataclass(frozen=True, slots=True)
class IndexedDocumentRecord:
    document_id: str
    monitor_id: str
    identity_key: str
    source_id: str
    version: int
    content_hash: str
    source_content: str
    title: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentAnalysisRecord:
    document_id: str
    monitor_id: str
    identity_key: str
    source_id: str
    version: int
    profile_name: str
    analysis_text: str
    output_json: str
    source_content: str
    title: str | None = None


@dataclass(frozen=True, slots=True)
class QueryableDocumentMatch:
    monitor_id: str
    identity_key: str
    source_id: str
    document_id: str
    version: int
    profile_name: str
    analysis_text: str
    source_content: str
    title: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentHistoryEntry:
    document_id: str
    monitor_id: str
    identity_key: str
    source_id: str
    version: int
    profile_name: str
    analysis_text: str
    source_content: str
    title: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentIntelligenceIndexResult:
    documents: tuple[IndexedDocumentRecord, ...]
    analyses: tuple[DocumentAnalysisRecord, ...]


@runtime_checkable
class DocumentIntelligenceRepository(Protocol):
    def get_latest_document(
        self,
        *,
        monitor_id: str,
        identity_key: str,
    ) -> IndexedDocumentRecord | None:
        """Return the latest indexed version for one monitor source record."""

    def save_document(self, record: IndexedDocumentRecord) -> IndexedDocumentRecord:
        """Persist one indexed document version."""

    def save_analysis(self, record: DocumentAnalysisRecord) -> DocumentAnalysisRecord:
        """Persist one queryable document analysis projection."""

    def query_documents(
        self,
        *,
        profile_name: str,
        contains_text: str,
        monitor_id: str | None = None,
        latest_only: bool = True,
    ) -> list[QueryableDocumentMatch]:
        """Return document matches for one profile and text filter."""

    def get_document_history(
        self,
        *,
        document_id: str,
        profile_name: str,
    ) -> list[DocumentHistoryEntry]:
        """Return versioned analysis history for one document and profile."""


@dataclass(frozen=True, slots=True)
class DocumentIntelligenceIndexer:
    repository: DocumentIntelligenceRepository

    def index_monitor_result(
        self,
        *,
        monitor_id: str,
        source_data: MonitorSourceData,
        analysis: MonitorAnalysis,
    ) -> DocumentIntelligenceIndexResult:
        indexed_documents = tuple(
            self._index_source_record(
                monitor_id=monitor_id,
                source_record=record,
            )
            for record in source_data.records
        )
        indexed_document_by_source_id = {
            record.source_id: record for record in indexed_documents
        }
        indexed_analyses: list[DocumentAnalysisRecord] = []
        for output in analysis.outputs:
            for source_id, analysis_projection in _project_analysis_output_by_source_id(output.output).items():
                indexed_document = indexed_document_by_source_id.get(source_id)
                if indexed_document is None:
                    continue
                indexed_analyses.append(
                    self.repository.save_analysis(
                        DocumentAnalysisRecord(
                            document_id=indexed_document.document_id,
                            monitor_id=indexed_document.monitor_id,
                            identity_key=indexed_document.identity_key,
                            source_id=indexed_document.source_id,
                            version=indexed_document.version,
                            profile_name=output.profile_name,
                            analysis_text=analysis_projection.analysis_text,
                            output_json=analysis_projection.output_json,
                            source_content=indexed_document.source_content,
                            title=indexed_document.title,
                        )
                    )
                )
        return DocumentIntelligenceIndexResult(
            documents=indexed_documents,
            analyses=tuple(indexed_analyses),
        )

    def _index_source_record(
        self,
        *,
        monitor_id: str,
        source_record: MonitorSourceRecord,
    ) -> IndexedDocumentRecord:
        identity_key = _resolve_identity_key(source_record)
        document_id = f"{monitor_id}:{_slugify_identity_key(identity_key)}"
        content_hash = hashlib.sha256(source_record.content.encode("utf-8")).hexdigest()
        latest = self.repository.get_latest_document(
            monitor_id=monitor_id,
            identity_key=identity_key,
        )
        version = 1
        if latest is not None:
            version = latest.version if latest.content_hash == content_hash else latest.version + 1
        return self.repository.save_document(
            IndexedDocumentRecord(
                document_id=document_id,
                monitor_id=monitor_id,
                identity_key=identity_key,
                source_id=source_record.source_id,
                version=version,
                content_hash=content_hash,
                source_content=source_record.content,
                title=source_record.title,
            )
        )


def _slugify_identity_key(value: str) -> str:
    collapsed = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return collapsed or "document"


def _resolve_identity_key(source_record: MonitorSourceRecord) -> str:
    if source_record.document_identity is not None:
        return source_record.document_identity
    if source_record.title is not None:
        return source_record.title
    return source_record.source_id


@dataclass(frozen=True, slots=True)
class _ProjectedAnalysis:
    analysis_text: str
    output_json: str


def _project_analysis_output_by_source_id(output: object) -> dict[str, _ProjectedAnalysis]:
    if not isinstance(output, dict):
        return {}

    items = output.get("items")
    if isinstance(items, list):
        projected_items: dict[str, _ProjectedAnalysis] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            source_id = item.get("source_id")
            if not isinstance(source_id, str) or not source_id.strip():
                continue
            projected_items[source_id] = _ProjectedAnalysis(
                analysis_text=_render_analysis_text(item),
                output_json=json.dumps(item, separators=(",", ":")),
            )
        if projected_items:
            return projected_items

    source_ids = output.get("source_ids")
    contents = output.get("contents")
    if isinstance(source_ids, list) and isinstance(contents, list):
        projected_pairs: dict[str, _ProjectedAnalysis] = {}
        for source_id, content in zip(source_ids, contents, strict=False):
            if not isinstance(source_id, str) or not isinstance(content, str):
                continue
            projected_pairs[source_id] = _ProjectedAnalysis(
                analysis_text=content.strip(),
                output_json=json.dumps(
                    {"source_id": source_id, "content": content},
                    separators=(",", ":"),
                ),
            )
        if projected_pairs:
            return projected_pairs

    return {}


def _render_analysis_text(item: dict[str, Any]) -> str:
    preferred_fields = ("summary", "content", "excerpt", "title")
    for field_name in preferred_fields:
        value = item.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()

    scalar_fields: list[str] = []
    for key, value in item.items():
        if key == "source_id":
            continue
        rendered = _render_scalar_value(value)
        if rendered is None:
            continue
        scalar_fields.append(f"{key}={rendered}")

    if scalar_fields:
        return "; ".join(scalar_fields)
    return json.dumps(item, separators=(",", ":"))


def _render_scalar_value(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return None
