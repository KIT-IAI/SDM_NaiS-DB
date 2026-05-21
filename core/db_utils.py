from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class TableBatch:
    table_name: str
    create_sql: str
    insert_sql: str
    rows: Sequence[Sequence[Any]]
    error_message: str


def connect(db_path: Path | str) -> sqlite3.Connection:
    return sqlite3.connect(str(db_path))


def drop_and_create_table(
    cursor: sqlite3.Cursor,
    table_name: str,
    create_sql: str,
) -> None:
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    cursor.execute(create_sql)


def safe_executemany(
    cursor: sqlite3.Cursor,
    sql: str,
    rows: Sequence[Sequence[Any]],
    *,
    error_message: str,
) -> None:
    try:
        cursor.executemany(sql, rows)
    except sqlite3.Error as exc:
        raise RuntimeError(f"{error_message}: {exc}") from exc


def safe_execute(
    cursor: sqlite3.Cursor,
    sql: str,
    params: Sequence[Any] | None = None,
    *,
    error_message: str,
) -> None:
    try:
        if params is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, params)
    except sqlite3.Error as exc:
        raise RuntimeError(f"{error_message}: {exc}") from exc


def write_table_batch(
    cursor: sqlite3.Cursor,
    batch: TableBatch,
) -> None:
    drop_and_create_table(cursor, batch.table_name, batch.create_sql)
    safe_executemany(
        cursor,
        batch.insert_sql,
        batch.rows,
        error_message=batch.error_message,
    )


def fetch_all(db_path: Path | str, sql: str, params: Sequence[Any] | None = None) -> list[tuple]:
    with connect(db_path) as conn:
        cursor = conn.cursor()
        if params is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, params)
        return cursor.fetchall()


def table_names(db_path: Path | str) -> list[str]:
    rows = fetch_all(
        db_path,
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name",
    )
    return [row[0] for row in rows]
