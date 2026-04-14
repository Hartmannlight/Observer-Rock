from pathlib import Path

from observer_rock.__main__ import main


def test_query_documents_returns_matches_from_indexed_monitor_results(
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
    (workspace / "input").mkdir()
    (workspace / "input" / "feed.json").write_text(
        '[{"source_id":"meeting-2026-03-14","content":"Traffic update for main street"},'
        '{"source_id":"memo-2026-03-15","content":"Budget memo"}]',
        encoding="utf-8",
    )

    run_exit_code = main(
        [
            "run-monitor",
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
            "traffic",
        ]
    )

    captured = capsys.readouterr()

    assert run_exit_code == 0
    assert query_exit_code == 0
    assert "Document query profile=digest_v1 contains=traffic scope=latest matches=1" in captured.out
    assert "monitor=local-file-digest identity=meeting-2026-03-14 source_id=meeting-2026-03-14" in captured.out
    assert "document=local-file-digest:meeting-2026-03-14@v1" in captured.out
    assert "excerpt=Traffic update for main street" in captured.out


def test_query_documents_can_filter_to_one_monitor(
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
        "  - id: monitor-a\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: builtin_json_file\n"
        "      config:\n"
        "        path: input/a.json\n"
        "    analyses:\n"
        "      - profile: digest_v1\n"
        "  - id: monitor-b\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: builtin_json_file\n"
        "      config:\n"
        "        path: input/b.json\n"
        "    analyses:\n"
        "      - profile: digest_v1\n",
        encoding="utf-8",
    )
    (workspace / "input").mkdir()
    (workspace / "input" / "a.json").write_text(
        '[{"source_id":"item-a","content":"Traffic update A"}]',
        encoding="utf-8",
    )
    (workspace / "input" / "b.json").write_text(
        '[{"source_id":"item-b","content":"Traffic update B"}]',
        encoding="utf-8",
    )

    assert main(["run-monitor", "monitor-a", "--workspace", str(workspace)]) == 0
    assert main(["run-monitor", "monitor-b", "--workspace", str(workspace)]) == 0
    capsys.readouterr()

    query_exit_code = main(
        [
            "query-documents",
            "--workspace",
            str(workspace),
            "--profile",
            "digest_v1",
            "--contains",
            "traffic",
            "--monitor",
            "monitor-b",
        ]
    )

    captured = capsys.readouterr()

    assert query_exit_code == 0
    assert "Document query profile=digest_v1 contains=traffic monitor=monitor-b scope=latest matches=1" in captured.out
    assert "monitor=monitor-b" in captured.out
    assert "monitor=monitor-a" not in captured.out


def test_query_documents_returns_only_latest_version_by_default(
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

    query_exit_code = main(
        [
            "query-documents",
            "--workspace",
            str(workspace),
            "--profile",
            "digest_v1",
            "--contains",
            "traffic",
        ]
    )

    captured = capsys.readouterr()

    assert query_exit_code == 0
    assert "scope=latest matches=1" in captured.out
    assert "document=local-file-digest:meeting-2026-03-14@v2" in captured.out
    assert "excerpt=Traffic update v2" in captured.out
    assert "document=local-file-digest:meeting-2026-03-14@v1" not in captured.out


def test_query_documents_can_include_all_versions(
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

    query_exit_code = main(
        [
            "query-documents",
            "--workspace",
            str(workspace),
            "--profile",
            "digest_v1",
            "--contains",
            "traffic",
            "--all-versions",
        ]
    )

    captured = capsys.readouterr()

    assert query_exit_code == 0
    assert "scope=all_versions matches=2" in captured.out
    assert "document=local-file-digest:meeting-2026-03-14@v2" in captured.out
    assert "document=local-file-digest:meeting-2026-03-14@v1" in captured.out


def test_query_documents_reports_no_matches_cleanly(
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
            "query-documents",
            "--workspace",
            str(workspace),
            "--profile",
            "digest_v1",
            "--contains",
            "traffic",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "Document query profile=digest_v1 contains=traffic scope=latest matches=0\n"
    assert captured.err == ""
