#!/usr/bin/env python3
"""Delete old completed ``system_jobs`` rows (retention)."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("state_db", type=Path)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    db = args.state_db.resolve()
    days = max(1, int(args.days))
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM system_jobs
            WHERE status = 'completed'
              AND datetime(updated_at) < datetime('now', ?)
            """,
            (f"-{days} days",),
        )
        n = int(cur.fetchone()[0])
        print(f"rows_to_delete={n} dry_run={args.dry_run}")
        if args.dry_run or n == 0:
            conn.rollback()
            return 0
        conn.execute(
            """
            DELETE FROM system_jobs
            WHERE status = 'completed'
              AND datetime(updated_at) < datetime('now', ?)
            """,
            (f"-{days} days",),
        )
        conn.commit()
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
