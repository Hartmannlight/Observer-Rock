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
    assert "local-file-digest" in captured.out
    assert output_path.exists()
    assert "meeting-2026-03-14" in output_path.read_text(encoding="utf-8")
    assert "memo-2026-03-15" in output_path.read_text(encoding="utf-8")
    assert notification_artifact.exists()
