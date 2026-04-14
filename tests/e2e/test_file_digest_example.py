from pathlib import Path
import shutil

from observer_rock.__main__ import main


def test_file_digest_example_e2e(tmp_path: Path, capsys) -> None:
    example_root = Path(__file__).resolve().parents[2] / "examples" / "file_digest"
    workspace = tmp_path / "file_digest"
    shutil.copytree(example_root, workspace)

    exit_code = main(
        [
            "run-monitor",
            "local-file-digest",
            "--workspace",
            str(workspace),
        ]
    )
    inspect_exit_code = main(
        [
            "inspect-artifacts",
            "local-file-digest",
            "--workspace",
            str(workspace),
        ]
    )
    query_exit_code = main(
        [
            "query-documents",
            "--workspace",
            str(workspace),
            "--profile",
            "digest_v1",
            "--contains",
            "meeting-2026-03-14",
        ]
    )
    history_exit_code = main(
        [
            "document-history",
            "--workspace",
            str(workspace),
            "--document",
            "local-file-digest:meeting-2026-03-14",
            "--profile",
            "digest_v1",
        ]
    )

    captured = capsys.readouterr()
    output_path = workspace / "output" / "digest.txt"
    notification_artifact = (
        workspace
        / ".observer_rock"
        / "artifacts"
        / "local-file-digest-notifications"
        / "v1"
        / "monitor_notifications.json"
    )

    assert exit_code == 0
    assert inspect_exit_code == 0
    assert query_exit_code == 0
    assert history_exit_code == 0
    assert "local-file-digest" in captured.out
    assert "Artifact inspection monitor=local-file-digest" in captured.out
    assert "source status=AVAILABLE document=local-file-digest-source-data@v1" in captured.out
    assert "analysis status=AVAILABLE document=local-file-digest-analysis-output@v1" in captured.out
    assert "notifications status=AVAILABLE document=local-file-digest-notifications@v1" in captured.out
    assert "Document query profile=digest_v1 contains=meeting-2026-03-14 scope=latest matches=1" in captured.out
    assert "document=local-file-digest:meeting-2026-03-14@v1" in captured.out
    assert "Document history document=local-file-digest:meeting-2026-03-14 profile=digest_v1 versions=1" in captured.out
    assert output_path.exists()
    assert "meeting-2026-03-14" in output_path.read_text(encoding="utf-8")
    assert "memo-2026-03-15" in output_path.read_text(encoding="utf-8")
    assert notification_artifact.exists()
