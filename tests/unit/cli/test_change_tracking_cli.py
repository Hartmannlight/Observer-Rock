from pathlib import Path

from observer_rock.__main__ import main
from tests._helpers import _SourceAwareAnalysisPlugin


class _FetchContextRecordingSourcePlugin:
    def __init__(self) -> None:
        self.fetch_contexts: list[object | None] = []
        self.run_count = 0

    def fetch(self, *, monitor, fetch_context=None) -> object:
        self.run_count += 1
        self.fetch_contexts.append(fetch_context)
        return [
            {
                "source_id": f"doc-{self.run_count}",
                "content": f"content-{self.run_count}",
            }
        ]


def test_run_monitor_passes_rotating_change_tracking_fetch_context_to_source_plugins(
    tmp_path: Path,
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
        "    plugin: source_aware\n"
        "    model_service: local_model\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: tracked-monitor\n"
        "    schedule: '*/30 * * * *'\n"
        "    source:\n"
        "      plugin: tracked_source\n"
        "    change_tracking:\n"
        "      recheck_recent_documents: 3\n"
        "      recheck_budget_per_run: 1\n"
        "      recheck_every_n_runs: 2\n"
        "    analyses:\n"
        "      - profile: digest_v1\n",
        encoding="utf-8",
    )

    source_plugin = _FetchContextRecordingSourcePlugin()
    analysis_plugin = _SourceAwareAnalysisPlugin()

    assert (
        main(
            ["run-monitor", "tracked-monitor", "--workspace", str(workspace)],
            source_plugins={"tracked_source": source_plugin},
            analysis_plugins={"source_aware": analysis_plugin},
        )
        == 0
    )
    assert (
        main(
            ["run-monitor", "tracked-monitor", "--workspace", str(workspace)],
            source_plugins={"tracked_source": source_plugin},
            analysis_plugins={"source_aware": analysis_plugin},
        )
        == 0
    )
    assert (
        main(
            ["run-monitor", "tracked-monitor", "--workspace", str(workspace)],
            source_plugins={"tracked_source": source_plugin},
            analysis_plugins={"source_aware": analysis_plugin},
        )
        == 0
    )
    assert (
        main(
            ["run-monitor", "tracked-monitor", "--workspace", str(workspace)],
            source_plugins={"tracked_source": source_plugin},
            analysis_plugins={"source_aware": analysis_plugin},
        )
        == 0
    )

    first, second, third, fourth = source_plugin.fetch_contexts

    assert first is not None
    assert first.run_iteration == 1
    assert first.recheck_enabled is False
    assert first.recheck_document_ids == ()
    assert first.recent_documents == ()

    assert second is not None
    assert second.run_iteration == 2
    assert second.recheck_enabled is True
    assert second.recheck_document_ids == ("doc-1",)
    assert [entry.source_id for entry in second.recent_documents] == ["doc-1"]

    assert third is not None
    assert third.run_iteration == 3
    assert third.recheck_enabled is False
    assert third.recheck_document_ids == ()
    assert [entry.source_id for entry in third.recent_documents] == ["doc-2", "doc-1"]

    assert fourth is not None
    assert fourth.run_iteration == 4
    assert fourth.recheck_enabled is True
    assert fourth.recheck_document_ids == ("doc-2",)
    assert [entry.source_id for entry in fourth.recent_documents] == ["doc-3", "doc-2", "doc-1"]
