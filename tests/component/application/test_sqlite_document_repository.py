from pathlib import Path

from observer_rock.application.documents import DocumentRecord
from observer_rock.infrastructure.sqlite import SqliteDocumentRepository


def test_sqlite_document_repository_persists_and_reads_versioned_documents(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "documents.db"
    repository = SqliteDocumentRepository(database_path)

    first_version = repository.save(DocumentRecord(document_id="doc-001", version=1))
    latest_version = repository.save(DocumentRecord(document_id="doc-001", version=2))

    persisted = SqliteDocumentRepository(database_path)

    assert first_version == DocumentRecord(document_id="doc-001", version=1)
    assert latest_version == DocumentRecord(document_id="doc-001", version=2)
    assert persisted.get("doc-001", version=1) == first_version
    assert persisted.get("doc-001", version=3) is None
    assert persisted.get_latest("doc-001") == latest_version
    assert persisted.get_latest("missing-doc") is None
