from pathlib import Path

from observer_rock.__main__ import main


def test_init_workspace_creates_a_runnable_starter_workspace(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "starter-workspace"

    exit_code = main(
        [
            "init-workspace",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == (
        f"Workspace initialized root={workspace.resolve()} monitor_id=starter-workspace-digest\n"
        "Next steps:\n"
        f"  python -m observer_rock validate-workspace --workspace {workspace.resolve()}\n"
        f"  python -m observer_rock list-monitors --workspace {workspace.resolve()}\n"
        "  python -m observer_rock run-monitor "
        f"starter-workspace-digest --workspace {workspace.resolve()}\n"
    )
    assert (workspace / "services.yml").exists()
    assert (workspace / "analysis_profiles.yml").exists()
    assert (workspace / "monitors.yml").exists()
    assert (workspace / "input" / "feed.json").exists()
    assert (workspace / "README.md").exists()
    assert "starter-workspace-digest" in (workspace / "monitors.yml").read_text(
        encoding="utf-8"
    )


def test_init_workspace_rejects_non_empty_target_directory(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "starter-workspace"
    workspace.mkdir()
    (workspace / "existing.txt").write_text("keep me", encoding="utf-8")

    exit_code = main(
        [
            "init-workspace",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == (
        f"Error: Workspace path must be empty before initialization: {workspace.resolve()}\n"
    )
