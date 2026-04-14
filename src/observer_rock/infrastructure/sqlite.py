import sqlite3
from datetime import datetime
import json
from pathlib import Path

from observer_rock.application.document_intelligence import (
    DocumentHistoryEntry,
    DocumentAnalysisRecord,
    IndexedDocumentRecord,
    QueryableDocumentMatch,
)
from observer_rock.application.documents import DocumentRecord
from observer_rock.application.repositories import RunRecord


class SqliteRunRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._initialize()

    def create(self, run: RunRecord) -> RunRecord:
        with sqlite3.connect(self._database_path) as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO runs (run_id, monitor_id, status, started_at, ended_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        run.run_id,
                        run.monitor_id,
                        run.status,
                        _serialize_datetime(run.started_at),
                        _serialize_datetime(run.ended_at),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise KeyError(run.run_id) from exc
        return run

    def save(self, run: RunRecord) -> RunRecord:
        with sqlite3.connect(self._database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE runs
                SET monitor_id = ?, status = ?, started_at = ?, ended_at = ?
                WHERE run_id = ?
                """,
                (
                    run.monitor_id,
                    run.status,
                    _serialize_datetime(run.started_at),
                    _serialize_datetime(run.ended_at),
                    run.run_id,
                ),
            )
        if cursor.rowcount == 0:
            raise KeyError(run.run_id)
        return run

    def get(self, run_id: str) -> RunRecord | None:
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT run_id, monitor_id, status, started_at, ended_at
                FROM runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return _deserialize_run_record(row)

    def list_runs(self) -> list[RunRecord]:
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                """
                SELECT run_id, monitor_id, status, started_at, ended_at
                FROM runs
                ORDER BY rowid
                """
            ).fetchall()
        return [_deserialize_run_record(row) for row in rows]

    def _initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    monitor_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    ended_at TEXT
                )
                """
            )


class SqliteDocumentRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._initialize()

    def save(self, document: DocumentRecord) -> DocumentRecord:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO documents (document_id, version)
                VALUES (?, ?)
                """,
                (document.document_id, document.version),
            )
        return document

    def get(self, document_id: str, *, version: int) -> DocumentRecord | None:
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT document_id, version
                FROM documents
                WHERE document_id = ? AND version = ?
                """,
                (document_id, version),
            ).fetchone()
        if row is None:
            return None
        return _deserialize_document_record(row)

    def get_latest(self, document_id: str) -> DocumentRecord | None:
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT document_id, version
                FROM documents
                WHERE document_id = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        return _deserialize_document_record(row)

    def _initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    PRIMARY KEY (document_id, version)
                )
                """
            )


class SqliteDocumentIntelligenceRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._initialize()

    def get_latest_document(
        self,
        *,
        monitor_id: str,
        identity_key: str,
    ) -> IndexedDocumentRecord | None:
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT document_id, monitor_id, source_id, version, content_hash, source_content, title, identity_key
                FROM indexed_documents
                WHERE monitor_id = ? AND identity_key = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (monitor_id, identity_key),
            ).fetchone()
        if row is None:
            return None
        return _deserialize_indexed_document_record(row)

    def save_document(self, record: IndexedDocumentRecord) -> IndexedDocumentRecord:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO indexed_documents (
                    document_id,
                    monitor_id,
                    source_id,
                    identity_key,
                    version,
                    content_hash,
                    source_content,
                    title
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.document_id,
                    record.monitor_id,
                    record.source_id,
                    record.identity_key,
                    record.version,
                    record.content_hash,
                    record.source_content,
                    record.title,
                ),
            )
        return record

    def save_analysis(self, record: DocumentAnalysisRecord) -> DocumentAnalysisRecord:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO document_analyses (
                    document_id,
                    monitor_id,
                    identity_key,
                    source_id,
                    version,
                    profile_name,
                    analysis_text,
                    output_json,
                    source_content,
                    title
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.document_id,
                    record.monitor_id,
                    record.identity_key,
                    record.source_id,
                    record.version,
                    record.profile_name,
                    record.analysis_text,
                    record.output_json,
                    record.source_content,
                    record.title,
                ),
            )
        return record

    def query_documents(
        self,
        *,
        profile_name: str,
        contains_text: str,
        monitor_id: str | None = None,
        latest_only: bool = True,
    ) -> list[QueryableDocumentMatch]:
        normalized_pattern = f"%{contains_text.casefold()}%"
        query = """
            SELECT monitor_id, identity_key, source_id, document_id, version, profile_name, analysis_text, source_content, title
            FROM document_analyses
            WHERE profile_name = ? AND (
                lower(analysis_text) LIKE ? OR lower(output_json) LIKE ?
            )
        """
        parameters: list[str] = [profile_name, normalized_pattern, normalized_pattern]
        if monitor_id is not None:
            query += " AND monitor_id = ?"
            parameters.append(monitor_id)
        if latest_only:
            query += """
             AND version = (
                SELECT MAX(da2.version)
                FROM document_analyses da2
                WHERE da2.document_id = document_analyses.document_id
                  AND da2.profile_name = document_analyses.profile_name
            )
            """
        query += " ORDER BY monitor_id, source_id, version DESC"
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [_deserialize_queryable_document_match(row) for row in rows]

    def get_document_history(
        self,
        *,
        document_id: str,
        profile_name: str,
    ) -> list[DocumentHistoryEntry]:
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                """
                SELECT document_id, monitor_id, identity_key, source_id, version, profile_name, analysis_text, source_content, title
                FROM document_analyses
                WHERE document_id = ? AND profile_name = ?
                ORDER BY version DESC
                """,
                (document_id, profile_name),
            ).fetchall()
        return [_deserialize_document_history_entry(row) for row in rows]

    def _initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS indexed_documents (
                    document_id TEXT NOT NULL,
                    monitor_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    identity_key TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    source_content TEXT NOT NULL,
                    title TEXT,
                    PRIMARY KEY (document_id, version)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS document_analyses (
                    document_id TEXT NOT NULL,
                    monitor_id TEXT NOT NULL,
                    identity_key TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    profile_name TEXT NOT NULL,
                    analysis_text TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    source_content TEXT NOT NULL,
                    title TEXT,
                    PRIMARY KEY (document_id, version, profile_name)
                )
                """
            )


class SqliteMonitorChangeTrackingRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._initialize()

    def get_state(self, monitor_id: str) -> tuple[int, int, tuple[tuple[str, str], ...]]:
        with sqlite3.connect(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT run_iteration, recheck_cursor, recent_documents_json
                FROM monitor_change_tracking_state
                WHERE monitor_id = ?
                """,
                (monitor_id,),
            ).fetchone()
        if row is None:
            return (0, 0, ())
        recent_documents = tuple(
            (entry["source_id"], entry["identity_key"])
            for entry in json.loads(row[2])
            if isinstance(entry, dict)
            and isinstance(entry.get("source_id"), str)
            and isinstance(entry.get("identity_key"), str)
        )
        return (row[0], row[1], recent_documents)

    def save_state(
        self,
        *,
        monitor_id: str,
        run_iteration: int,
        recheck_cursor: int,
        recent_documents: tuple[tuple[str, str], ...],
    ) -> None:
        payload = json.dumps(
            [
                {"source_id": source_id, "identity_key": identity_key}
                for source_id, identity_key in recent_documents
            ],
            separators=(",", ":"),
        )
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO monitor_change_tracking_state (
                    monitor_id,
                    run_iteration,
                    recheck_cursor,
                    recent_documents_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (monitor_id, run_iteration, recheck_cursor, payload),
            )

    def _initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_change_tracking_state (
                    monitor_id TEXT PRIMARY KEY,
                    run_iteration INTEGER NOT NULL,
                    recheck_cursor INTEGER NOT NULL,
                    recent_documents_json TEXT NOT NULL
                )
                """
            )


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _deserialize_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _deserialize_run_record(row: tuple[str, str, str, str | None, str | None]) -> RunRecord:
    return RunRecord(
        run_id=row[0],
        monitor_id=row[1],
        status=row[2],
        started_at=_deserialize_datetime(row[3]),
        ended_at=_deserialize_datetime(row[4]),
    )


def _deserialize_document_record(row: tuple[str, int]) -> DocumentRecord:
    return DocumentRecord(document_id=row[0], version=row[1])


def _deserialize_indexed_document_record(
    row: tuple[str, str, str, int, str, str, str | None, str],
) -> IndexedDocumentRecord:
    return IndexedDocumentRecord(
        document_id=row[0],
        monitor_id=row[1],
        source_id=row[2],
        identity_key=row[7],
        version=row[3],
        content_hash=row[4],
        source_content=row[5],
        title=row[6],
    )


def _deserialize_queryable_document_match(
    row: tuple[str, str, str, str, int, str, str, str, str | None],
) -> QueryableDocumentMatch:
    return QueryableDocumentMatch(
        monitor_id=row[0],
        identity_key=row[1],
        source_id=row[2],
        document_id=row[3],
        version=row[4],
        profile_name=row[5],
        analysis_text=row[6],
        source_content=row[7],
        title=row[8],
    )


def _deserialize_document_history_entry(
    row: tuple[str, str, str, str, int, str, str, str, str | None],
) -> DocumentHistoryEntry:
    return DocumentHistoryEntry(
        document_id=row[0],
        monitor_id=row[1],
        identity_key=row[2],
        source_id=row[3],
        version=row[4],
        profile_name=row[5],
        analysis_text=row[6],
        source_content=row[7],
        title=row[8],
    )
