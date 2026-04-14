import pytest


def test_plugin_registry_registers_and_resolves_analysis_plugins_by_name() -> None:
    from observer_rock.plugins.registry import PluginRegistry

    plugin = object()
    registry = PluginRegistry()

    registry.register_analysis_plugin("sentiment_v1", plugin)

    assert registry.resolve_analysis_plugin("sentiment_v1") is plugin


def test_plugin_registry_rejects_unknown_analysis_plugins_by_name() -> None:
    from observer_rock.plugins.registry import PluginRegistry

    registry = PluginRegistry()

    with pytest.raises(KeyError) as exc_info:
        registry.resolve_analysis_plugin("sentiment_v1")

    assert exc_info.value.args[0] == "Unknown analysis plugin: sentiment_v1"


def test_plugin_registry_loads_external_plugins_from_configured_import_paths(
    tmp_path,
    monkeypatch,
) -> None:
    from observer_rock.config.models import MonitorConfig, MonitorSourceConfig, ServicesConfig
    from observer_rock.config.workspace import load_workspace_config
    from observer_rock.plugins.registry import PluginRegistry

    module_path = tmp_path / "external_observer_plugin.py"
    module_path.write_text(
        """
class ExternalSourcePlugin:
    def fetch(self, *, monitor):
        return {"monitor_id": monitor.id, "origin": "external"}


def register_plugins(registry):
    registry.register_source_plugin("external_source", ExternalSourcePlugin())
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "services.yml").write_text(
        """
plugin_import_paths:
  - external_observer_plugin
services: {}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    workspace = load_workspace_config(tmp_path)

    assert workspace.services == ServicesConfig.model_validate(
        {"plugin_import_paths": ["external_observer_plugin"], "services": {}}
    )

    registry = PluginRegistry()
    registry.load_plugins(workspace.services.plugin_import_paths)

    plugin = registry.resolve_source_plugin("external_source")
    result = plugin.fetch(
        monitor=MonitorConfig(
            id="reddit-wallstreetbets",
            schedule="*/5 * * * *",
            source=MonitorSourceConfig(plugin="external_source"),
        )
    )

    assert result == {"monitor_id": "reddit-wallstreetbets", "origin": "external"}


def test_plugin_registry_loads_built_in_and_external_plugins_together(
    tmp_path,
    monkeypatch,
) -> None:
    from observer_rock.plugins.registry import PluginRegistry

    module_path = tmp_path / "external_observer_plugin.py"
    module_path.write_text(
        """
class ExternalSourcePlugin:
    def fetch(self, *, monitor):
        return {"origin": "external"}


def register_plugins(registry):
    registry.register_source_plugin("external_source", ExternalSourcePlugin())
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    registry = PluginRegistry()
    registry.load_plugins(["external_observer_plugin"])

    registry.resolve_source_plugin("builtin_echo")
    registry.resolve_source_plugin("external_source")


def test_plugin_registry_rejects_plugin_modules_without_register_plugins(
    tmp_path,
    monkeypatch,
) -> None:
    from observer_rock.plugins.registry import PluginRegistry

    module_path = tmp_path / "invalid_observer_plugin.py"
    module_path.write_text("PLUGIN_NAME = 'invalid'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    registry = PluginRegistry()

    with pytest.raises(ValueError) as exc_info:
        registry.load_plugins(["invalid_observer_plugin"])

    assert (
        exc_info.value.args[0]
        == "Plugin module 'invalid_observer_plugin' must define a callable register_plugins"
    )
