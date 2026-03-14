from pathlib import Path

from observer_rock.application.artifacts import ArtifactRef, LoadedArtifact


class FilesystemArtifactStore:
    def __init__(self, root_directory: Path) -> None:
        self._root_directory = root_directory

    def save(
        self,
        *,
        document_id: str,
        version: int,
        artifact_name: str,
        content_type: str,
        data: bytes,
    ) -> ArtifactRef:
        artifact_path = self._root_directory / document_id / f"v{version}" / artifact_name
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(data)
        return ArtifactRef(
            document_id=document_id,
            version=version,
            artifact_name=artifact_name,
            content_type=content_type,
            size_bytes=len(data),
            path=artifact_path,
        )

    def load(
        self,
        *,
        document_id: str,
        version: int,
        artifact_name: str,
        content_type: str,
    ) -> LoadedArtifact:
        artifact_path = self._root_directory / document_id / f"v{version}" / artifact_name
        data = artifact_path.read_bytes()
        return LoadedArtifact(
            artifact=ArtifactRef(
                document_id=document_id,
                version=version,
                artifact_name=artifact_name,
                content_type=content_type,
                size_bytes=len(data),
                path=artifact_path,
            ),
            data=data,
        )
