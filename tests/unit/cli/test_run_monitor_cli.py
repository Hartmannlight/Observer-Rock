from pathlib import Path

import pytest

from observer_rock.__main__ import main
from observer_rock.application.documents import DocumentRecord
from observer_rock.application.monitoring import (
    MonitorAnalysis,
    MonitorAnalysisArtifactReader,
    MonitorAnalysisOutputEntry,
    MonitorSourceArtifactReader,
    MonitorSourceData,
    MonitorSourceRecord,
)
from observer_rock.infrastructure.artifacts import FilesystemArtifactStore
from observer_rock.infrastructure.sqlite import SqliteDocumentRepository
from tests._helpers import _RecordingSourcePlugin, _SourceAwareAnalysisPlugin


class _ExplodingSourcePlugin:
    def __init__(self, message: str) -> None:
        self.message = message
        self.calls: list[str] = []

    def fetch(self, *, monitor) -> object:
        self.calls.append(monitor.id)
        raise RuntimeError(self.message)


class _ExplodingAnalysisPlugin:
    def __init__(self, message: str) -> None:
        self.message = message
        self.calls: list[tuple[str, str]] = []

    def analyze(self, *, monitor, profile_name, profile, source_data=None) -> object:
        self.calls.append((monitor.id, profile_name))
        raise RuntimeError(self.message)


class _FlakyAnalysisPlugin:
    def __init__(self, *, failures_before_success: int, success_output: object) -> None:
        self.failures_before_success = failures_before_success
        self.success_output = success_output
        self.calls: list[tuple[str, str]] = []

    def analyze(self, *, monitor, profile_name, profile, source_data=None) -> object:
        self.calls.append((monitor.id, profile_name))
        if len(self.calls) <= self.failures_before_success:
            raise RuntimeError(f"analysis exploded attempt {len(self.calls)}")
        return self.success_output


class _FlakyNotifierPlugin:
    def __init__(self, *, failures_before_success: int) -> None:
        self.failures_before_success = failures_before_success
        self.calls: list[tuple[str, str, str]] = []

    def notify(self, *, monitor, service_name, service, payload: str) -> object:
        self.calls.append((monitor.id, service_name, payload))
        if len(self.calls) <= self.failures_before_success:
            raise RuntimeError(f"notification exploded attempt {len(self.calls)}")
        return {"service_name": service_name, "payload": payload}


def test_cli_executes_named_monitor_happy_path_with_workspace_defaults(
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
            "run-monitor",
            "monitor-123",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    captured = capsys.readouterr()
    state_root = workspace / ".observer_rock"
    document_repository = SqliteDocumentRepository(state_root / "documents.db")
    artifact_store = FilesystemArtifactStore(state_root / "artifacts")
    source_reader = MonitorSourceArtifactReader(
        document_repository=document_repository,
        artifact_store=artifact_store,
    )
    analysis_reader = MonitorAnalysisArtifactReader(
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    assert exit_code == 0
    assert "monitor-123" in captured.out
    assert "COMPLETED" in captured.out
    assert (state_root / "runs.db").exists()
    assert (state_root / "documents.db").exists()
    assert document_repository.get_latest("monitor-123-source-data") == DocumentRecord(
        document_id="monitor-123-source-data",
        version=1,
    )
    assert document_repository.get_latest("monitor-123-analysis-output") == DocumentRecord(
        document_id="monitor-123-analysis-output",
        version=1,
    )
    assert source_reader.load_latest(monitor_id="monitor-123").source == MonitorSourceData(
        monitor_id="monitor-123",
        source_plugin="reddit_fetch",
        records=(MonitorSourceRecord(source_id="item-001", content="first post"),),
    )
    assert analysis_reader.load_latest(monitor_id="monitor-123").analysis == MonitorAnalysis(
        monitor_id="monitor-123",
        outputs=(
            MonitorAnalysisOutputEntry(
                profile_name="summary_v2",
                plugin="llm_extract",
                output={
                    "record_count": 1,
                    "source_ids": ["item-001"],
                    "contents": ["first post"],
                },
            ),
        ),
    )
    assert (
        state_root
        / "artifacts"
        / "monitor-123-source-data"
        / "v1"
        / "monitor_source_data.json"
    ).read_text(encoding="utf-8") == (
        '{"monitor_id":"monitor-123","source_plugin":"reddit_fetch","records":'
        '[{"source_id":"item-001","content":"first post"}]}'
    )
    assert (
        state_root
        / "artifacts"
        / "monitor-123-analysis-output"
        / "v1"
        / "monitor_analysis.json"
    ).read_text(encoding="utf-8") == (
        '{"monitor_id":"monitor-123","outputs":[{"profile_name":"summary_v2",'
        '"plugin":"llm_extract","output":{"record_count":1,"source_ids":["item-001"],'
        '"contents":["first post"]}}]}'
    )
    assert source_plugin.calls == ["monitor-123"]
    assert analysis_plugin.calls == [("monitor-123", "summary_v2")]


def test_cli_persists_v2_documents_on_second_run(
    tmp_path: Path,
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

    first_exit_code = main(
        [
            "run-monitor",
            "monitor-123",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )
    source_plugin.payload = [{"source_id": "item-002", "content": "second post"}]
    second_exit_code = main(
        [
            "run-monitor",
            "monitor-123",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    state_root = workspace / ".observer_rock"
    document_repository = SqliteDocumentRepository(state_root / "documents.db")
    artifact_store = FilesystemArtifactStore(state_root / "artifacts")
    source_reader = MonitorSourceArtifactReader(
        document_repository=document_repository,
        artifact_store=artifact_store,
    )
    analysis_reader = MonitorAnalysisArtifactReader(
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    assert first_exit_code == 0
    assert second_exit_code == 0
    assert document_repository.get("monitor-123-source-data", version=1) == DocumentRecord(
        document_id="monitor-123-source-data",
        version=1,
    )
    assert document_repository.get("monitor-123-source-data", version=2) == DocumentRecord(
        document_id="monitor-123-source-data",
        version=2,
    )
    assert document_repository.get("monitor-123-analysis-output", version=1) == DocumentRecord(
        document_id="monitor-123-analysis-output",
        version=1,
    )
    assert document_repository.get("monitor-123-analysis-output", version=2) == DocumentRecord(
        document_id="monitor-123-analysis-output",
        version=2,
    )
    assert source_reader.load_latest(monitor_id="monitor-123").document == DocumentRecord(
        document_id="monitor-123-source-data",
        version=2,
    )
    assert source_reader.load_latest(monitor_id="monitor-123").source == MonitorSourceData(
        monitor_id="monitor-123",
        source_plugin="reddit_fetch",
        records=(MonitorSourceRecord(source_id="item-002", content="second post"),),
    )
    assert analysis_reader.load_latest(monitor_id="monitor-123").document == DocumentRecord(
        document_id="monitor-123-analysis-output",
        version=2,
    )
    assert analysis_reader.load_latest(monitor_id="monitor-123").analysis == MonitorAnalysis(
        monitor_id="monitor-123",
        outputs=(
            MonitorAnalysisOutputEntry(
                profile_name="summary_v2",
                plugin="llm_extract",
                output={
                    "record_count": 1,
                    "source_ids": ["item-002"],
                    "contents": ["second post"],
                },
            ),
        ),
    )
    assert (
        state_root
        / "artifacts"
        / "monitor-123-source-data"
        / "v2"
        / "monitor_source_data.json"
    ).exists()
    assert (
        state_root
        / "artifacts"
        / "monitor-123-analysis-output"
        / "v2"
        / "monitor_analysis.json"
    ).exists()


def test_cli_loads_builtin_and_configured_plugins_before_monitor_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "external_analysis_plugin.py").write_text(
        "class ExternalAnalysisPlugin:\n"
        "    def analyze(self, *, monitor, profile_name, profile, source_data=None):\n"
        "        return {\n"
        "            'profile_name': profile_name,\n"
        "            'source_plugin': source_data.source_plugin,\n"
        "            'record_count': len(source_data.records),\n"
        "        }\n"
        "\n"
        "def register_plugins(registry):\n"
        "    registry.register_analysis_plugin('external_analysis', ExternalAnalysisPlugin())\n",
        encoding="utf-8",
    )
    (workspace / "services.yml").write_text(
        "plugin_import_paths:\n"
        "  - external_analysis_plugin\n"
        "services:\n"
        "  openai_strong:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  summary_v2:\n"
        "    plugin: external_analysis\n"
        "    model_service: openai_strong\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: builtin-monitor\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: builtin_echo\n"
        "    analyses:\n"
        "      - profile: summary_v2\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(workspace))

    exit_code = main(["run-monitor", "builtin-monitor", "--workspace", str(workspace)])

    captured = capsys.readouterr()
    artifact = (
        workspace
        / ".observer_rock"
        / "artifacts"
        / "builtin-monitor-analysis-output"
        / "v1"
        / "monitor_analysis.json"
    )

    assert exit_code == 0
    assert captured.err == ""
    assert (
        artifact.read_text(encoding="utf-8") == '{"monitor_id":"builtin-monitor","outputs":'
        '[{"profile_name":"summary_v2","plugin":"external_analysis","output":'
        '{"profile_name":"summary_v2","source_plugin":"builtin_echo","record_count":1}}]}'
    )


def test_cli_fails_for_source_plugin_runtime_error(
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
        "  - id: source-failure-monitor\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit_fetch\n"
        "    analyses:\n"
        "      - profile: summary_v2\n",
        encoding="utf-8",
    )

    source_plugin = _ExplodingSourcePlugin("source fetch exploded")
    analysis_plugin = _SourceAwareAnalysisPlugin()

    exit_code = main(
        [
            "run-monitor",
            "source-failure-monitor",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    captured = capsys.readouterr()
    state_root = workspace / ".observer_rock"

    assert exit_code == 1
    assert "workspace status=LOADED" in captured.out
    assert "run status=STARTED monitor=source-failure-monitor" in captured.out
    assert "source status=FAILED attempts=1 error=source fetch exploded" in captured.out
    assert "run status=FAILED monitor=source-failure-monitor" in captured.out
    assert (
        captured.err
        == "source-failure-monitor FAILED stage=source attempts=1: source fetch exploded\n"
    )
    assert (state_root / "runs.db").exists()
    assert (state_root / "documents.db").exists()
    assert not (
        state_root
        / "artifacts"
        / "source-failure-monitor-source-data"
        / "v1"
        / "monitor_source_data.json"
    ).exists()
    assert source_plugin.calls == ["source-failure-monitor"]
    assert analysis_plugin.calls == []


def test_cli_fails_for_analysis_plugin_runtime_error(
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
        "  - id: analysis-failure-monitor\n"
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
    analysis_plugin = _ExplodingAnalysisPlugin("analysis exploded")

    exit_code = main(
        [
            "run-monitor",
            "analysis-failure-monitor",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    captured = capsys.readouterr()
    state_root = workspace / ".observer_rock"

    assert exit_code == 1
    assert "workspace status=LOADED" in captured.out
    assert "run status=STARTED monitor=analysis-failure-monitor" in captured.out
    assert "source status=COMPLETED document=analysis-failure-monitor-source-data@v1" in captured.out
    assert "analysis status=FAILED target=summary_v2 attempts=1 error=analysis exploded" in captured.out
    assert "run status=FAILED monitor=analysis-failure-monitor" in captured.out
    assert (
        captured.err
        == "analysis-failure-monitor FAILED stage=analysis target=summary_v2 attempts=1: analysis exploded\n"
    )
    assert (state_root / "runs.db").exists()
    assert (state_root / "documents.db").exists()
    assert (
        state_root
        / "artifacts"
        / "analysis-failure-monitor-source-data"
        / "v1"
        / "monitor_source_data.json"
    ).read_text(encoding="utf-8") == (
        '{"monitor_id":"analysis-failure-monitor","source_plugin":"reddit_fetch",'
        '"records":[{"source_id":"item-001","content":"first post"}]}'
    )
    assert not (
        state_root
        / "artifacts"
        / "analysis-failure-monitor-analysis-output"
        / "v1"
        / "monitor_analysis.json"
    ).exists()
    assert source_plugin.calls == ["analysis-failure-monitor"]
    assert analysis_plugin.calls == [("analysis-failure-monitor", "summary_v2")]


def test_cli_reader_consistency_after_first_run_analysis_failure(
    tmp_path: Path,
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
        "  - id: first-analysis-failure-monitor\n"
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
    analysis_plugin = _ExplodingAnalysisPlugin("analysis exploded")

    exit_code = main(
        [
            "run-monitor",
            "first-analysis-failure-monitor",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    state_root = workspace / ".observer_rock"
    document_repository = SqliteDocumentRepository(state_root / "documents.db")
    artifact_store = FilesystemArtifactStore(state_root / "artifacts")
    source_reader = MonitorSourceArtifactReader(
        document_repository=document_repository,
        artifact_store=artifact_store,
    )
    analysis_reader = MonitorAnalysisArtifactReader(
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    assert exit_code == 1
    assert source_reader.load_latest(
        monitor_id="first-analysis-failure-monitor"
    ).document == DocumentRecord(
        document_id="first-analysis-failure-monitor-source-data",
        version=1,
    )
    assert source_reader.load_latest(
        monitor_id="first-analysis-failure-monitor"
    ).source == MonitorSourceData(
        monitor_id="first-analysis-failure-monitor",
        source_plugin="reddit_fetch",
        records=(MonitorSourceRecord(source_id="item-001", content="first post"),),
    )
    assert document_repository.get_latest(
        "first-analysis-failure-monitor-source-data"
    ) == DocumentRecord(
        document_id="first-analysis-failure-monitor-source-data",
        version=1,
    )
    assert document_repository.get_latest(
        "first-analysis-failure-monitor-analysis-output"
    ) is None
    with pytest.raises(
        KeyError,
        match="Unknown document_id: first-analysis-failure-monitor-analysis-output",
    ):
        analysis_reader.load_latest(monitor_id="first-analysis-failure-monitor")


def test_cli_reader_consistency_after_second_run_analysis_failure(
    tmp_path: Path,
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
        "  - id: partial-analysis-failure-monitor\n"
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
    first_analysis_plugin = _SourceAwareAnalysisPlugin()

    first_exit_code = main(
        [
            "run-monitor",
            "partial-analysis-failure-monitor",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": first_analysis_plugin},
    )

    source_plugin.payload = [{"source_id": "item-002", "content": "second post"}]
    failing_analysis_plugin = _ExplodingAnalysisPlugin("analysis exploded")

    second_exit_code = main(
        [
            "run-monitor",
            "partial-analysis-failure-monitor",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": failing_analysis_plugin},
    )

    state_root = workspace / ".observer_rock"
    document_repository = SqliteDocumentRepository(state_root / "documents.db")
    artifact_store = FilesystemArtifactStore(state_root / "artifacts")
    source_reader = MonitorSourceArtifactReader(
        document_repository=document_repository,
        artifact_store=artifact_store,
    )
    analysis_reader = MonitorAnalysisArtifactReader(
        document_repository=document_repository,
        artifact_store=artifact_store,
    )

    assert first_exit_code == 0
    assert second_exit_code == 1
    assert source_reader.load_latest(
        monitor_id="partial-analysis-failure-monitor"
    ).document == DocumentRecord(
        document_id="partial-analysis-failure-monitor-source-data",
        version=2,
    )
    assert source_reader.load_latest(
        monitor_id="partial-analysis-failure-monitor"
    ).source == MonitorSourceData(
        monitor_id="partial-analysis-failure-monitor",
        source_plugin="reddit_fetch",
        records=(MonitorSourceRecord(source_id="item-002", content="second post"),),
    )
    assert analysis_reader.load_latest(
        monitor_id="partial-analysis-failure-monitor"
    ).document == DocumentRecord(
        document_id="partial-analysis-failure-monitor-analysis-output",
        version=1,
    )
    assert analysis_reader.load_latest(
        monitor_id="partial-analysis-failure-monitor"
    ).analysis == MonitorAnalysis(
        monitor_id="partial-analysis-failure-monitor",
        outputs=(
            MonitorAnalysisOutputEntry(
                profile_name="summary_v2",
                plugin="llm_extract",
                output={
                    "record_count": 1,
                    "source_ids": ["item-001"],
                    "contents": ["first post"],
                },
            ),
        ),
    )
    assert document_repository.get_latest(
        "partial-analysis-failure-monitor-source-data"
    ) == DocumentRecord(
        document_id="partial-analysis-failure-monitor-source-data",
        version=2,
    )
    assert document_repository.get_latest(
        "partial-analysis-failure-monitor-analysis-output"
    ) == DocumentRecord(
        document_id="partial-analysis-failure-monitor-analysis-output",
        version=1,
    )
    assert not (
        state_root
        / "artifacts"
        / "partial-analysis-failure-monitor-analysis-output"
        / "v2"
        / "monitor_analysis.json"
    ).exists()


def test_cli_reader_missing_analysis_artifact_existing_document(
    tmp_path: Path,
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
        "  - id: missing-ana-artifact\n"
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
            "run-monitor",
            "missing-ana-artifact",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    state_root = workspace / ".observer_rock"
    artifact_path = (
        state_root
        / "artifacts"
        / "missing-ana-artifact-analysis-output"
        / "v1"
        / "monitor_analysis.json"
    )
    document_repository = SqliteDocumentRepository(state_root / "documents.db")
    analysis_reader = MonitorAnalysisArtifactReader(
        document_repository=document_repository,
        artifact_store=FilesystemArtifactStore(state_root / "artifacts"),
    )

    artifact_path.unlink()

    assert exit_code == 0
    assert document_repository.get_latest(
        "missing-ana-artifact-analysis-output"
    ) == DocumentRecord(
        document_id="missing-ana-artifact-analysis-output",
        version=1,
    )
    with pytest.raises(FileNotFoundError, match="monitor_analysis.json"):
        analysis_reader.load_latest(monitor_id="missing-ana-artifact")


def test_cli_retries_analysis_until_success_when_profile_allows_retries(
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
        "    model_service: openai_strong\n"
        "    retries: 2\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: retry-analysis-monitor\n"
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
    analysis_plugin = _FlakyAnalysisPlugin(
        failures_before_success=2,
        success_output={"record_count": 1, "source_ids": ["item-001"]},
    )

    exit_code = main(
        [
            "run-monitor",
            "retry-analysis-monitor",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "analysis attempts summary_v2=3" in captured.out
    assert "analysis status=COMPLETED document=retry-analysis-monitor-analysis-output@v1" in captured.out
    assert analysis_plugin.calls == [
        ("retry-analysis-monitor", "summary_v2"),
        ("retry-analysis-monitor", "summary_v2"),
        ("retry-analysis-monitor", "summary_v2"),
    ]


def test_cli_fails_analysis_after_retry_budget_is_exhausted(
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
        "    model_service: openai_strong\n"
        "    retries: 1\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: exhausted-analysis-monitor\n"
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
    analysis_plugin = _FlakyAnalysisPlugin(
        failures_before_success=2,
        success_output={"record_count": 1},
    )

    exit_code = main(
        [
            "run-monitor",
            "exhausted-analysis-monitor",
            "--workspace",
            str(workspace),
        ],
        source_plugins={"reddit_fetch": source_plugin},
        analysis_plugins={"llm_extract": analysis_plugin},
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "analysis status=FAILED target=summary_v2 attempts=2 error=analysis exploded attempt 2" in captured.out
    assert (
        captured.err
        == "exhausted-analysis-monitor FAILED stage=analysis target=summary_v2 attempts=2: analysis exploded attempt 2\n"
    )
    assert len(analysis_plugin.calls) == 2


def test_cli_retries_notifications_until_success_when_service_allows_retries(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  local_model:\n"
        "    plugin: noop_model\n"
        "  alerts:\n"
        "    plugin: flaky_notifier\n"
        "    retries: 1\n",
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
        "  - id: retry-notification-monitor\n"
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
        "        service: alerts\n",
        encoding="utf-8",
    )
    (workspace / "input").mkdir()
    (workspace / "input" / "feed.json").write_text(
        '[{"source_id":"item-001","content":"first post"}]',
        encoding="utf-8",
    )

    notifier_plugin = _FlakyNotifierPlugin(failures_before_success=1)

    exit_code = main(
        [
            "run-monitor",
            "retry-notification-monitor",
            "--workspace",
            str(workspace),
        ],
        notifier_plugins={"flaky_notifier": notifier_plugin},
    )

    captured = capsys.readouterr()

    assert exit_code == 0, f"stdout={captured.out!r} stderr={captured.err!r}"
    assert "notifications attempts digest_v1->alerts=2" in captured.out
    assert "notifications status=COMPLETED document=retry-notification-monitor-notifications@v1" in captured.out
    assert len(notifier_plugin.calls) == 2


def test_cli_fails_notifications_after_retry_budget_is_exhausted(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  local_model:\n"
        "    plugin: noop_model\n"
        "  alerts:\n"
        "    plugin: flaky_notifier\n"
        "    retries: 1\n",
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
        "  - id: exhausted-notification-monitor\n"
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
        "        service: alerts\n",
        encoding="utf-8",
    )
    (workspace / "input").mkdir()
    (workspace / "input" / "feed.json").write_text(
        '[{"source_id":"item-001","content":"first post"}]',
        encoding="utf-8",
    )

    notifier_plugin = _FlakyNotifierPlugin(failures_before_success=2)

    exit_code = main(
        [
            "run-monitor",
            "exhausted-notification-monitor",
            "--workspace",
            str(workspace),
        ],
        notifier_plugins={"flaky_notifier": notifier_plugin},
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "analysis status=COMPLETED document=exhausted-notification-monitor-analysis-output@v1" in captured.out
    assert "notifications status=FAILED target=digest_v1->alerts attempts=2 error=notification exploded attempt 2" in captured.out
    assert (
        captured.err
        == "exhausted-notification-monitor FAILED stage=notifications target=digest_v1->alerts attempts=2: notification exploded attempt 2\n"
    )
    assert len(notifier_plugin.calls) == 2
