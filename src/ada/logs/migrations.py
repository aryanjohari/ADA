"""Idempotent schema migrations for life logs (M19a)."""

from __future__ import annotations

import sqlite3

from ada.body.vitals import utc_now_iso
from ada.logs.schema import FOOD_REFERENCE_DDL, LIFE_LOGS_DDL

LIFE_SCHEMA_VERSION = 1
FOOD_SCHEMA_VERSION = 1


def _current_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()
    except sqlite3.OperationalError:
        return 0
    if row is None or row[0] is None:
        return 0
    return int(row[0])


def _apply_ddl(conn: sqlite3.Connection, ddl: tuple[str, ...]) -> None:
    for stmt in ddl:
        conn.execute(stmt)


def migrate_life_db(conn: sqlite3.Connection) -> None:
    if _current_version(conn) >= LIFE_SCHEMA_VERSION:
        return
    _apply_ddl(conn, LIFE_LOGS_DDL)
    conn.execute(
        "INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
        (LIFE_SCHEMA_VERSION, utc_now_iso()),
    )


def migrate_food_db(conn: sqlite3.Connection) -> None:
    if _current_version(conn) >= FOOD_SCHEMA_VERSION:
        return
    _apply_ddl(conn, FOOD_REFERENCE_DDL)
    conn.execute(
        "INSERT OR REPLACE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
        (FOOD_SCHEMA_VERSION, utc_now_iso()),
    )
