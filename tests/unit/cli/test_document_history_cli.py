from pathlib import Path

from observer_rock.__main__ import main


def test_document_history_shows_versions_and_latest_change(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  local_model:\n"
        "    plugin: noop_model\n",
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
        "      - profile: digest_v1\n",
        encoding="utf-8",
    )
    (workspace / "input").mkdir()
    feed_path = workspace / "input" / "feed.json"
    feed_path.write_text(
        '[{"source_id":"meeting-2026-03-14","content":"Traffic update v1"}]',
        encoding="utf-8",
    )

    assert main(["run-monitor", "local-file-digest", "--workspace", str(workspace)]) == 0
    feed_path.write_text(
        '[{"source_id":"meeting-2026-03-14","content":"Traffic update v2"}]',
        encoding="utf-8",
    )
    assert main(["run-monitor", "local-file-digest", "--workspace", str(workspace)]) == 0
    capsys.readouterr()

    exit_code = main(
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

    assert exit_code == 0
    assert (
        "Document history document=local-file-digest:meeting-2026-03-14 profile=digest_v1 versions=2"
        in captured.out
    )
    assert "version=2 monitor=local-file-digest identity=meeting-2026-03-14" in captured.out
    assert "version=1 monitor=local-file-digest identity=meeting-2026-03-14" in captured.out
    assert "excerpt=Traffic update v2" in captured.out
    assert "excerpt=Traffic update v1" in captured.out
    assert "comparison from=v1 to=v2 source_changed=true analysis_changed=true" in captured.out
    assert "source_diff=-Traffic update v1" in captured.out
    assert "source_diff=+Traffic update v2" in captured.out


def test_document_history_reports_initial_document_cleanly(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  local_model:\n"
        "    plugin: noop_model\n",
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
        "      - profile: digest_v1\n",
        encoding="utf-8",
    )
    (workspace / "input").mkdir()
    (workspace / "input" / "feed.json").write_text(
        '[{"source_id":"meeting-2026-03-14","content":"Traffic update v1"}]',
        encoding="utf-8",
    )

    assert main(["run-monitor", "local-file-digest", "--workspace", str(workspace)]) == 0
    capsys.readouterr()

    exit_code = main(
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

    assert exit_code == 0
    assert "versions=1" in captured.out
    assert "comparison status=INITIAL version_count=1" in captured.out


def test_document_history_reports_no_history_cleanly(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  local_model:\n"
        "    plugin: noop_model\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "document-history",
            "--workspace",
            str(workspace),
            "--document",
            "local-file-digest:missing",
            "--profile",
            "digest_v1",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        captured.out
        == "Document history document=local-file-digest:missing profile=digest_v1 versions=0\n"
    )
    assert captured.err == ""
