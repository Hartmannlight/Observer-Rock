import pytest

from observer_rock.application.documents import DocumentRecord, DocumentRepository


def test_document_record_rejects_blank_ids_and_non_positive_versions() -> None:
    with pytest.raises(ValueError, match="document_id must not be blank"):
        DocumentRecord(document_id="", version=1)

    with pytest.raises(ValueError, match="version must be greater than zero"):
        DocumentRecord(document_id="doc-001", version=0)


def test_document_repository_protocol_supports_versioned_document_lookups() -> None:
    class StubDocumentRepository:
        def save(self, document: DocumentRecord) -> DocumentRecord:
            return document

        def get(
            self, document_id: str, *, version: int
        ) -> DocumentRecord | None:
            return None

        def get_latest(self, document_id: str) -> DocumentRecord | None:
            return None

    assert isinstance(StubDocumentRepository(), DocumentRepository)
