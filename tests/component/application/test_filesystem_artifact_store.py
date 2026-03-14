from pathlib import Path

from observer_rock.infrastructure.artifacts import FilesystemArtifactStore


def test_filesystem_artifact_store_saves_artifact_and_returns_metadata(
    tmp_path: Path,
) -> None:
    store = FilesystemArtifactStore(tmp_path / "artifacts")

    artifact = store.save(
        document_id="doc-001",
        version=1,
        artifact_name="source.txt",
        content_type="text/plain",
        data=b"hello world\n",
    )

    assert artifact.document_id == "doc-001"
    assert artifact.version == 1
    assert artifact.artifact_name == "source.txt"
    assert artifact.content_type == "text/plain"
    assert artifact.size_bytes == 12
    assert artifact.path == tmp_path / "artifacts" / "doc-001" / "v1" / "source.txt"
    assert artifact.path.read_bytes() == b"hello world\n"
