from __future__ import annotations

import shutil
import sqlite3

from core.builder_config import ALTBAUATLAS_BACKUP_DB_PATH, ALTBAUATLAS_SOURCE_DB_PATH


DB_PATH = ALTBAUATLAS_SOURCE_DB_PATH
BACKUP_PATH = ALTBAUATLAS_BACKUP_DB_PATH

# Mapping of non-standard / corrupted characters to their replacements
REPLACEMENTS = {
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ï¿½": "ü",   # Example: Lehmschï¿½ttung -> Lehmschüttung
}


def backup_database(db_path: str, backup_path: str) -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file does not exist: {db_path}")
    shutil.copy2(db_path, backup_path)
    print(f"Backup created: {backup_path}")


def get_text_columns(conn: sqlite3.Connection):
    result = {}
    cur = conn.cursor()

    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        """
    )
    tables = [row[0] for row in cur.fetchall()]

    for table in tables:
        cur.execute(f"PRAGMA table_info('{table}')")
        cols = cur.fetchall()
        text_cols = [col[1] for col in cols if col[2] and col[2].upper() == "TEXT"]
        if text_cols:
            result[table] = text_cols

    return result


def count_occurrences_in_column(conn: sqlite3.Connection, table: str, column: str, bad: str) -> int:
    cur = conn.cursor()
    sql = f"""
        SELECT SUM(
            (LENGTH("{column}") - LENGTH(REPLACE("{column}", ?, ''))) / LENGTH(?)
        )
        FROM "{table}"
        WHERE "{column}" IS NOT NULL
          AND "{column}" LIKE '%' || ? || '%'
    """
    cur.execute(sql, (bad, bad, bad))
    value = cur.fetchone()[0]
    return int(value) if value is not None else 0


def replace_in_column(conn: sqlite3.Connection, table: str, column: str, old: str, new: str) -> int:
    cur = conn.cursor()
    sql = f'''
        UPDATE "{table}"
        SET "{column}" = REPLACE("{column}", ?, ?)
        WHERE "{column}" IS NOT NULL
          AND "{column}" LIKE '%' || ? || '%'
    '''
    cur.execute(sql, (old, new, old))
    return cur.rowcount


def main() -> None:
    backup_database(DB_PATH, BACKUP_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")

    text_columns = get_text_columns(conn)

    total_replacements = 0

    try:
        for table, columns in text_columns.items():
            print(f"\nProcessing table: {table}")
            for column in columns:
                column_total = 0

                for bad, good in REPLACEMENTS.items():
                    occ = count_occurrences_in_column(conn, table, column, bad)
                    if occ > 0:
                        affected_rows = replace_in_column(conn, table, column, bad, good)
                        print(
                            f'  Column "{column}": "{bad}" -> "{good}", '
                            f'replaced {occ} occurrence(s), affected {affected_rows} row(s)'
                        )
                        column_total += occ
                        total_replacements += occ

                if column_total == 0:
                    print(f'  Column "{column}": no changes needed')

        conn.commit()
        print(f"\nDone. Total replacements: {total_replacements}")

    except Exception as exc:
        conn.rollback()
        print(f"\nAn error occurred. Changes have been rolled back: {exc}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
