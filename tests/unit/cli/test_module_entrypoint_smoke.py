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
            state_root=workspace_root / ".observer_rock",
            execution=SimpleNamespace(
                monitor=SimpleNamespace(id=monitor_id),
                outcome=SimpleNamespace(name="COMPLETED"),
                error=None,
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
    assert captured.out == f"monitor-123 COMPLETED {workspace / '.observer_rock' / 'artifacts'}\n"
    assert captured.err == ""
