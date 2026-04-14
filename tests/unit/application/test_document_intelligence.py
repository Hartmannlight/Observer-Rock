from observer_rock.application.document_intelligence import (
    DocumentAnalysisRecord,
    DocumentIntelligenceIndexer,
    IndexedDocumentRecord,
    QueryableDocumentMatch,
)
from observer_rock.application.monitoring import (
    MonitorAnalysis,
    MonitorAnalysisOutputEntry,
    MonitorSourceData,
    MonitorSourceRecord,
)


class _InMemoryDocumentIntelligenceRepository:
    def __init__(self) -> None:
        self.documents: dict[tuple[str, str], IndexedDocumentRecord] = {}
        self.analyses: dict[tuple[str, int, str], DocumentAnalysisRecord] = {}

    def get_latest_document(
        self,
        *,
        monitor_id: str,
        identity_key: str,
    ) -> IndexedDocumentRecord | None:
        return self.documents.get((monitor_id, identity_key))

    def save_document(self, record: IndexedDocumentRecord) -> IndexedDocumentRecord:
        self.documents[(record.monitor_id, record.identity_key)] = record
        return record

    def save_analysis(self, record: DocumentAnalysisRecord) -> DocumentAnalysisRecord:
        self.analyses[(record.document_id, record.version, record.profile_name)] = record
        return record

    def query_documents(
        self,
        *,
        profile_name: str,
        contains_text: str,
        monitor_id: str | None = None,
    ) -> list[QueryableDocumentMatch]:
        normalized = contains_text.casefold()
        return [
            QueryableDocumentMatch(
                monitor_id=record.monitor_id,
                identity_key=record.identity_key,
                source_id=record.source_id,
                document_id=record.document_id,
                version=record.version,
                profile_name=record.profile_name,
                analysis_text=record.analysis_text,
                source_content=record.source_content,
                title=record.title,
            )
            for record in self.analyses.values()
            if record.profile_name == profile_name
            and (
                normalized in record.analysis_text.casefold()
                or normalized in record.output_json.casefold()
            )
            and (monitor_id is None or record.monitor_id == monitor_id)
        ]


def test_indexer_creates_document_records_and_analysis_matches_for_builtin_summary_shape() -> None:
    repository = _InMemoryDocumentIntelligenceRepository()
    indexer = DocumentIntelligenceIndexer(repository=repository)

    indexer.index_monitor_result(
        monitor_id="local-file-digest",
        source_data=MonitorSourceData(
            monitor_id="local-file-digest",
            source_plugin="builtin_json_file",
            records=(
                MonitorSourceRecord(source_id="item-001", content="first post"),
                MonitorSourceRecord(source_id="item-002", content="second post"),
            ),
        ),
        analysis=MonitorAnalysis(
            monitor_id="local-file-digest",
            outputs=(
                MonitorAnalysisOutputEntry(
                    profile_name="digest_v1",
                    plugin="builtin_summary",
                    output={
                        "items": [
                            {"source_id": "item-001", "summary": "first post"},
                            {"source_id": "item-002", "summary": "second post"},
                        ]
                    },
                ),
            ),
        ),
    )

    assert repository.documents[("local-file-digest", "item-001")] == IndexedDocumentRecord(
        document_id="local-file-digest:item-001",
        monitor_id="local-file-digest",
        identity_key="item-001",
        source_id="item-001",
        version=1,
        content_hash=repository.documents[("local-file-digest", "item-001")].content_hash,
        source_content="first post",
        title=None,
    )
    assert repository.analyses[
        ("local-file-digest:item-001", 1, "digest_v1")
    ] == DocumentAnalysisRecord(
        document_id="local-file-digest:item-001",
        monitor_id="local-file-digest",
        identity_key="item-001",
        source_id="item-001",
        version=1,
        profile_name="digest_v1",
        analysis_text="first post",
        output_json='{"source_id":"item-001","summary":"first post"}',
        source_content="first post",
        title=None,
    )


