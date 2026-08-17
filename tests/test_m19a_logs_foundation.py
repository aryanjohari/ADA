"""M19a Slice 0 — SQLite foundation tests."""

from __future__ import annotations

from pathlib import Path

from ada.io.paths import get_paths
from ada.logs.connection import open_food_db, open_life_db
from ada.logs.meals import append_meal
from ada.logs.migrations import migrate_food_db, migrate_life_db
from ada.logs.time import get_running, start_block, stop_block
from ada.runs.append import new_receipt_id


def test_schema_create_idempotent(data_root: Path) -> None:
    paths = get_paths()
    with open_life_db(paths=paths) as conn:
        migrate_life_db(conn)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "meals" in tables
    assert "time_blocks" in tables
    with open_life_db(paths=paths) as conn:
        migrate_life_db(conn)
        assert conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] >= 1

    with open_food_db(paths=paths) as conn:
        migrate_food_db(conn)
        assert "foods" in {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }


def test_append_meal_row(data_root: Path) -> None:
    paths = get_paths()
    rid = new_receipt_id()
    result = append_meal(receipt_id=rid, note="test", paths=paths)
    assert result["ok"] is True
    with open_life_db(paths=paths) as conn:
        row = conn.execute(
            "SELECT receipt_id, note FROM meals WHERE meal_id = ?",
            (result["meal_id"],),
        ).fetchone()
    assert row is not None
    assert row["receipt_id"] == rid
    assert row["note"] == "test"


def test_single_running_timer(data_root: Path) -> None:
    paths = get_paths()
    r1 = start_block(kind="focus_deep", receipt_id=new_receipt_id(), paths=paths)
    running = get_running(paths=paths)
    assert running is not None
    assert running["block_id"] == r1["block_id"]

    r2 = start_block(kind="cooking", receipt_id=new_receipt_id(), paths=paths)
    assert r2.get("auto_stopped_prior") == r1["block_id"]
    running = get_running(paths=paths)
    assert running is not None
    assert running["block_id"] == r2["block_id"]

    with open_life_db(paths=paths) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM time_blocks WHERE status = 'running'"
        ).fetchone()[0]
    assert count == 1


def test_orphan_close_policy(data_root: Path) -> None:
    paths = get_paths()
    r1 = start_block(kind="sleep", receipt_id=new_receipt_id(), paths=paths)
    start_block(kind="wake", receipt_id=new_receipt_id(), paths=paths)
    with open_life_db(paths=paths) as conn:
        row = conn.execute(
            "SELECT status, auto_stopped_by FROM time_blocks WHERE block_id = ?",
            (r1["block_id"],),
        ).fetchone()
    assert row is not None
    assert row["status"] == "orphan_closed"
    assert row["auto_stopped_by"] is not None


def test_stop_no_active(data_root: Path) -> None:
    paths = get_paths()
    out = stop_block(receipt_id=new_receipt_id(), paths=paths)
    assert out["ok"] is False
    assert out["reason"] == "no_active_block"
