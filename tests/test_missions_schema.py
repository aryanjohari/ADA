"""Missions table, tasks.mission_id migration, and PersistentState helpers."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest
import sqlite3

from ada.persistent.store import PersistentState


@pytest.mark.asyncio
async def test_fresh_db_has_missions_and_mission_fk(tmp_path: Path, schema_sql_path: Path) -> None:
    db = tmp_path / "m.db"
    ps = PersistentState(db, schema_sql_path)
    await ps.connect()
    try:
        async with aiosqlite.connect(db) as raw:
            await raw.execute("PRAGMA foreign_keys = ON")
            cur = await raw.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='missions'"
            )
            assert await cur.fetchone() is not None
            cur = await raw.execute("PRAGMA table_info(tasks)")
            cols = {str(r[1]) for r in await cur.fetchall()}
            assert "mission_id" in cols
            cur = await raw.execute("PRAGMA table_info(workflows)")
            wfcols = {str(r[1]) for r in await cur.fetchall()}
            assert "mission_id" in wfcols
            cur = await raw.execute("PRAGMA foreign_key_check")
            assert await cur.fetchall() == []
    finally:
        await ps.close()


@pytest.mark.asyncio
async def test_migration_adds_missions_schema(
    tmp_path: Path, schema_sql_path: Path
) -> None:
    before = (
        Path(__file__).resolve().parent / "fixtures" / "schema_before_missions.sql"
    )
    db = tmp_path / "pre_missions.db"
    async with aiosqlite.connect(db) as raw:
        await raw.execute("PRAGMA foreign_keys = ON")
        await raw.executescript(before.read_text(encoding="utf-8"))
        await raw.commit()
    ps = PersistentState(db, schema_sql_path)
    await ps.connect()
    try:
        async with aiosqlite.connect(db) as raw:
            await raw.execute("PRAGMA foreign_keys = ON")
            cur = await raw.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='missions'"
            )
            assert await cur.fetchone() is not None
            cur = await raw.execute("PRAGMA table_info(tasks)")
            cols = {str(r[1]) for r in await cur.fetchall()}
            assert "mission_id" in cols
            cur = await raw.execute("PRAGMA table_info(workflows)")
            wfcols = {str(r[1]) for r in await cur.fetchall()}
            assert "mission_id" in wfcols
            cur = await raw.execute("PRAGMA foreign_key_check")
            assert await cur.fetchall() == []
    finally:
        await ps.close()


@pytest.mark.asyncio
async def test_create_mission_get_by_slug_roundtrip(
    tmp_path: Path, schema_sql_path: Path
) -> None:
    db = tmp_path / "m.db"
    ps = PersistentState(db, schema_sql_path)
    await ps.connect()
    try:
        mid = await ps.create_mission(
            "grow-nz-newsletter",
            "NZ housing newsletter",
            niche="housing",
            topic="policy",
            defaults_json={"tone": "analytical"},
            brief_md="# Brief",
            brief_md_path="/tmp/brief.md",
            schedule_hint_json={"cron": "0 9 * * 1"},
        )
        assert mid > 0
        row = await ps.get_mission_by_slug("grow-nz-newsletter")
        assert row is not None
        assert row["id"] == mid
        assert row["slug"] == "grow-nz-newsletter"
        assert row["title"] == "NZ housing newsletter"
        assert row["niche"] == "housing"
        assert row["topic"] == "policy"
        assert row["defaults_json"] == {"tone": "analytical"}
        assert row["brief_md"] == "# Brief"
        assert row["brief_md_path"] == "/tmp/brief.md"
        assert row["schedule_hint_json"] == {"cron": "0 9 * * 1"}
    finally:
        await ps.close()


@pytest.mark.asyncio
async def test_create_mission_duplicate_slug_integrity_error(
    tmp_path: Path, schema_sql_path: Path
) -> None:
    db = tmp_path / "m.db"
    ps = PersistentState(db, schema_sql_path)
    await ps.connect()
    try:
        await ps.create_mission("same-slug", "One")
        with pytest.raises(sqlite3.IntegrityError):
            await ps.create_mission("same-slug", "Two")
    finally:
        await ps.close()


@pytest.mark.asyncio
async def test_attach_task_mission_delete_sets_null(
    tmp_path: Path, schema_sql_path: Path
) -> None:
    db = tmp_path / "m.db"
    ps = PersistentState(db, schema_sql_path)
    await ps.connect()
    try:
        mid = await ps.create_mission("m", "Mission")
        tid = await ps.insert_task("goal text", task_kind="goal")
        await ps.attach_task_to_mission(tid, mid)
        cur = await ps._conn.execute(
            "SELECT mission_id FROM tasks WHERE id = ?", (tid,)
        )
        row = await cur.fetchone()
        assert row is not None and int(row[0]) == mid
        await ps._conn.execute("DELETE FROM missions WHERE id = ?", (mid,))
        await ps._conn.commit()
        cur = await ps._conn.execute(
            "SELECT mission_id FROM tasks WHERE id = ?", (tid,)
        )
        row = await cur.fetchone()
        assert row is not None and row[0] is None
    finally:
        await ps.close()
