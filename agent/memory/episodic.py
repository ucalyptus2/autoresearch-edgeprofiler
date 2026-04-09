from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agent.state import CycleRecord


class EpisodicMemory:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle INTEGER NOT NULL,
                    target_node TEXT NOT NULL,
                    score REAL NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def append(self, record: CycleRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO cycles(cycle, target_node, score, payload) VALUES (?, ?, ?, ?)",
                (record.cycle, record.target_node, record.score, record.model_dump_json()),
            )
            conn.commit()

    def recent(self, limit: int = 3) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT payload FROM cycles ORDER BY cycle DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]
