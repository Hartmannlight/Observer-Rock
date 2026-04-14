import json
from pathlib import Path

from observer_rock.application.monitoring import MonitorAnalysisOutputEntry, MonitorSourceData
from observer_rock.config.models import MonitorConfig
from observer_rock.plugins.registry import PluginRegistry
from observer_rock.plugins.source import SourceFetchContext


class BuiltinEchoSourcePlugin:
    def fetch(
        self,
        *,
        monitor: MonitorConfig,
        fetch_context: SourceFetchContext | None = None,
    ) -> object:
        return [
            {
                "source_id": f"{monitor.id}-builtin",
                "content": f"builtin echo for {monitor.id}",
            }
        ]


class BuiltinJsonFileSourcePlugin:
    def fetch(
        self,
        *,
        monitor: MonitorConfig,
        fetch_context: SourceFetchContext | None = None,
    ) -> object:
        configured_path = monitor.source.config.get("path")
        if not isinstance(configured_path, str) or not configured_path.strip():
            raise ValueError("builtin_json_file source requires source.config.path")

        source_path = Path(configured_path)
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("builtin_json_file source payload must be a list")
        return payload


class BuiltinIndexedFileSourcePlugin:
    def fetch(
        self,
        *,
        monitor: MonitorConfig,
        fetch_context: SourceFetchContext | None = None,
    ) -> object:
        configured_index_path = monitor.source.config.get("index_path")
        if not isinstance(configured_index_path, str) or not configured_index_path.strip():
            raise ValueError("builtin_indexed_file source requires source.config.index_path")

        discovery_limit = monitor.source.config.get("discovery_limit", 5)
        if not isinstance(discovery_limit, int) or discovery_limit <= 0:
            raise ValueError(
                "builtin_indexed_file source requires source.config.discovery_limit > 0"
            )

        index_path = Path(configured_index_path)
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("builtin_indexed_file source index payload must be a list")

        known_source_ids = {
            document.source_id for document in (fetch_context.recent_documents if fetch_context else ())
        }
        selected_entries: list[dict[str, object]] = []
        selected_source_ids: set[str] = set()

        for entry in payload[:discovery_limit]:
            if not isinstance(entry, dict):
                continue
            source_id = entry.get("source_id")
            if not isinstance(source_id, str) or not source_id.strip():
                continue
            if source_id in known_source_ids:
                continue
            selected_entries.append(entry)
            selected_source_ids.add(source_id)

        recheck_source_ids = set(fetch_context.recheck_document_ids if fetch_context else ())
        if recheck_source_ids:
            for entry in payload:
                if not isinstance(entry, dict):
                    continue
                source_id = entry.get("source_id")
                if not isinstance(source_id, str) or not source_id.strip():
                    continue
                if source_id not in recheck_source_ids or source_id in selected_source_ids:
                    continue
                selected_entries.append(entry)
                selected_source_ids.add(source_id)

        return [
            _load_indexed_file_source_record(index_path=index_path, entry=entry)
            for entry in selected_entries
        ]


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
    registry.register_source_plugin("builtin_indexed_file", BuiltinIndexedFileSourcePlugin())
    registry.register_analysis_plugin("builtin_summary", BuiltinSummaryAnalysisPlugin())
    registry.register_renderer_plugin("builtin_digest", BuiltinDigestRendererPlugin())
    registry.register_notifier_plugin("file_notifier", BuiltinFileNotifierPlugin())


def _load_indexed_file_source_record(*, index_path: Path, entry: dict[str, object]) -> dict[str, object]:
    source_id = entry.get("source_id")
    path = entry.get("path")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("builtin_indexed_file index entries require a non-blank source_id")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("builtin_indexed_file index entries require a non-blank path")

    document_path = Path(path)
    if not document_path.is_absolute():
        document_path = (index_path.parent / document_path).resolve()
    payload: dict[str, object] = {
        "source_id": source_id,
        "content": document_path.read_text(encoding="utf-8").strip(),
    }
    if isinstance(entry.get("document_identity"), str) and entry["document_identity"].strip():
        payload["document_identity"] = entry["document_identity"].strip()
    if isinstance(entry.get("title"), str) and entry["title"].strip():
        payload["title"] = entry["title"].strip()
    return payload
