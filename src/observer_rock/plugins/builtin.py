import json
from pathlib import Path

from observer_rock.application.monitoring import MonitorAnalysisOutputEntry, MonitorSourceData
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


class BuiltinJsonFileSourcePlugin:
    def fetch(self, *, monitor: MonitorConfig) -> object:
        configured_path = monitor.source.config.get("path")
        if not isinstance(configured_path, str) or not configured_path.strip():
            raise ValueError("builtin_json_file source requires source.config.path")

        source_path = Path(configured_path)
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("builtin_json_file source payload must be a list")
        return payload


class BuiltinSummaryAnalysisPlugin:
    def analyze(self, *, monitor, profile_name, profile, source_data=None) -> object:
        records = () if source_data is None else source_data.records
        return {
            "monitor_id": monitor.id,
            "profile_name": profile_name,
            "record_count": len(records),
            "items": [
                {
                    "source_id": record.source_id,
                    "summary": record.content,
                }
                for record in records
            ],
        }


class BuiltinDigestRendererPlugin:
    def render(
        self,
        *,
        monitor,
        output,
        analysis_output: MonitorAnalysisOutputEntry,
        source_data: MonitorSourceData | None = None,
    ) -> str:
        lines = [
            f"Monitor: {monitor.id}",
            f"Profile: {analysis_output.profile_name}",
        ]
        rendered_output = analysis_output.output
        if isinstance(rendered_output, dict):
            items = rendered_output.get("items")
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    source_id = item.get("source_id", "unknown")
                    summary = item.get("summary", "")
                    lines.append(f"- {source_id}: {summary}")
        if source_data is not None:
            lines.append(f"Source records: {len(source_data.records)}")
        return "\n".join(lines)


class BuiltinFileNotifierPlugin:
    def notify(self, *, monitor, service_name, service, payload: str) -> object:
        if service.path is None:
            raise ValueError(f"Service '{service_name}' requires path for file notifier")
        target_path = Path(service.path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("a", encoding="utf-8") as handle:
            if target_path.exists() and target_path.stat().st_size > 0:
                handle.write("\n\n")
            handle.write(payload)
        return {"path": str(target_path)}


def register_plugins(registry: PluginRegistry) -> None:
    registry.register_source_plugin("builtin_echo", BuiltinEchoSourcePlugin())
    registry.register_source_plugin("builtin_json_file", BuiltinJsonFileSourcePlugin())
    registry.register_analysis_plugin("builtin_summary", BuiltinSummaryAnalysisPlugin())
    registry.register_renderer_plugin("builtin_digest", BuiltinDigestRendererPlugin())
    registry.register_notifier_plugin("file_notifier", BuiltinFileNotifierPlugin())
