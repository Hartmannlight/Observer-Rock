from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    document_id: str
    version: int
    artifact_name: str
    content_type: str
    size_bytes: int
    path: Path

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id must not be blank")
        if self.version <= 0:
            raise ValueError("version must be greater than zero")
        if not self.artifact_name.strip():
            raise ValueError("artifact_name must not be blank")
        if not self.content_type.strip():
            raise ValueError("content_type must not be blank")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must not be negative")


@dataclass(frozen=True, slots=True)
class LoadedArtifact:
    artifact: ArtifactRef
    data: bytes


class ArtifactStore(Protocol):
    def save(
        self,
        *,
        document_id: str,
        version: int,
        artifact_name: str,
        content_type: str,
        data: bytes,
    ) -> ArtifactRef:
        """Persist one artifact and return typed metadata."""

    def load(
        self,
        *,
        document_id: str,
        version: int,
        artifact_name: str,
        content_type: str,
    ) -> LoadedArtifact:
        """Load one persisted artifact with metadata by document version and artifact name."""
