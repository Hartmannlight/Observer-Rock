from observer_rock.plugins.analysis import AnalysisPlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._analysis_plugins: dict[str, AnalysisPlugin] = {}

    def register_analysis_plugin(self, plugin_name: str, plugin: AnalysisPlugin) -> None:
        self._analysis_plugins[plugin_name] = plugin

    def resolve_analysis_plugin(self, plugin_name: str) -> AnalysisPlugin:
        if plugin_name in self._analysis_plugins:
            return self._analysis_plugins[plugin_name]

        raise KeyError(f"Unknown analysis plugin: {plugin_name}")
