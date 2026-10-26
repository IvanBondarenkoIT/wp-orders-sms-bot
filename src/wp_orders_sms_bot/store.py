"""SQLite store for processed order IDs (idempotency)."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class ProcessedStore:
    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_orders (
                    order_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            conn.commit()

    def has(self, order_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_orders WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            return row is not None

    def add(self, order_id: str, campaign_id: str) -> bool:
        """Insert order. Returns True if newly inserted, False if already existed."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO processed_orders (order_id, campaign_id) VALUES (?, ?)",
                    (order_id, campaign_id),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
