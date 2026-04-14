from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest


def test_module_entrypoint_executes_monitor_with_real_workspace_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "workspace_plugins.py").write_text(
        "class WorkspaceAnalysisPlugin:\n"
        "    def analyze(self, *, monitor, profile_name, profile, source_data=None):\n"
        "        records = list(source_data.records)\n"
        "        return {\n"
        "            'profile_name': profile_name,\n"
        "            'record_count': len(records),\n"
        "            'first_source_id': records[0].source_id,\n"
        "        }\n"
        "\n"
        "def register_plugins(registry):\n"
        "    registry.register_analysis_plugin('workspace_analysis', WorkspaceAnalysisPlugin())\n",
        encoding="utf-8",
    )
    (workspace / "services.yml").write_text(
        "plugin_import_paths:\n"
        "  - workspace_plugins\n"
        "services:\n"
        "  openai_strong:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  summary_v2:\n"
        "    plugin: workspace_analysis\n"
        "    model_service: openai_strong\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-123\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: builtin_echo\n"
        "    analyses:\n"
        "      - profile: summary_v2\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace)
    monkeypatch.setattr(sys, "argv", ["observer-rock", "run-monitor", "monitor-123"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("observer_rock.__main__", run_name="__main__")

    captured = capsys.readouterr()
    artifact = (
        workspace
        / ".observer_rock"
        / "artifacts"
        / "monitor-123-analysis-output"
        / "v1"
        / "monitor_analysis.json"
    )

    assert exc_info.value.code == 0
    assert captured.err == ""
    assert captured.out == f"monitor-123 COMPLETED {workspace / '.observer_rock' / 'artifacts'}\n"
    assert (
        artifact.read_text(encoding="utf-8") == '{"monitor_id":"monitor-123","outputs":'
        '[{"profile_name":"summary_v2","plugin":"workspace_analysis","output":'
        '{"profile_name":"summary_v2","record_count":1,'
        '"first_source_id":"monitor-123-builtin"}}]}'
    )
