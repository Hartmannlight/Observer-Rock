from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from observer_rock.config.models import MonitorConfig


@dataclass(frozen=True, slots=True)
class RecentDocumentReference:
    source_id: str
    identity_key: str


@dataclass(frozen=True, slots=True)
class SourceFetchContext:
    run_iteration: int
    recheck_enabled: bool
    recheck_document_ids: tuple[str, ...]
    recent_documents: tuple[RecentDocumentReference, ...]


@runtime_checkable
class SourcePlugin(Protocol):
    def fetch(
        self,
        *,
        monitor: MonitorConfig,
        fetch_context: SourceFetchContext | None = None,
    ) -> object:
        """Fetch raw source payloads for one monitor."""
