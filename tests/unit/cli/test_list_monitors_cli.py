from datetime import UTC, datetime
from pathlib import Path

from observer_rock.__main__ import main


def test_list_monitors_reports_due_and_not_due_monitors_with_operator_fields(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  local_model:\n"
        "    plugin: noop_model\n"
        "  local_output:\n"
        "    plugin: file_notifier\n"
        "    path: output/digest.txt\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  digest_v1:\n"
        "    plugin: builtin_summary\n"
        "    model_service: local_model\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: due-monitor\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: builtin_json_file\n"
        "      config:\n"
        "        path: input/feed.json\n"
        "    analyses:\n"
        "      - profile: digest_v1\n"
        "    outputs:\n"
        "      - profile: digest_v1\n"
        "        renderer: builtin_digest\n"
        "        service: local_output\n"
        "  - id: nightly-monitor\n"
        "    schedule: '0 0 * * *'\n"
        "    source:\n"
        "      plugin: builtin_echo\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "list-monitors",
            "--workspace",
            str(workspace),
            "--tick",
            "2026-03-14T12:05:00+00:00",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert (
        captured.out
        == "Configured monitors (2) at 2026-03-14T12:05:00+00:00\n"
        "due-monitor DUE schedule='*/5 * * * *' source=builtin_json_file analyses=digest_v1 outputs=digest_v1->builtin_digest->local_output\n"
        "nightly-monitor NOT_DUE schedule='0 0 * * *' source=builtin_echo analyses=none outputs=none\n"
    )


def test_list_monitors_uses_current_tick_when_not_provided(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  primary:\n"
        "    plugin: noop_model\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-123\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: builtin_echo\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "observer_rock.cli.runtime._scheduler_now",
        lambda: datetime(2026, 3, 14, 12, 10, tzinfo=UTC),
    )

    exit_code = main(
        [
            "list-monitors",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert (
        captured.out
        == "Configured monitors (1) at 2026-03-14T12:10:00+00:00\n"
        "monitor-123 DUE schedule='*/5 * * * *' source=builtin_echo analyses=none outputs=none\n"
    )


def test_list_monitors_exits_with_clear_error_when_workspace_defines_no_monitors(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  primary:\n"
        "    plugin: noop_model\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "list-monitors",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "Error: Workspace config does not define any monitors\n"
