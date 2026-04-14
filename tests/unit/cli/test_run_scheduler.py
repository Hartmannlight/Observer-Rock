from datetime import UTC, datetime
from pathlib import Path

from observer_rock.__main__ import main
from observer_rock.cli import runtime as cli_runtime
from tests._helpers import _RecordingSourcePlugin, _SourceAwareAnalysisPlugin


class _ExplodingAnalysisPlugin:
    def __init__(self, *, fail_monitor_id: str, message: str) -> None:
        self.fail_monitor_id = fail_monitor_id
        self.message = message
        self.calls: list[tuple[str, str]] = []

    def analyze(self, *, monitor, profile_name, profile, source_data=None) -> object:
        self.calls.append((monitor.id, profile_name))
        if monitor.id == self.fail_monitor_id:
            raise RuntimeError(self.message)
        return {"monitor_id": monitor.id, "profile_name": profile_name}


def test_run_scheduler_executes_the_configured_monitor_once(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_strong:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  summary_v2:\n"
        "    plugin: llm_extract\n"
        "    model_service: openai_strong\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-123\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit_fetch\n"
        "    analyses:\n"
        "      - profile: summary_v2\n",
        encoding="utf-8",
    )

    source_plugin = _RecordingSourcePlugin(
        payload=[{"source_id": "item-001", "content": "first post"}]
    )
    analysis_plugin = _SourceAwareAnalysisPlugin()

    exit_code = main(
        [
            "run-scheduler",
            "--workspace",
            str(workspace),
            "--tick",
            "2026-03-14T12:05:00+00:00",
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "scheduler status=STARTED" in captured.out
    assert "tick=2026-03-14T12:05:00+00:00" in captured.out
    assert "run status=STARTED monitor=monitor-123" in captured.out
    assert "source status=COMPLETED document=monitor-123-source-data@v1" in captured.out
    assert "analysis status=COMPLETED document=monitor-123-analysis-output@v1" in captured.out
    assert "run status=COMPLETED monitor=monitor-123" in captured.out
    assert "Scheduler summary tick=2026-03-14T12:05:00+00:00 configured=1 due=1 skipped=0 completed=1 failed=0" in captured.out
    assert captured.err == ""
    assert source_plugin.calls == ["monitor-123"]
    assert analysis_plugin.calls == [("monitor-123", "summary_v2")]


def test_run_scheduler_exits_with_clear_error_when_workspace_defines_no_monitors(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path
    (workspace / "services.yml").write_text(
        "services:\n"
        "  primary:\n"
        "    plugin: slack\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "run-scheduler",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "Error: Workspace config does not define any monitors\n"


def test_run_scheduler_suppresses_success_output_when_any_monitor_runtime_fails(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_strong:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  summary_v2:\n"
        "    plugin: llm_extract\n"
        "    model_service: openai_strong\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-success\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit_fetch\n"
        "    analyses:\n"
        "      - profile: summary_v2\n"
        "  - id: monitor-failure\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit_fetch\n"
        "    analyses:\n"
        "      - profile: summary_v2\n",
        encoding="utf-8",
    )

    source_plugin = _RecordingSourcePlugin(
        payload=[{"source_id": "item-001", "content": "first post"}]
    )
    analysis_plugin = _ExplodingAnalysisPlugin(
        fail_monitor_id="monitor-failure",
        message="analysis exploded",
    )

    exit_code = main(
        [
            "run-scheduler",
            "--workspace",
            str(workspace),
            "--tick",
            "2026-03-14T12:05:00+00:00",
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "scheduler status=STARTED" in captured.out
    assert "run status=COMPLETED monitor=monitor-success" in captured.out
    assert "analysis status=FAILED target=summary_v2 attempts=1 error=analysis exploded" in captured.out
    assert "Scheduler summary tick=2026-03-14T12:05:00+00:00 configured=2 due=2 skipped=0 completed=1 failed=1" in captured.out
    assert captured.err == (
        "monitor-failure FAILED stage=analysis "
        "target=summary_v2 attempts=1: analysis exploded\n"
    )
    assert source_plugin.calls == ["monitor-success", "monitor-failure"]
    assert analysis_plugin.calls == [
        ("monitor-success", "summary_v2"),
        ("monitor-failure", "summary_v2"),
    ]


def test_run_scheduler_skips_monitor_when_schedule_is_not_due_for_current_tick(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_strong:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  summary_v2:\n"
        "    plugin: llm_extract\n"
        "    model_service: openai_strong\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-not-due\n"
        "    schedule: '0 0 * * *'\n"
        "    source:\n"
        "      plugin: reddit_fetch\n"
        "    analyses:\n"
        "      - profile: summary_v2\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cli_runtime,
        "_scheduler_now",
        lambda: datetime(2026, 3, 14, 12, 5, tzinfo=UTC),
        raising=False,
    )
    source_plugin = _RecordingSourcePlugin(
        payload=[{"source_id": "item-001", "content": "first post"}]
    )
    analysis_plugin = _SourceAwareAnalysisPlugin()

    exit_code = main(
        [
            "run-scheduler",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        captured.out
        == "scheduler status=STARTED "
        f"workspace={workspace} "
        "tick=2026-03-14T12:05:00+00:00 "
        "services=1 analysis_profiles=1 configured=1 due=0 skipped=1\n"
        "No monitors due at 2026-03-14T12:05:00+00:00 (1 configured)\n"
        "Scheduler summary tick=2026-03-14T12:05:00+00:00 configured=1 due=0 skipped=1 completed=0 failed=0\n"
    )
    assert captured.err == ""
    assert source_plugin.calls == []
    assert analysis_plugin.calls == []


def test_run_scheduler_skips_step_interval_monitor_on_non_matching_tick(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_strong:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  summary_v2:\n"
        "    plugin: llm_extract\n"
        "    model_service: openai_strong\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-step-interval\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit_fetch\n"
        "    analyses:\n"
        "      - profile: summary_v2\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cli_runtime,
        "_scheduler_now",
        lambda: datetime(2026, 3, 14, 12, 6, tzinfo=UTC),
        raising=False,
    )
    source_plugin = _RecordingSourcePlugin(
        payload=[{"source_id": "item-001", "content": "first post"}]
    )
    analysis_plugin = _SourceAwareAnalysisPlugin()

    exit_code = main(
        [
            "run-scheduler",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        captured.out
        == "scheduler status=STARTED "
        f"workspace={workspace} "
        "tick=2026-03-14T12:06:00+00:00 "
        "services=1 analysis_profiles=1 configured=1 due=0 skipped=1\n"
        "No monitors due at 2026-03-14T12:06:00+00:00 (1 configured)\n"
        "Scheduler summary tick=2026-03-14T12:06:00+00:00 configured=1 due=0 skipped=1 completed=0 failed=0\n"
    )
    assert captured.err == ""
    assert source_plugin.calls == []
    assert analysis_plugin.calls == []
