from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class MemoryItem(BaseModel):
    """Represents a discrete unit of knowledge."""
    key: str
    value: Any
    category: str
    confidence: float = 1.0


class MemoryStore:
    """A durable, thread-safe storage engine for agent knowledge.

    This class manages a local SQLite database to persist insights, user preferences,
    and technical facts across multiple workflow executions. It provides a key-value
    interface backed by structured SQL storage.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def put(self, item: MemoryItem) -> None:
        """Saves a memory item to the durable store."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO memory (key, value, category, confidence)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    confidence = excluded.confidence,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (item.key, json.dumps(item.value), item.category, item.confidence),
            )

    def get(self, key: str) -> MemoryItem | None:
        """Retrieves a specific memory item by its key."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT key, value, category, confidence FROM memory WHERE key = ?", (key,)
            ).fetchone()
            
            if not row:
                return None
            
            return MemoryItem(
                key=row[0],
                value=json.loads(row[1]),
                category=row[2],
                confidence=row[3],
            )

    def search(self, category: str) -> list[MemoryItem]:
        """Finds all memory items within a specific category."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT key, value, category, confidence FROM memory WHERE category = ?", 
                (category,)
            ).fetchall()
            
            return [
                MemoryItem(
                    key=r[0], value=json.loads(r[1]), category=r[2], confidence=r[3]
                )
                for r in rows
            ]
