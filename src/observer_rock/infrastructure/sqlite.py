import sqlite3
from datetime import datetime
from pathlib import Path

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