def test_indexer_increments_version_when_source_content_changes() -> None:
    repository = _InMemoryDocumentIntelligenceRepository()
    indexer = DocumentIntelligenceIndexer(repository=repository)

    first = indexer.index_monitor_result(
        monitor_id="local-file-digest",
        source_data=MonitorSourceData(
            monitor_id="local-file-digest",
            source_plugin="builtin_json_file",
            records=(MonitorSourceRecord(source_id="item-001", content="first post"),),
        ),
        analysis=MonitorAnalysis(
            monitor_id="local-file-digest",
            outputs=(
                MonitorAnalysisOutputEntry(
                    profile_name="digest_v1",
                    plugin="builtin_summary",
                    output={"items": [{"source_id": "item-001", "summary": "first post"}]},
                ),
            ),
        ),
    )
    second = indexer.index_monitor_result(
        monitor_id="local-file-digest",
        source_data=MonitorSourceData(
            monitor_id="local-file-digest",
            source_plugin="builtin_json_file",
            records=(MonitorSourceRecord(source_id="item-001", content="updated post"),),
        ),
        analysis=MonitorAnalysis(
            monitor_id="local-file-digest",
            outputs=(
                MonitorAnalysisOutputEntry(
                    profile_name="digest_v1",
                    plugin="builtin_summary",
                    output={"items": [{"source_id": "item-001", "summary": "updated post"}]},
                ),
            ),
        ),
    )

    assert first.documents[0].version == 1
    assert second.documents[0].version == 2
    assert (
        repository.analyses[("local-file-digest:item-001", 2, "digest_v1")].analysis_text
        == "updated post"
    )


def test_indexer_reuses_existing_version_when_source_content_is_unchanged() -> None:
    repository = _InMemoryDocumentIntelligenceRepository()
    indexer = DocumentIntelligenceIndexer(repository=repository)

    indexer.index_monitor_result(
        monitor_id="local-file-digest",
        source_data=MonitorSourceData(
            monitor_id="local-file-digest",
            source_plugin="builtin_json_file",
            records=(MonitorSourceRecord(source_id="item-001", content="first post"),),
        ),
        analysis=MonitorAnalysis(
            monitor_id="local-file-digest",
            outputs=(
                MonitorAnalysisOutputEntry(
                    profile_name="digest_v1",
                    plugin="builtin_summary",
                    output={"items": [{"source_id": "item-001", "summary": "first post"}]},
                ),
            ),
        ),
    )
    second = indexer.index_monitor_result(
        monitor_id="local-file-digest",
        source_data=MonitorSourceData(
            monitor_id="local-file-digest",
            source_plugin="builtin_json_file",
            records=(MonitorSourceRecord(source_id="item-001", content="first post"),),
        ),
        analysis=MonitorAnalysis(
            monitor_id="local-file-digest",
            outputs=(
                MonitorAnalysisOutputEntry(
                    profile_name="digest_v1",
                    plugin="builtin_summary",
                    output={"items": [{"source_id": "item-001", "summary": "first post"}]},
                ),
            ),
        ),
    )

    assert second.documents[0].version == 1


def test_indexer_uses_stable_document_identity_when_source_id_changes() -> None:
    repository = _InMemoryDocumentIntelligenceRepository()
    indexer = DocumentIntelligenceIndexer(repository=repository)

    first = indexer.index_monitor_result(
        monitor_id="local-file-digest",
        source_data=MonitorSourceData(
            monitor_id="local-file-digest",
            source_plugin="builtin_json_file",
            records=(
                MonitorSourceRecord(
                    source_id="feed-entry-001",
                    content="first protocol version",
                    document_identity="council/2026-03-14/protocol",
                    title="Council Protocol 2026-03-14",
                ),
            ),
        ),
        analysis=MonitorAnalysis(
            monitor_id="local-file-digest",
            outputs=(
                MonitorAnalysisOutputEntry(
                    profile_name="digest_v1",
                    plugin="builtin_summary",
                    output={
                        "items": [
                            {
                                "source_id": "feed-entry-001",
                                "summary": "first protocol version",
                            }
                        ]
                    },
                ),
            ),
        ),
    )
    second = indexer.index_monitor_result(
        monitor_id="local-file-digest",
        source_data=MonitorSourceData(
            monitor_id="local-file-digest",
            source_plugin="builtin_json_file",
            records=(
                MonitorSourceRecord(
                    source_id="feed-entry-009",
                    content="updated protocol version",
                    document_identity="council/2026-03-14/protocol",
                    title="Council Protocol 2026-03-14",
                ),
            ),
        ),
        analysis=MonitorAnalysis(
            monitor_id="local-file-digest",
            outputs=(
                MonitorAnalysisOutputEntry(
                    profile_name="digest_v1",
                    plugin="builtin_summary",
                    output={
                        "items": [
                            {
                                "source_id": "feed-entry-009",
                                "summary": "updated protocol version",
                            }
                        ]
                    },
                ),
            ),
        ),
    )

    assert first.documents[0].document_id == "local-file-digest:council-2026-03-14-protocol"
    assert second.documents[0].document_id == "local-file-digest:council-2026-03-14-protocol"
    assert second.documents[0].version == 2


