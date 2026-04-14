from importlib import import_module
from typing import Protocol

from observer_rock.plugins.analysis import AnalysisPlugin
from observer_rock.plugins.source import SourcePlugin

BUILTIN_PLUGIN_IMPORT_PATHS = ("observer_rock.plugins.builtin",)


class PluginRegistrar(Protocol):
    def register_plugins(self, registry: "PluginRegistry") -> None: ...


class PluginRegistry:
    def __init__(self) -> None:
        self._analysis_plugins: dict[str, AnalysisPlugin] = {}
        self._source_plugins: dict[str, SourcePlugin] = {}

    def load_plugins(self, plugin_import_paths: list[str]) -> None:
        for plugin_import_path in [*BUILTIN_PLUGIN_IMPORT_PATHS, *plugin_import_paths]:
            try:
                plugin_module = import_module(plugin_import_path)
            except ImportError as exc:
                raise ValueError(
                    f"Could not import plugin module '{plugin_import_path}'"
                ) from exc
            except Exception as exc:
                raise ValueError(
                    f"Plugin module '{plugin_import_path}' failed during import: {exc}"
                ) from exc

            registrar = getattr(plugin_module, "register_plugins", None)
            if not callable(registrar):
                raise ValueError(
                    f"Plugin module '{plugin_import_path}' must define a callable "
                    "register_plugins"
                )
            try:
                registrar(self)
            except Exception as exc:
                raise ValueError(
                    "Plugin module "
                    f"'{plugin_import_path}' failed while registering plugins: {exc}"
                ) from exc

    def register_analysis_plugin(self, plugin_name: str, plugin: AnalysisPlugin) -> None:
        self._analysis_plugins[plugin_name] = plugin

    def resolve_analysis_plugin(self, plugin_name: str) -> AnalysisPlugin:
        if plugin_name in self._analysis_plugins:
            return self._analysis_plugins[plugin_name]

        raise KeyError(f"Unknown analysis plugin: {plugin_name}")

    def register_source_plugin(self, plugin_name: str, plugin: SourcePlugin) -> None:
        self._source_plugins[plugin_name] = plugin

    def resolve_source_plugin(self, plugin_name: str) -> SourcePlugin:
        if plugin_name in self._source_plugins:
            return self._source_plugins[plugin_name]

        raise KeyError(f"Unknown source plugin: {plugin_name}")
