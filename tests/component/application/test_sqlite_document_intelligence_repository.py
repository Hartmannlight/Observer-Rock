from pathlib import Path

from observer_rock.application.document_intelligence import (
    DocumentAnalysisRecord,
    IndexedDocumentRecord,
)
from observer_rock.infrastructure.sqlite import SqliteDocumentIntelligenceRepository


def test_sqlite_document_intelligence_repository_persists_and_queries_matches(
    tmp_path: Path,
) -> None:
    repository = SqliteDocumentIntelligenceRepository(tmp_path / "documents.db")

    repository.save_document(
        IndexedDocumentRecord(
            document_id="local-file-digest:item-001",
            monitor_id="local-file-digest",
            identity_key="item-001",
            source_id="item-001",
            version=1,
            content_hash="hash-1",
            source_content="first post",
            title=None,
        )
    )
    repository.save_analysis(
        DocumentAnalysisRecord(
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
    )

    latest = repository.get_latest_document(
        monitor_id="local-file-digest",
        identity_key="item-001",
    )
    matches = repository.query_documents(
        profile_name="digest_v1",
        contains_text="first",
    )

    assert latest == IndexedDocumentRecord(
        document_id="local-file-digest:item-001",
        monitor_id="local-file-digest",
        identity_key="item-001",
        source_id="item-001",
        version=1,
        content_hash="hash-1",
        source_content="first post",
        title=None,
    )
    assert len(matches) == 1
    assert matches[0].document_id == "local-file-digest:item-001"
    assert matches[0].profile_name == "digest_v1"
    assert matches[0].analysis_text == "first post"


def test_sqlite_document_intelligence_repository_returns_document_history_in_latest_first_order(
    tmp_path: Path,
) -> None:
    repository = SqliteDocumentIntelligenceRepository(tmp_path / "documents.db")

    repository.save_analysis(
        DocumentAnalysisRecord(
            document_id="local-file-digest:item-001",
            monitor_id="local-file-digest",
            identity_key="item-001",
            source_id="item-001",
            version=1,
            profile_name="digest_v1",
            analysis_text="first post",
            output_json='{"source_id":"item-001","summary":"first post"}',
            source_content="first post",
            title="Item 001",
        )
    )
    repository.save_analysis(
        DocumentAnalysisRecord(
            document_id="local-file-digest:item-001",
            monitor_id="local-file-digest",
            identity_key="item-001",
            source_id="item-002",
            version=2,
            profile_name="digest_v1",
            analysis_text="updated post",
            output_json='{"source_id":"item-002","summary":"updated post"}',
            source_content="updated post",
            title="Item 001",
        )
    )

    history = repository.get_document_history(
        document_id="local-file-digest:item-001",
        profile_name="digest_v1",
    )

    assert [entry.version for entry in history] == [2, 1]
    assert history[0].analysis_text == "updated post"
    assert history[0].source_id == "item-002"
    assert history[1].analysis_text == "first post"
