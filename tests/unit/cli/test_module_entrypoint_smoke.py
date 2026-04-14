from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_module_entrypoint_uses_cwd_as_default_workspace_and_invokes_run_monitor(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)

    recorded: dict[str, object] = {}

    def fake_run_monitor_command(
        *,
        workspace_root: Path,
        monitor_id: str,
        source_plugins: object | None = None,
        analysis_plugins: object | None = None,
        renderer_plugins: object | None = None,
        notifier_plugins: object | None = None,
    ) -> SimpleNamespace:
        recorded["workspace_root"] = workspace_root
        recorded["monitor_id"] = monitor_id
        recorded["source_plugins"] = source_plugins
        recorded["analysis_plugins"] = analysis_plugins
        recorded["renderer_plugins"] = renderer_plugins
        recorded["notifier_plugins"] = notifier_plugins
        return SimpleNamespace(
            workspace_root=workspace_root,
            state_root=workspace_root / ".observer_rock",
            service_count=0,
            analysis_profile_count=0,
            configured_monitor_count=1,
            execution=SimpleNamespace(
                monitor=SimpleNamespace(id=monitor_id),
                outcome=SimpleNamespace(name="COMPLETED"),
                error=None,
                run=SimpleNamespace(
                    run_id=f"{monitor_id}-run",
                    started_at=SimpleNamespace(isoformat=lambda: "2026-03-14T12:05:00+00:00"),
                    ended_at=SimpleNamespace(isoformat=lambda: "2026-03-14T12:05:01+00:00"),
                ),
                value=SimpleNamespace(
                    source=SimpleNamespace(
                        document=SimpleNamespace(
                            document_id=f"{monitor_id}-source-data",
                            version=1,
                        ),
                        artifact=SimpleNamespace(
                            path=workspace_root
                            / ".observer_rock"
                            / "artifacts"
                            / f"{monitor_id}-source-data"
                            / "v1"
                            / "monitor_source_data.json"
                        ),
                    ),
                    analysis=SimpleNamespace(
                        document=SimpleNamespace(
                            document_id=f"{monitor_id}-analysis-output",
                            version=1,
                        ),
                        artifact=SimpleNamespace(
                            path=workspace_root
                            / ".observer_rock"
                            / "artifacts"
                            / f"{monitor_id}-analysis-output"
                            / "v1"
                            / "monitor_analysis.json"
                        ),
                    ),
                    notifications=None,
                    source_attempts=1,
                    analysis_attempts=(),
                    notification_attempts=(),
                ),
            ),
        )

    monkeypatch.setattr("observer_rock.cli.run_monitor_command", fake_run_monitor_command)
    monkeypatch.setattr(sys, "argv", ["observer-rock", "run-monitor", "monitor-123"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("observer_rock.__main__", run_name="__main__")

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert recorded == {
        "workspace_root": workspace,
        "monitor_id": "monitor-123",
        "source_plugins": None,
        "analysis_plugins": None,
        "renderer_plugins": None,
        "notifier_plugins": None,
    }
    assert "workspace status=LOADED" in captured.out
    assert "run status=STARTED monitor=monitor-123 run_id=monitor-123-run" in captured.out
    assert "source status=COMPLETED document=monitor-123-source-data@v1" in captured.out
    assert "analysis status=COMPLETED document=monitor-123-analysis-output@v1" in captured.out
    assert "notifications status=SKIPPED reason=no_outputs" in captured.out
    assert "run status=COMPLETED monitor=monitor-123 run_id=monitor-123-run" in captured.out
    assert (
        "monitor-123 COMPLETED source=monitor-123-source-data@v1 "
        "analysis=monitor-123-analysis-output@v1 notifications=none"
    ) in captured.out
    assert captured.err == ""
