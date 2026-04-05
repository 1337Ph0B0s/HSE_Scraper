from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from typing import Any, Dict, Iterable, Optional

import pandas as pd


class SQLiteStore:
    """
    Checkpoint/reanudación:
    - guarda cada notice_number como PK
    - almacena JSON del registro completo
    - permite export a CSV al final (o cuando quieras)
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.con = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS notices (
                notice_number TEXT PRIMARY KEY,
                data_json TEXT NOT NULL
            )
            """
        )
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                error TEXT,
                created_at TEXT
            )
            """
        )
        self.con.commit()

    def close(self) -> None:
        self.con.close()

    def has_notice(self, notice_number: str) -> bool:
        cur = self.con.execute(
            "SELECT 1 FROM notices WHERE notice_number = ? LIMIT 1",
            (notice_number,),
        )
        return cur.fetchone() is not None

    def upsert_notice(self, record: Any) -> None:
        payload = json.dumps(asdict(record), ensure_ascii=False)
        self.con.execute(
            "INSERT OR REPLACE INTO notices (notice_number, data_json) VALUES (?, ?)",
            (record.notice_number, payload),
        )

    def commit(self) -> None:
        self.con.commit()

    def log_error(self, url: str, error: str, created_at: str) -> None:
        self.con.execute(
            "INSERT INTO errors (url, error, created_at) VALUES (?, ?, ?)",
            (url, error, created_at),
        )

    def export_to_csv(self, out_csv: str) -> int:
        cur = self.con.execute("SELECT data_json FROM notices")
        rows = [json.loads(r[0]) for r in cur.fetchall()]
        df = pd.DataFrame(rows).sort_values(by=["notice_number"])
        df.to_csv(out_csv, index=False, encoding="utf-8")
        return len(df)