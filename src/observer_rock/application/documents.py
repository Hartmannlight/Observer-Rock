from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    document_id: str
    version: int

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id must not be blank")
        if self.version <= 0:
            raise ValueError("version must be greater than zero")


@runtime_checkable
class DocumentRepository(Protocol):
    def save(self, document: DocumentRecord) -> DocumentRecord:
        """Persist a document version."""

    def get(self, document_id: str, *, version: int) -> DocumentRecord | None:
        """Return a specific document version, if present."""

    def get_latest(self, document_id: str) -> DocumentRecord | None:
        """Return the latest known version for a document, if present."""
