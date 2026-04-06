from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from typing import Any, Dict, Iterable, Optional

import pandas as pd


class SQLiteStore:
    """
    Almacenamiento incremental (checkpoint) basado en SQLite para reanudación del scraping.

    Objetivo
    --------
    Persistir cada registro del dataset (1 notice = 1 fila) a medida que se extrae, de forma que:
    - El scraping sea reanudable (si se interrumpe con Ctrl+C o por un error).
    - Se eviten duplicados (clave primaria `notice_number`).
    - Se puedan exportar resultados parciales o finales a CSV de forma reproducible.

    Diseño
    ------
    - Tabla principal: `notices`
        - `notice_number` (TEXT, PRIMARY KEY): identificador único del registro.
        - `data_json` (TEXT): serialización JSON del `NoticeRecord` (toda la fila).
    - Tabla auxiliar: `errors`
        - Registra fallos en URLs individuales (por ejemplo, detalle con HTML inesperado),
          sin detener el pipeline completo.

    Justificación
    -------------
    - SQLite es liviano, local y no requiere servicios externos.
    - Guardar en JSON permite flexibilidad: si el modelo crece (nuevas columnas), no es necesario
      alterar el esquema con frecuencia.
    - Facilita auditoría y trazabilidad: se conserva la fila completa junto con el `detail_url`
      y `scraped_at_utc`.

    Consideraciones de calidad
    --------------------------
    - El pipeline debe hacer `commit()` periódicamente (p. ej., cada N registros) para minimizar
      pérdida de progreso ante interrupciones.
    - La exportación a CSV se realiza a partir de `notices`, ordenada por `notice_number`.

    Parameters
    ----------
    db_path : str
        Ruta del archivo SQLite. Si no existe, se crea automáticamente.

    Notes
    -----
    - Este store no “descarga datos”; solo gestiona persistencia y exportación.
    - La política de “no re-scrapear” se implementa en el pipeline mediante `has_notice()`.
      Si se desea forzar re-scraping, debe añadirse un flag `--force` a nivel de pipeline/CLI.
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