from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_python_module_run_monitor_executes_successfully_in_subprocess(
    tmp_path: Path,
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

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    artifact = (
        workspace
        / ".observer_rock"
        / "artifacts"
        / "monitor-123-analysis-output"
        / "v1"
        / "monitor_analysis.json"
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout == f"monitor-123 COMPLETED {workspace / '.observer_rock' / 'artifacts'}\n"
    assert (
        artifact.read_text(encoding="utf-8") == '{"monitor_id":"monitor-123","outputs":'
        '[{"profile_name":"summary_v2","plugin":"workspace_analysis","output":'
        '{"profile_name":"summary_v2","record_count":1,'
        '"first_source_id":"monitor-123-builtin"}}]}'
    )


def test_python_module_run_monitor_exits_with_clear_error_for_invalid_services_yml_syntax(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services: [\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "any-monitor"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr.startswith("Error: Invalid YAML in services config")
    assert "services.yml" in completed.stderr


def test_python_module_run_monitor_exits_with_clear_error_for_services_root_type_error(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "- services:\n"
        "    openai_strong:\n"
        "      plugin: openai\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "Error: services config must contain a mapping at the document root\n"


def test_python_module_run_monitor_exits_with_clear_error_for_invalid_analysis_profiles_yml_syntax(
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
        "analysis_profiles: [\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr.startswith("Error: Invalid YAML in analysis profiles config")
    assert "analysis_profiles.yml" in completed.stderr


def test_python_module_run_monitor_exits_with_clear_error_for_analysis_profiles_root_type_error(
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
        "- analysis_profiles:\n"
        "    summary_v2:\n"
        "      plugin: llm_extract\n"
        "      model_service: openai_strong\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert (
        completed.stderr
        == "Error: analysis profiles config must contain a mapping at the document root\n"
    )


def test_python_module_run_monitor_exits_with_clear_error_for_invalid_monitors_yml_syntax(
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
    (workspace / "monitors.yml").write_text(
        "monitors: [\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr.startswith("Error: Invalid YAML in monitors config")
    assert "monitors.yml" in completed.stderr


def test_python_module_run_monitor_exits_with_clear_error_for_monitors_root_type_error(
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
    (workspace / "monitors.yml").write_text(
        "- monitors:\n"
        "  - id: monitor-123\n"
        "    schedule: daily\n"
        "    source:\n"
        "      plugin: builtin_echo\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "Error: monitors config must contain a mapping at the document root\n"


def test_python_module_run_monitor_reports_workspace_plugin_import_failure_in_subprocess(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "broken_plugin.py").write_text(
        "raise RuntimeError('boom during import')\n",
        encoding="utf-8",
    )
    (workspace / "services.yml").write_text(
        "plugin_import_paths:\n"
        "  - broken_plugin\n"
        "services:\n"
        "  openai_strong:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "Error: Plugin module 'broken_plugin' failed during import: "
        "boom during import\n"
    )


def test_python_module_run_monitor_reports_missing_callable_register_plugins_in_subprocess(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "invalid_plugin.py").write_text(
        "PLUGIN_NAME = 'invalid'\n",
        encoding="utf-8",
    )
    (workspace / "services.yml").write_text(
        "plugin_import_paths:\n"
        "  - invalid_plugin\n"
        "services:\n"
        "  openai_strong:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "Error: Plugin module 'invalid_plugin' must define a callable register_plugins\n"
    )


def test_python_module_run_monitor_reports_unknown_monitor_in_subprocess(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  primary:\n"
        "    plugin: slack\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: known-monitor\n"
        "    schedule: daily\n"
        "    source:\n"
        "      plugin: rss\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "missing-monitor"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "Error: unknown monitor 'missing-monitor'\n"


def test_python_module_run_monitor_reports_missing_services_file_in_subprocess(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        f"Error: Workspace config is missing required services.yml: "
        f"{workspace / 'services.yml'}\n"
    )


def test_python_module_run_monitor_reports_missing_model_service_reference_in_analysis_profiles(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  discord_alerts:\n"
        "    plugin: discord\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  street_mentions_v1:\n"
        "    plugin: llm_extract\n"
        "    model_service: openai_fast\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-123\n"
        "    schedule: daily\n"
        "    source:\n"
        "      plugin: builtin_echo\n"
        "    analyses:\n"
        "      - profile: street_mentions_v1\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "Error: Analysis profile 'street_mentions_v1' in analysis_profiles.yml "
        "references missing service 'openai_fast'\n"
    )


def test_python_module_run_monitor_reports_missing_analysis_profile_reference_in_monitors(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_fast:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  sentiment:\n"
        "    plugin: llm_extract\n"
        "    model_service: openai_fast\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: reddit-wallstreetbets\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit\n"
        "    analyses:\n"
        "      - profile: urgency\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "reddit-wallstreetbets"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "Error: Monitor 'reddit-wallstreetbets' references missing analysis profile "
        "'urgency'\n"
    )


def test_python_module_run_monitor_reports_workspace_wide_missing_analysis_profile_reference_in_other_monitor(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_fast:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  sentiment:\n"
        "    plugin: llm_extract\n"
        "    model_service: openai_fast\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-123\n"
        "    schedule: daily\n"
        "    source:\n"
        "      plugin: builtin_echo\n"
        "  - id: reddit-wallstreetbets\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit\n"
        "    analyses:\n"
        "      - profile: urgency\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "Error: Monitor 'reddit-wallstreetbets' references missing analysis profile "
        "'urgency'\n"
    )


def test_python_module_run_monitor_reports_workspace_wide_duplicate_analysis_profiles_in_other_monitor(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_fast:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "analysis_profiles.yml").write_text(
        "analysis_profiles:\n"
        "  sentiment:\n"
        "    plugin: llm_extract\n"
        "    model_service: openai_fast\n"
        "  urgency:\n"
        "    plugin: llm_extract\n"
        "    model_service: openai_fast\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-123\n"
        "    schedule: daily\n"
        "    source:\n"
        "      plugin: builtin_echo\n"
        "    analyses:\n"
        "      - profile: sentiment\n"
        "  - id: reddit-wallstreetbets\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit\n"
        "    analyses:\n"
        "      - profile: urgency\n"
        "      - profile: urgency\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr.startswith("Error: 1 validation error for MonitorsConfig\n")
    assert "monitors.1" in completed.stderr
    assert "duplicate analysis profile: urgency" in completed.stderr


def test_python_module_run_monitor_reports_workspace_wide_duplicate_monitor_id_in_other_monitor(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_fast:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-123\n"
        "    schedule: daily\n"
        "    source:\n"
        "      plugin: builtin_echo\n"
        "  - id: monitor-123\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr.startswith("Error: 1 validation error for MonitorsConfig\n")
    assert "monitors" in completed.stderr
    assert "duplicate monitor id: monitor-123" in completed.stderr


def test_python_module_run_monitor_reports_workspace_wide_blank_source_plugin_in_other_monitor(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_fast:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-123\n"
        "    schedule: daily\n"
        "    source:\n"
        "      plugin: builtin_echo\n"
        "  - id: reddit-wallstreetbets\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: ''\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr.startswith("Error: 1 validation error for MonitorsConfig\n")
    assert "monitors.1.source.plugin" in completed.stderr
    assert "String should have at least 1 character" in completed.stderr


def test_python_module_run_monitor_reports_workspace_wide_missing_service_reference_in_analysis_profiles(
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
        "    model_service: openai_strong\n"
        "  enrichment_v1:\n"
        "    plugin: llm_extract\n"
        "    model_service: openai_fast\n",
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

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "Error: Analysis profile 'enrichment_v1' in analysis_profiles.yml "
        "references missing service 'openai_fast'\n"
    )


def test_python_module_run_monitor_reports_missing_analysis_profiles_file_required_by_other_monitor(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_fast:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: monitor-123\n"
        "    schedule: daily\n"
        "    source:\n"
        "      plugin: builtin_echo\n"
        "  - id: reddit-wallstreetbets\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit\n"
        "    analyses:\n"
        "      - profile: urgency\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "monitor-123"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "Error: Workspace config requires analysis_profiles.yml "
        "when monitors declare analyses: "
        f"{workspace / 'analysis_profiles.yml'}\n"
    )


def test_python_module_run_monitor_reports_missing_analysis_profiles_file_for_monitor_analyses(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "services.yml").write_text(
        "services:\n"
        "  openai_fast:\n"
        "    plugin: openai\n",
        encoding="utf-8",
    )
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: reddit-wallstreetbets\n"
        "    schedule: '*/5 * * * *'\n"
        "    source:\n"
        "      plugin: reddit\n"
        "    analyses:\n"
        "      - profile: urgency\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "observer_rock", "run-monitor", "reddit-wallstreetbets"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == (
        "Error: Workspace config requires analysis_profiles.yml "
        "when monitors declare analyses: "
        f"{workspace / 'analysis_profiles.yml'}\n"
    )
