from __future__ import annotations

import sqlite3
from pathlib import Path


class SqliteDeliveryReceiptStore:
    """Durable best-effort deduplication for successfully delivered message parts.

    The external Telegram call and local SQLite commit cannot be one atomic transaction.
    A process crash after Telegram accepts a message but before the receipt is persisted may
    still produce a duplicate on restart. The store prevents normal retry/restart duplicates
    once a successful receipt has been recorded.
    """

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def was_delivered(self, source_key: str, chat_id: str, part_index: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM delivery_receipts
                WHERE source_key = ? AND chat_id = ? AND part_index = ?
                """,
                (source_key, chat_id, part_index),
            ).fetchone()
        return row is not None

    def mark_delivered(self, source_key: str, chat_id: str, part_index: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO delivery_receipts(source_key, chat_id, part_index)
                VALUES (?, ?, ?)
                """,
                (source_key, chat_id, part_index),
            )
            connection.commit()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS delivery_receipts (
                    source_key TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    part_index INTEGER NOT NULL,
                    delivered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (source_key, chat_id, part_index)
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path, timeout=30)
