from pathlib import Path

from observer_rock.__main__ import main
from tests._helpers import _RecordingSourcePlugin, _SourceAwareAnalysisPlugin


class _ExplodingAnalysisPlugin:
    def __init__(self, message: str) -> None:
        self.message = message

    def analyze(self, *, monitor, profile_name, profile, source_data=None) -> object:
        raise RuntimeError(self.message)


def test_inspect_artifacts_shows_latest_source_analysis_and_notifications(
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
        "  - id: inspectable-monitor\n"
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
        '[{"source_id":"item-001","content":"first post"}]',
        encoding="utf-8",
    )

    run_exit_code = main(
        [
            "run-monitor",
            "inspectable-monitor",
            "--workspace",
            str(workspace),
        ]
    )
    inspect_exit_code = main(
        [
            "inspect-artifacts",
            "inspectable-monitor",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert run_exit_code == 0
    assert inspect_exit_code == 0
    assert "Artifact inspection monitor=inspectable-monitor" in captured.out
    assert (
        "source status=AVAILABLE document=inspectable-monitor-source-data@v1"
        in captured.out
    )
    assert '"source_id":"item-001"' in captured.out
    assert (
        "analysis status=AVAILABLE document=inspectable-monitor-analysis-output@v1"
        in captured.out
    )
    assert '"summary":"first post"' in captured.out
    assert (
        "notifications status=AVAILABLE "
        "document=inspectable-monitor-notifications@v1"
    ) in captured.out
    assert '"service_name":"local_output"' in captured.out
    assert captured.err == ""


def test_inspect_artifacts_reports_missing_downstream_artifacts_after_analysis_failure(
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
        "  - id: partially-persisted-monitor\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit_fetch\n"
        "    analyses:\n"
        "      - profile: summary_v2\n",
        encoding="utf-8",
    )

    run_exit_code = main(
        [
            "run-monitor",
            "partially-persisted-monitor",
            "--workspace",
            str(workspace),
        ],
        source_plugins={
            "reddit_fetch": _RecordingSourcePlugin(
                payload=[{"source_id": "item-001", "content": "first post"}]
            )
        },
        analysis_plugins={"llm_extract": _ExplodingAnalysisPlugin("analysis exploded")},
    )
    inspect_exit_code = main(
        [
            "inspect-artifacts",
            "partially-persisted-monitor",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert run_exit_code == 1
    assert inspect_exit_code == 0
    assert (
        "source status=AVAILABLE document=partially-persisted-monitor-source-data@v1"
        in captured.out
    )
    assert "analysis status=MISSING reason=no persisted artifact" in captured.out
    assert "notifications status=MISSING reason=no persisted artifact" in captured.out
    assert captured.err == "partially-persisted-monitor FAILED stage=analysis target=summary_v2 attempts=1: analysis exploded\n"


def test_inspect_artifacts_fails_when_latest_artifact_file_is_missing(
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
        "  - id: broken-analysis-monitor\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit_fetch\n"
        "    analyses:\n"
        "      - profile: summary_v2\n",
        encoding="utf-8",
    )

    run_exit_code = main(
        [
            "run-monitor",
            "broken-analysis-monitor",
            "--workspace",
            str(workspace),
        ],
        source_plugins={
            "reddit_fetch": _RecordingSourcePlugin(
                payload=[{"source_id": "item-001", "content": "first post"}]
            )
        },
        analysis_plugins={"llm_extract": _SourceAwareAnalysisPlugin()},
    )
    broken_artifact = (
        workspace
        / ".observer_rock"
        / "artifacts"
        / "broken-analysis-monitor-analysis-output"
        / "v1"
        / "monitor_analysis.json"
    )
    broken_artifact.unlink()

    inspect_exit_code = main(
        [
            "inspect-artifacts",
            "broken-analysis-monitor",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert run_exit_code == 0
    assert inspect_exit_code == 1
    assert (
        "analysis status=BROKEN document=broken-analysis-monitor-analysis-output@v1"
        in captured.out
    )
    assert "reason=" in captured.out
    assert "monitor_analysis.json" in captured.out
