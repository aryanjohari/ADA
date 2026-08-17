"""SQLite connection helpers — WAL mode, mount gate (M19a)."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data
from ada.logs.migrations import migrate_food_db, migrate_life_db


def _configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")


def _require(paths: DataPaths | None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing durable writes"
        )
    p.ensure_logs_dirs()
    return p


@contextmanager
def open_life_db(*, paths: DataPaths | None = None) -> Iterator[sqlite3.Connection]:
    """Open life_logs.db with migrations applied."""
    p = _require(paths)
    conn = sqlite3.connect(p.life_logs_db, timeout=30.0)
    try:
        _configure_connection(conn)
        migrate_life_db(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def open_food_db(*, paths: DataPaths | None = None) -> Iterator[sqlite3.Connection]:
    """Open food_reference.db with migrations applied."""
    p = _require(paths)
    conn = sqlite3.connect(p.food_reference_db, timeout=30.0)
    try:
        _configure_connection(conn)
        migrate_food_db(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def life_db_path(paths: DataPaths | None = None) -> Path:
    return _require(paths).life_logs_db
