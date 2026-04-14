from pathlib import Path

from observer_rock.__main__ import main


def test_init_workspace_onboarding_flow_e2e(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / "city-bulletin"

    init_exit_code = main(
        [
            "init-workspace",
            "--workspace",
            str(workspace),
        ]
    )
    init_output = capsys.readouterr()

    validate_exit_code = main(
        [
            "validate-workspace",
            "--workspace",
            str(workspace),
            "--tick",
            "2026-03-14T12:05:00+00:00",
        ]
    )
    validate_output = capsys.readouterr()

    list_exit_code = main(
        [
            "list-monitors",
            "--workspace",
            str(workspace),
            "--tick",
            "2026-03-14T12:05:00+00:00",
        ]
    )
    list_output = capsys.readouterr()

    run_exit_code = main(
        [
            "run-monitor",
            "city-bulletin-digest",
            "--workspace",
            str(workspace),
        ]
    )
    run_output = capsys.readouterr()

    assert init_exit_code == 0
    assert validate_exit_code == 0
    assert list_exit_code == 0
    assert run_exit_code == 0
    assert "Workspace initialized" in init_output.out
    assert "Workspace VALID" in validate_output.out
    assert "city-bulletin-digest DUE" in list_output.out
    assert "city-bulletin-digest COMPLETED" in run_output.out
    assert (workspace / "output" / "digest.txt").exists()
    digest_text = (workspace / "output" / "digest.txt").read_text(encoding="utf-8")
    assert "meeting-2026-03-14" in digest_text
    assert "memo-2026-03-15" in digest_text
