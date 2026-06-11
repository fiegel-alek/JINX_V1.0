"""SQLite persistence for early JINX application state."""

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(slots=True)
class SQLiteJINXDatabase:
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    collection TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (collection, document_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_documents_collection
                ON documents(collection)
                """
            )

    def save_document(self, collection: str, document_id: str, document: dict[str, Any]) -> None:
        if not collection:
            raise ValueError("collection is required")
        if not document_id:
            raise ValueError("document_id is required")
        now = datetime.now(UTC).isoformat()
        payload = json.dumps(document, sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO documents(collection, document_id, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(collection, document_id)
                DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
                """,
                (collection, document_id, payload, now, now),
            )

    def get_document(self, collection: str, document_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload FROM documents
                WHERE collection = ? AND document_id = ?
                """,
                (collection, document_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"document not found: {collection}/{document_id}")
        return json.loads(row["payload"])

    def list_documents(self, collection: str) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload FROM documents
                WHERE collection = ?
                ORDER BY created_at ASC, document_id ASC
                """,
                (collection,),
            ).fetchall()
        return tuple(json.loads(row["payload"]) for row in rows)

    def count(self, collection: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE collection = ?",
                (collection,),
            ).fetchone()
        return int(row["count"])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection
