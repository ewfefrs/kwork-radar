"""Локальная память (SQLite): какие заказы уже показаны и их статус."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .models import Project


class State:
    def __init__(self, db_path: Path):
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen (
                id          TEXT PRIMARY KEY,
                title       TEXT,
                score       INTEGER,
                status      TEXT DEFAULT 'shown',   -- shown | applied | skipped
                first_seen  REAL
            )
            """
        )
        self._conn.commit()

    def is_seen(self, project_id: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM seen WHERE id = ?", (project_id,))
        return cur.fetchone() is not None

    def add(self, project: Project) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO seen (id, title, score, status, first_seen) "
            "VALUES (?, ?, ?, 'shown', ?)",
            (project.id, project.title, project.score, time.time()),
        )
        self._conn.commit()

    def set_status(self, project_id: str, status: str) -> None:
        self._conn.execute(
            "UPDATE seen SET status = ? WHERE id = ?", (status, project_id)
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