def test_indexer_uses_title_as_identity_heuristic_when_explicit_identity_is_missing() -> None:
    repository = _InMemoryDocumentIntelligenceRepository()
    indexer = DocumentIntelligenceIndexer(repository=repository)

    first = indexer.index_monitor_result(
        monitor_id="local-file-digest",
        source_data=MonitorSourceData(
            monitor_id="local-file-digest",
            source_plugin="builtin_json_file",
            records=(
                MonitorSourceRecord(
                    source_id="feed-entry-001",
                    content="first protocol version",
                    document_identity=None,
                    title="Council Protocol 2026-03-14",
                ),
            ),
        ),
        analysis=MonitorAnalysis(
            monitor_id="local-file-digest",
            outputs=(
                MonitorAnalysisOutputEntry(
                    profile_name="digest_v1",
                    plugin="builtin_summary",
                    output={
                        "items": [
                            {
                                "source_id": "feed-entry-001",
                                "summary": "first protocol version",
                            }
                        ]
                    },
                ),
            ),
        ),
    )
    second = indexer.index_monitor_result(
        monitor_id="local-file-digest",
        source_data=MonitorSourceData(
            monitor_id="local-file-digest",
            source_plugin="builtin_json_file",
            records=(
                MonitorSourceRecord(
                    source_id="feed-entry-009",
                    content="updated protocol version",
                    document_identity=None,
                    title="Council Protocol 2026-03-14",
                ),
            ),
        ),
        analysis=MonitorAnalysis(
            monitor_id="local-file-digest",
            outputs=(
                MonitorAnalysisOutputEntry(
                    profile_name="digest_v1",
                    plugin="builtin_summary",
                    output={
                        "items": [
                            {
                                "source_id": "feed-entry-009",
                                "summary": "updated protocol version",
                            }
                        ]
                    },
                ),
            ),
        ),
    )

    assert first.documents[0].identity_key == "Council Protocol 2026-03-14"
    assert first.documents[0].document_id == "local-file-digest:council-protocol-2026-03-14"
    assert second.documents[0].document_id == "local-file-digest:council-protocol-2026-03-14"
    assert second.documents[0].version == 2


def test_indexer_projects_source_id_and_contents_shape_into_readable_analysis_text() -> None:
    repository = _InMemoryDocumentIntelligenceRepository()
    indexer = DocumentIntelligenceIndexer(repository=repository)

    indexer.index_monitor_result(
        monitor_id="local-file-digest",
        source_data=MonitorSourceData(
            monitor_id="local-file-digest",
            source_plugin="builtin_json_file",
            records=(MonitorSourceRecord(source_id="item-001", content="first post"),),
        ),
        analysis=MonitorAnalysis(
            monitor_id="local-file-digest",
            outputs=(
                MonitorAnalysisOutputEntry(
                    profile_name="digest_v1",
                    plugin="llm_extract",
                    output={
                        "source_ids": ["item-001"],
                        "contents": ["first post"],
                    },
                ),
            ),
        ),
    )

    assert repository.analyses[("local-file-digest:item-001", 1, "digest_v1")].analysis_text == (
        "first post"
    )
    assert repository.analyses[("local-file-digest:item-001", 1, "digest_v1")].output_json == (
        '{"source_id":"item-001","content":"first post"}'
    )
