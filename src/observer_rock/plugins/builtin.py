from observer_rock.config.models import MonitorConfig
from observer_rock.plugins.registry import PluginRegistry


class BuiltinEchoSourcePlugin:
    def fetch(self, *, monitor: MonitorConfig) -> object:
        return [
            {
                "source_id": f"{monitor.id}-builtin",
                "content": f"builtin echo for {monitor.id}",
            }
        ]


def register_plugins(registry: PluginRegistry) -> None:
    registry.register_source_plugin("builtin_echo", BuiltinEchoSourcePlugin())
