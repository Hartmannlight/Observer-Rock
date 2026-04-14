from pathlib import Path

from observer_rock.__main__ import main


def test_indexed_file_source_discovers_new_documents_and_rechecks_recent_ones(
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
        "  - id: indexed-watch\n"
        "    schedule: '*/30 * * * *'\n"
        "    source:\n"
        "      plugin: builtin_indexed_file\n"
        "      config:\n"
        "        index_path: input/index.json\n"
        "        discovery_limit: 1\n"
        "    change_tracking:\n"
        "      recheck_recent_documents: 3\n"
        "      recheck_budget_per_run: 1\n"
        "      recheck_every_n_runs: 2\n"
        "    analyses:\n"
        "      - profile: digest_v1\n",
        encoding="utf-8",
    )
    (workspace / "input" / "documents").mkdir(parents=True)
    (workspace / "input" / "documents" / "meeting-2026-03-14.txt").write_text(
        "Traffic update v1",
        encoding="utf-8",
    )
    (workspace / "input" / "index.json").write_text(
        '[{"source_id":"meeting-2026-03-14","title":"Meeting 2026-03-14","path":"documents/meeting-2026-03-14.txt"}]',
        encoding="utf-8",
    )

    assert main(["run-monitor", "indexed-watch", "--workspace", str(workspace)]) == 0

    (workspace / "input" / "documents" / "meeting-2026-03-14.txt").write_text(
        "Traffic update v2",
        encoding="utf-8",
    )
    (workspace / "input" / "documents" / "memo-2026-03-15.txt").write_text(
        "Budget memo",
        encoding="utf-8",
    )
    (workspace / "input" / "index.json").write_text(
        "["  # newest-first discovery index
        '{"source_id":"memo-2026-03-15","title":"Memo 2026-03-15","path":"documents/memo-2026-03-15.txt"},'
        '{"source_id":"meeting-2026-03-14","title":"Meeting 2026-03-14","path":"documents/meeting-2026-03-14.txt"}'
        "]",
        encoding="utf-8",
    )

    assert main(["run-monitor", "indexed-watch", "--workspace", str(workspace)]) == 0
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
            "--all-versions",
        ]
    )
    history_exit_code = main(
        [
            "document-history",
            "--workspace",
            str(workspace),
            "--document",
            "indexed-watch:meeting-2026-03-14",
            "--profile",
            "digest_v1",
        ]
    )

    captured = capsys.readouterr()

    assert query_exit_code == 0
    assert history_exit_code == 0
    assert "scope=all_versions matches=2" in captured.out
    assert "document=indexed-watch:meeting-2026-03-14@v2" in captured.out
    assert "document=indexed-watch:meeting-2026-03-14@v1" in captured.out
    assert "Document history document=indexed-watch:meeting-2026-03-14 profile=digest_v1 versions=2" in captured.out
    assert "comparison from=v1 to=v2 source_changed=true analysis_changed=true" in captured.out
    assert "source_diff=-Traffic update v1" in captured.out
    assert "source_diff=+Traffic update v2" in captured.out
