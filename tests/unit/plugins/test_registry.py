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
