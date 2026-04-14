from pathlib import Path

import pytest


def test_cli_package_exports_canonical_main_entrypoint() -> None:
    from observer_rock.__main__ import main as module_main
    from observer_rock.cli import main

    assert main is module_main


def test_run_monitor_exits_with_clear_error_for_unknown_monitor(
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
    (workspace / "monitors.yml").write_text(
        "monitors:\n"
        "  - id: known-monitor\n"
        "    schedule: daily\n"
        "    source:\n"
        "      plugin: rss\n",
        encoding="utf-8",
    )

    from observer_rock.cli import main

    exit_code = main(
        [
            "run-monitor",
            "missing-monitor",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "Error: unknown monitor 'missing-monitor'\n"


def test_run_monitor_exits_with_clear_error_for_invalid_plugin_import(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path
    (workspace / "services.yml").write_text(
        "plugin_import_paths:\n"
        "  - does_not_exist_plugin\n"
        "services:\n"
        "  primary:\n"
        "    plugin: slack\n",
        encoding="utf-8",
    )

    from observer_rock.cli import main

    exit_code = main(
        [
            "run-monitor",
            "any-monitor",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "Error: Could not import plugin module 'does_not_exist_plugin'\n"


def test_run_monitor_exits_with_clear_error_for_plugin_module_runtime_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    workspace = tmp_path
    (workspace / "broken_plugin.py").write_text(
        "raise RuntimeError('boom during import')\n",
        encoding="utf-8",
    )
    (workspace / "services.yml").write_text(
        "plugin_import_paths:\n"
        "  - broken_plugin\n"
        "services:\n"
        "  primary:\n"
        "    plugin: slack\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(workspace))

    from observer_rock.cli import main

    exit_code = main(
        [
            "run-monitor",
            "any-monitor",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == (
        "Error: Plugin module 'broken_plugin' failed during import: "
        "boom during import\n"
    )


def test_run_monitor_exits_with_clear_error_for_plugin_registration_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    workspace = tmp_path
    (workspace / "broken_plugin.py").write_text(
        "def register_plugins(registry):\n"
        "    raise RuntimeError('boom during registration')\n",
        encoding="utf-8",
    )
    (workspace / "services.yml").write_text(
        "plugin_import_paths:\n"
        "  - broken_plugin\n"
        "services:\n"
        "  primary:\n"
        "    plugin: slack\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(workspace))

    from observer_rock.cli import main

    exit_code = main(
        [
            "run-monitor",
            "any-monitor",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == (
        "Error: Plugin module 'broken_plugin' failed while registering plugins: "
        "boom during registration\n"
    )


def test_run_monitor_exits_with_clear_error_for_missing_workspace_config(
    tmp_path: Path,
    capsys,
) -> None:
    workspace = tmp_path

    from observer_rock.cli import main

    exit_code = main(
        [
            "run-monitor",
            "any-monitor",
            "--workspace",
            str(workspace),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == (
        f"Error: Workspace config is missing required services.yml: "
        f"{workspace / 'services.yml'}\n"
    )
