from datetime import UTC, datetime
from pathlib import Path

from observer_rock.__main__ import main


def test_validate_workspace_reports_resolved_paths_and_config_summary(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("DISCORD_TOKEN", "secret-token")
    (workspace / "services.yml").write_text(
        "plugin_import_paths:\n"
        "  - workspace_plugins\n"
        "services:\n"
        "  local_model:\n"
        "    plugin: noop_model\n"
        "  discord_alerts:\n"
        "    plugin: discord\n"
        "    token_env: DISCORD_TOKEN\n"
        "    channel_id: '12345'\n"
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
        "  - id: local-file-digest\n"
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
        "        service: local_output\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "validate-workspace",
            "--workspace",
            str(workspace),
            "--tick",
            "2026-03-14T12:05:00+00:00",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == (
        f"Workspace VALID root={workspace.resolve()} tick=2026-03-14T12:05:00+00:00\n"
        "Summary plugin_imports=1 services=3 analysis_profiles=1 monitors=1\n"
        "plugin-import workspace_plugins\n"
        "service local_model plugin=noop_model token_source=none path=none\n"
        "service discord_alerts plugin=discord token_source=env:DISCORD_TOKEN path=none\n"
        f"service local_output plugin=file_notifier token_source=none path={(workspace / 'output' / 'digest.txt').resolve()}\n"
        "analysis-profile digest_v1 plugin=builtin_summary model_service=local_model\n"
        f"monitor local-file-digest due=DUE schedule='*/5 * * * *' source=builtin_json_file source_path={(workspace / 'input' / 'feed.json').resolve()} analyses=digest_v1 outputs=digest_v1->builtin_digest->local_output\n"
    )


def test_validate_workspace_uses_current_tick_when_not_provided(
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
        "    schedule: '0 0 * * *'\n"
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
            "validate-workspace",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert (
        captured.out
        == f"Workspace VALID root={workspace.resolve()} tick=2026-03-14T12:10:00+00:00\n"
        "Summary plugin_imports=0 services=1 analysis_profiles=0 monitors=1\n"
        "service primary plugin=noop_model token_source=none path=none\n"
        "monitor monitor-123 due=NOT_DUE schedule='0 0 * * *' source=builtin_echo source_path=none analyses=none outputs=none\n"
    )


def test_validate_workspace_exits_with_clear_error_for_missing_required_secret(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  discord_alerts:\n"
        "    plugin: discord\n"
        "    token_env: DISCORD_TOKEN\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "validate-workspace",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "Error: missing required environment variable: DISCORD_TOKEN\n"
